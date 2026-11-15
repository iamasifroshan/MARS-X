"""Continuous Backend Stability & Resource Monitoring Harness for MARS-X.

Runs continuous multi-endpoint load, concurrency bursts, and OS process resource
monitoring against the FastAPI backend (http://127.0.0.1:8000) for a specified duration
(e.g., 31 minutes / 1860 seconds).
"""

import sys
import os
import time
import json
import argparse
import statistics
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
import psutil


API_BASE = "http://127.0.0.1:8000"

# Target endpoints and payloads
SAMPLE_PAYLOADS = {
    "marswalk_tyrrhena_1": {
        "start_lat": -4.600,
        "start_lon": 66.317,
        "dest_lat": -4.640,
        "dest_lon": 66.350,
        "mode": "walking",
        "max_slope_deg": 25.0,
    },
    "marswalk_tyrrhena_2": {
        "start_lat": -4.610,
        "start_lon": 66.320,
        "dest_lat": -4.630,
        "dest_lon": 66.340,
        "mode": "walking",
        "max_slope_deg": 25.0,
    },
    "elevation_mola": {
        "url": f"{API_BASE}/api/v1/terrain/elevation/profile?start_lat=-10.0&start_lon=120.0&end_lat=-10.5&end_lon=120.5&num_samples=50"
    },
    "elevation_ctx": {
        "url": f"{API_BASE}/api/v1/terrain/elevation/profile?start_lat=-4.60&start_lon=66.317&end_lat=-4.64&end_lon=66.350&num_samples=80"
    },
    "discovery_list": f"{API_BASE}/api/v1/discovery/list?limit=10",
    "discovery_categories": f"{API_BASE}/api/v1/discovery/categories",
    "discovery_profile": f"{API_BASE}/api/v1/discovery/profile?lat=-4.60&lon=66.317",
    "environmental_metadata": f"{API_BASE}/api/v1/environmental/metadata",
    "environmental_pressure": f"{API_BASE}/api/v1/environmental/pressure/estimate?elevation_m=-1500.0",
    "climatology_metadata": f"{API_BASE}/api/v1/environmental/climatology/metadata",
    "climatology_point": f"{API_BASE}/api/v1/environmental/climatology/point?lat=-4.60&lon=66.317&ls_deg=90.0&ltst_hours=14.0",
}


def find_uvicorn_proc(port: int = 8000) -> Optional[psutil.Process]:
    """Find the psutil.Process instance running Uvicorn on the specified port."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(proc.info["cmdline"] or [])
            if "uvicorn" in cmd and "app.main:app" in cmd and "python" in proc.info["name"].lower():
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


class MetricsTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.categories: Dict[str, List[float]] = {
            "health": [],
            "status": [],
            "discovery": [],
            "elevation_profile": [],
            "marswalk_route": [],
            "environmental": [],
            "climatology": [],
        }
        self.counts = {
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0,
            "timeouts": 0,
            "connection_refused": 0,
        }
        self.status_codes: Dict[int, int] = {}
        self.failure_events: List[Dict[str, Any]] = []
        self.resource_samples: List[Dict[str, Any]] = []

    def record_response(self, category: str, latency_ms: float, status_code: Optional[int], error_msg: Optional[str] = None):
        with self.lock:
            self.counts["total_requests"] += 1
            if status_code and 200 <= status_code < 400:
                self.counts["success_requests"] += 1
                if category in self.categories:
                    self.categories[category].append(latency_ms)
            else:
                self.counts["failed_requests"] += 1
                event = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "category": category,
                    "status_code": status_code,
                    "latency_ms": round(latency_ms, 2),
                    "error": error_msg,
                }
                self.failure_events.append(event)
                if "timed out" in (error_msg or "").lower():
                    self.counts["timeouts"] += 1
                if "connection" in (error_msg or "").lower():
                    self.counts["connection_refused"] += 1

            if status_code:
                self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

    def record_resource_sample(self, sample: Dict[str, Any]):
        with self.lock:
            self.resource_samples.append(sample)

    def compute_summary(self, elapsed_seconds: float) -> Dict[str, Any]:
        with self.lock:
            cat_stats = {}
            for cat, latencies in self.categories.items():
                if latencies:
                    sorted_lat = sorted(latencies)
                    cat_stats[cat] = {
                        "count": len(latencies),
                        "min_ms": round(min(sorted_lat), 2),
                        "median_ms": round(statistics.median(sorted_lat), 2),
                        "mean_ms": round(statistics.mean(sorted_lat), 2),
                        "p95_ms": round(sorted_lat[int(len(sorted_lat) * 0.95)], 2),
                        "max_ms": round(max(sorted_lat), 2),
                    }
                else:
                    cat_stats[cat] = {"count": 0}

            # Resource metrics
            mem_rss_samples = [s["memory_rss_mb"] for s in self.resource_samples if "memory_rss_mb" in s]
            cpu_samples = [s["cpu_pct"] for s in self.resource_samples if "cpu_pct" in s]
            handle_samples = [s.get("num_handles", 0) for s in self.resource_samples if "num_handles" in s]

            return {
                "elapsed_seconds": round(elapsed_seconds, 1),
                "counts": self.counts,
                "status_codes": self.status_codes,
                "category_latency_stats": cat_stats,
                "failure_events_count": len(self.failure_events),
                "failure_events": self.failure_events,
                "resource_summary": {
                    "total_samples": len(self.resource_samples),
                    "memory_rss_mb": {
                        "initial": round(mem_rss_samples[0], 2) if mem_rss_samples else None,
                        "peak": round(max(mem_rss_samples), 2) if mem_rss_samples else None,
                        "final": round(mem_rss_samples[-1], 2) if mem_rss_samples else None,
                    },
                    "cpu_pct": {
                        "mean": round(statistics.mean(cpu_samples), 2) if cpu_samples else None,
                        "peak": round(max(cpu_samples), 2) if cpu_samples else None,
                    },
                    "open_handles": {
                        "initial": handle_samples[0] if handle_samples else None,
                        "peak": max(handle_samples) if handle_samples else None,
                        "final": handle_samples[-1] if handle_samples else None,
                    },
                },
            }


def run_single_request(client: httpx.Client, category: str, method: str, url: str, tracker: MetricsTracker, json_body: Optional[dict] = None):
    t0 = time.perf_counter()
    status_code = None
    err_str = None
    try:
        if method == "GET":
            resp = client.get(url, timeout=15.0)
        else:
            resp = client.post(url, json=json_body, timeout=30.0)
        status_code = resp.status_code
        if status_code >= 400:
            err_str = f"HTTP {status_code}: {resp.text[:200]}"
    except Exception as e:
        err_str = f"{type(e).__name__}: {str(e)}"
    finally:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        tracker.record_response(category, latency_ms, status_code, err_str)


def run_stability_monitor(duration_seconds: int = 1860, report_dir: str = "reports"):
    os.makedirs(report_dir, exist_ok=True)
    telemetry_path = os.path.join(report_dir, "stability_30min_telemetry.json")
    summary_path = os.path.join(report_dir, "stability_30min_summary.json")

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting MARS-X Continuous Stability & Reliability Test")
    print(f"Target duration: {duration_seconds} seconds ({duration_seconds / 60:.1f} minutes)")
    print(f"Backend API Base: {API_BASE}")

    tracker = MetricsTracker()
    start_time = time.time()
    last_checkpoint = start_time
    last_resource_sample = start_time
    cycle_count = 0

    uvicorn_proc = find_uvicorn_proc(8000)
    if uvicorn_proc:
        print(f"Identified Uvicorn process: PID {uvicorn_proc.pid} ({uvicorn_proc.name()})")
    else:
        print("Warning: Could not initially identify Uvicorn PID on port 8000. Will rescan during loop.")

    # Create reusable HTTP client with keep-alive
    client = httpx.Client(headers={"Origin": "http://localhost:3005", "Accept": "application/json"})

    try:
        while True:
            now = time.time()
            elapsed = now - start_time
            if elapsed >= duration_seconds:
                print(f"\nTarget duration of {duration_seconds}s reached. Concluding test.")
                break

            cycle_count += 1

            # 1. Sample process resources every 5 seconds
            if now - last_resource_sample >= 5.0:
                last_resource_sample = now
                if not uvicorn_proc or not uvicorn_proc.is_running():
                    uvicorn_proc = find_uvicorn_proc(8000)

                if uvicorn_proc and uvicorn_proc.is_running():
                    try:
                        mem = uvicorn_proc.memory_info()
                        cpu = uvicorn_proc.cpu_percent(interval=None)
                        num_handles = uvicorn_proc.num_handles() if hasattr(uvicorn_proc, "num_handles") else None
                        num_threads = uvicorn_proc.num_threads()
                        sample = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "elapsed_s": round(elapsed, 1),
                            "pid": uvicorn_proc.pid,
                            "is_running": True,
                            "cpu_pct": cpu,
                            "memory_rss_mb": round(mem.rss / (1024 * 1024), 2),
                            "memory_vms_mb": round(mem.vms / (1024 * 1024), 2),
                            "num_handles": num_handles,
                            "num_threads": num_threads,
                            "port_8000_listening": True,
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        sample = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "elapsed_s": round(elapsed, 1),
                            "is_running": False,
                            "port_8000_listening": False,
                        }
                else:
                    sample = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "elapsed_s": round(elapsed, 1),
                        "is_running": False,
                        "port_8000_listening": False,
                    }
                tracker.record_resource_sample(sample)

            # 2. Sequential / Interleaved Requests
            # Health check
            run_single_request(client, "health", "GET", f"{API_BASE}/health", tracker)
            # Status check
            run_single_request(client, "status", "GET", f"{API_BASE}/api/v1/status", tracker)

            # Discovery (alternate list, categories, profile)
            if cycle_count % 3 == 0:
                run_single_request(client, "discovery", "GET", SAMPLE_PAYLOADS["discovery_list"], tracker)
            elif cycle_count % 3 == 1:
                run_single_request(client, "discovery", "GET", SAMPLE_PAYLOADS["discovery_categories"], tracker)
            else:
                run_single_request(client, "discovery", "GET", SAMPLE_PAYLOADS["discovery_profile"], tracker)

            # Elevation profile (every 2 cycles)
            if cycle_count % 2 == 0:
                elev_url = SAMPLE_PAYLOADS["elevation_ctx"]["url"] if cycle_count % 4 == 0 else SAMPLE_PAYLOADS["elevation_mola"]["url"]
                run_single_request(client, "elevation_profile", "GET", elev_url, tracker)

            # Environmental / Climatology
            if cycle_count % 4 == 0:
                run_single_request(client, "environmental", "GET", SAMPLE_PAYLOADS["environmental_metadata"], tracker)
            elif cycle_count % 4 == 2:
                run_single_request(client, "climatology", "GET", SAMPLE_PAYLOADS["climatology_point"], tracker)

            # Marswalk Route planning (every 5 cycles)
            if cycle_count % 5 == 0:
                body = SAMPLE_PAYLOADS["marswalk_tyrrhena_1"] if (cycle_count // 5) % 2 == 0 else SAMPLE_PAYLOADS["marswalk_tyrrhena_2"]
                run_single_request(client, "marswalk_route", "POST", f"{API_BASE}/api/v1/marswalk/route", tracker, json_body=body)

            # 3. Concurrency Burst every 20 cycles: Launch 6 concurrent requests simultaneously
            if cycle_count % 20 == 0:
                burst_tasks = [
                    ("health", "GET", f"{API_BASE}/health", None),
                    ("status", "GET", f"{API_BASE}/api/v1/status", None),
                    ("discovery", "GET", SAMPLE_PAYLOADS["discovery_list"], None),
                    ("elevation_profile", "GET", SAMPLE_PAYLOADS["elevation_ctx"]["url"], None),
                    ("environmental", "GET", SAMPLE_PAYLOADS["environmental_pressure"], None),
                    ("marswalk_route", "POST", f"{API_BASE}/api/v1/marswalk/route", SAMPLE_PAYLOADS["marswalk_tyrrhena_1"]),
                ]
                threads = []
                for cat, meth, u, b in burst_tasks:
                    th = threading.Thread(target=run_single_request, args=(client, cat, meth, u, tracker, b))
                    th.start()
                    threads.append(th)
                for th in threads:
                    th.join(timeout=35.0)

            # 4. Periodic progress report & checkpoint save every 30 seconds
            if now - last_checkpoint >= 30.0:
                last_checkpoint = now
                summary = tracker.compute_summary(elapsed)
                with open(summary_path, "w") as f:
                    json.dump(summary, f, indent=2)

                print(
                    f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                    f"Elapsed: {elapsed:.0f}s / {duration_seconds}s ({elapsed/duration_seconds*100:.1f}%) | "
                    f"Total reqs: {tracker.counts['total_requests']} (Success: {tracker.counts['success_requests']}, Fail: {tracker.counts['failed_requests']}) | "
                    f"Health avg: {summary['category_latency_stats'].get('health', {}).get('mean_ms', 0):.1f}ms | "
                    f"Route p95: {summary['category_latency_stats'].get('marswalk_route', {}).get('p95_ms', 0):.1f}ms | "
                    f"Elev p95: {summary['category_latency_stats'].get('elevation_profile', {}).get('p95_ms', 0):.1f}ms | "
                    f"RAM: {summary['resource_summary']['memory_rss_mb'].get('final')} MB | "
                    f"CPU: {summary['resource_summary']['cpu_pct'].get('peak')}%",
                    flush=True,
                )

            # Brief sleep between cycles to keep request rate realistic (~1.5 requests/sec average)
            time.sleep(1.2)

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        client.close()
        elapsed_total = time.time() - start_time
        final_summary = tracker.compute_summary(elapsed_total)

        # Write final files
        with open(summary_path, "w") as f:
            json.dump(final_summary, f, indent=2)
        with open(telemetry_path, "w") as f:
            json.dump({
                "summary": final_summary,
                "resource_samples": tracker.resource_samples,
                "failure_events": tracker.failure_events,
            }, f, indent=2)

        print("\n========================================================")
        print("MARS-X CONTINUOUS STABILITY AUDIT COMPLETE")
        print(f"Total Elapsed Time: {elapsed_total:.1f} seconds ({elapsed_total/60:.2f} minutes)")
        print(f"Total Requests Dispatched: {tracker.counts['total_requests']}")
        print(f"Successful Requests (HTTP 2xx): {tracker.counts['success_requests']}")
        print(f"Failed Requests: {tracker.counts['failed_requests']}")
        print(f"Status Code Breakdown: {tracker.status_codes}")
        print("Category Performance Summary:")
        for cat, stats in final_summary["category_latency_stats"].items():
            print(f"  - {cat:20s}: {stats}")
        print("Resource Summary:")
        print(f"  - RSS Memory: {final_summary['resource_summary']['memory_rss_mb']}")
        print(f"  - Open Handles: {final_summary['resource_summary']['open_handles']}")
        print(f"  - Peak CPU: {final_summary['resource_summary']['cpu_pct']}")
        print(f"Reports saved to {summary_path} and {telemetry_path}")
        print("========================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MARS-X Continuous Stability Monitor")
    parser.add_argument("--duration", type=int, default=1860, help="Test duration in seconds (default: 1860s = 31 minutes)")
    parser.add_argument("--report-dir", type=str, default="reports", help="Directory to save telemetry and summary JSON")
    args = parser.parse_args()

    run_stability_monitor(duration_seconds=args.duration, report_dir=args.report_dir)
