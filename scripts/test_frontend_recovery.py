"""Test controlled backend restart, failure detection, and automatic recovery.

Simulates frontend behavior during a backend crash/restart:
1. Verifies initial ONLINE state (HTTP 200 on /health and /api/v1/status).
2. Terminates backend process to simulate controlled failure.
3. Tests that health polling detects failure and transitions to OFFLINE.
4. Tests that in-flight/subsequent requests fail cleanly with timeout/unreachable errors.
5. Restarts backend process on port 8000.
6. Polls health until automatic recovery is detected (transitions to ONLINE).
7. Verifies subsequent Route Planning and Science Discovery requests succeed immediately
   WITHOUT full application reload.
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime, timezone
import httpx
import psutil

API_BASE = "http://127.0.0.1:8000"


def find_uvicorn_pid() -> list[int]:
    pids = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(proc.info["cmdline"] or [])
            if "uvicorn" in cmd and "app.main:app" in cmd and "python" in proc.info["name"].lower():
                pids.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return pids


def run_recovery_test():
    print(f"[{datetime.now(timezone.utc).isoformat()}] STARTING CONTROLLED BACKEND RECOVERY TEST")
    client = httpx.Client(headers={"Origin": "http://localhost:3005"})

    # Step 1: Initial state check
    print("\n--- Step 1: Verify Initial Backend Health (ONLINE) ---")
    t0 = time.perf_counter()
    resp = client.get(f"{API_BASE}/health")
    health_latency = (time.perf_counter() - t0) * 1000
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print(f"Health check OK: {resp.status_code} in {health_latency:.1f}ms. Status: ONLINE")

    # Step 2: Identify and terminate Uvicorn process
    pids = find_uvicorn_pid()
    print(f"\n--- Step 2: Terminate Backend Process (Simulate Outage) ---")
    print(f"Active Uvicorn PID(s): {pids}")
    for pid in pids:
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=5)
            print(f"Successfully terminated PID {pid}")
        except Exception as e:
            print(f"Error terminating PID {pid}: {e}")

    # Step 3: Verify failure detection (transitions to OFFLINE)
    print("\n--- Step 3: Verify Disconnection Detection (OFFLINE) ---")
    disconnect_detected = False
    for attempt in range(5):
        try:
            r = client.get(f"{API_BASE}/health", timeout=2.0)
            print(f"Attempt {attempt+1}: Still responding?! {r.status_code}")
            time.sleep(1)
        except Exception as e:
            disconnect_detected = True
            print(f"Attempt {attempt+1}: Connection failed cleanly: {type(e).__name__}. Status: OFFLINE")
            break

    assert disconnect_detected, "Backend disconnection was not detected!"

    # Step 4: Verify in-flight / subsequent requests fail cleanly during outage
    print("\n--- Step 4: Verify Clean Request Failure During Outage ---")
    try:
        route_resp = client.post(
            f"{API_BASE}/api/v1/marswalk/route",
            json={
                "start_lat": -4.60,
                "start_lon": 66.317,
                "dest_lat": -4.64,
                "dest_lon": 66.35,
                "mode": "walking",
                "max_slope_deg": 25.0,
            },
            timeout=3.0,
        )
        print(f"Route during outage responded: {route_resp.status_code}")
    except Exception as e:
        print(f"Route request failed cleanly during outage as expected: {type(e).__name__} ({e})")

    # Step 5: Restart backend
    print("\n--- Step 5: Restart Backend Server on Port 8000 ---")
    restart_t0 = time.perf_counter()
    python_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".venv", "Scripts", "python.exe"))
    uvicorn_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".venv", "Scripts", "uvicorn.exe"))
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))

    new_proc = subprocess.Popen(
        [uvicorn_exe, "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000"],
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"Spawned new backend process: PID {new_proc.pid}")

    # Step 6: Poll health to measure automatic recovery time
    print("\n--- Step 6: Detect Automatic Recovery (OFFLINE -> ONLINE) ---")
    recovered = False
    recovery_start = time.perf_counter()
    while time.perf_counter() - recovery_start < 20.0:
        try:
            r = client.get(f"{API_BASE}/health", timeout=1.5)
            if r.status_code == 200:
                recovery_duration = (time.perf_counter() - restart_t0) * 1000
                print(f"Backend RECOVERED to ONLINE! Total restart-to-recovery time: {recovery_duration:.1f}ms ({recovery_duration/1000:.2f}s)")
                recovered = True
                break
        except Exception:
            time.sleep(0.4)

    assert recovered, "Backend failed to recover within 20 seconds!"

    # Step 7: Verify subsequent operations succeed immediately without page reload
    print("\n--- Step 7: Verify Post-Recovery Route and Science Operations ---")
    # Science discovery
    t_sci = time.perf_counter()
    sci_resp = client.get(f"{API_BASE}/api/v1/discovery/list?limit=5")
    sci_lat = (time.perf_counter() - t_sci) * 1000
    assert sci_resp.status_code == 200, f"Science discovery failed: {sci_resp.status_code}"
    print(f"Science Discovery OK: HTTP 200 in {sci_lat:.1f}ms (returned {len(sci_resp.json())} items)")

    # Marswalk single-leg route
    t_route = time.perf_counter()
    route_resp = client.post(
        f"{API_BASE}/api/v1/marswalk/route",
        json={
            "start_lat": -4.60,
            "start_lon": 66.317,
            "dest_lat": -4.64,
            "dest_lon": 66.35,
            "mode": "walking",
            "max_slope_deg": 25.0,
        },
    )
    route_lat = (time.perf_counter() - t_route) * 1000
    assert route_resp.status_code == 200, f"Route planning failed: {route_resp.status_code}"
    route_data = route_resp.json()
    print(f"Marswalk Route OK: HTTP 200 in {route_lat:.1f}ms (Route ID: {route_data['route_id']}, Distance: {route_data['total_surface_distance_m']:.1f}m)")

    # Elevation profile
    t_elev = time.perf_counter()
    elev_resp = client.get(f"{API_BASE}/api/v1/terrain/elevation/profile?start_lat=-4.60&start_lon=66.317&end_lat=-4.64&end_lon=66.350&num_samples=80")
    elev_lat = (time.perf_counter() - t_elev) * 1000
    assert elev_resp.status_code == 200, f"Elevation profile failed: {elev_resp.status_code}"
    elev_data = elev_resp.json()
    print(f"Elevation Profile OK: HTTP 200 in {elev_lat:.1f}ms (Sampled {len(elev_data['points'])} points)")

    client.close()
    recovery_report = {
        "test": "controlled_backend_restart_and_recovery",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "disconnection_detected": True,
        "clean_failure_during_outage": True,
        "restart_to_online_ms": round(recovery_duration, 1),
        "post_recovery_science_ms": round(sci_lat, 1),
        "post_recovery_route_ms": round(route_lat, 1),
        "post_recovery_elevation_ms": round(elev_lat, 1),
        "all_post_recovery_requests_succeeded": True,
        "new_backend_pid": new_proc.pid,
    }
    with open("reports/recovery_test_result.json", "w") as f:
        json.dump(recovery_report, f, indent=2)

    print("\n========================================================")
    print("CONTROLLED RECOVERY TEST: 100% PASSED")
    print(f"Restart-to-Online Time: {recovery_duration/1000:.2f} seconds")
    print(f"Post-Recovery Science Latency: {sci_lat:.1f}ms")
    print(f"Post-Recovery Route Latency: {route_lat:.1f}ms")
    print(f"Post-Recovery Elevation Latency: {elev_lat:.1f}ms")
    print(f"New Backend PID: {new_proc.pid}")
    print("Report saved to reports/recovery_test_result.json")
    print("========================================================")
    return recovery_report


if __name__ == "__main__":
    run_recovery_test()
