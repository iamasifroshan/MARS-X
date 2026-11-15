// Test all frontend API calls against the live backend
const API_BASE = "http://127.0.0.1:8000";

async function testEndpoint(name, url, options = {}) {
    const t0 = Date.now();
    try {
        const res = await fetch(url, {
            ...options,
            headers: {
                "Origin": "http://localhost:3005",
                ...(options.headers || {})
            }
        });
        const duration = Date.now() - t0;
        const cors = res.headers.get("access-control-allow-origin");
        console.log(`[PASS] ${name}: ${res.status} in ${duration}ms (CORS: ${cors})`);
        return true;
    } catch (err) {
        const duration = Date.now() - t0;
        console.error(`[FAIL] ${name}: ${err.message} in ${duration}ms`);
        return false;
    }
}

async function run() {
    console.log("Testing API endpoints from origin http://localhost:3005...");
    
    // 1. Health
    await testEndpoint("Health check", `${API_BASE}/health`);
    
    // 2. Status
    await testEndpoint("Status check", `${API_BASE}/api/v1/status`);

    // 3. Discovery categories
    await testEndpoint("Discovery Categories", `${API_BASE}/api/v1/discovery/categories`);

    // 4. Discovery list
    await testEndpoint("Discovery List", `${API_BASE}/api/v1/discovery/list`);

    // 5. Marswalk metadata
    await testEndpoint("Marswalk Metadata", `${API_BASE}/api/v1/marswalk/metadata`);

    // 6. Marswalk Route (Single Leg)
    await testEndpoint("Marswalk Route Planning", `${API_BASE}/api/v1/marswalk/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            start_lat: -4.6,
            start_lon: 66.317,
            dest_lat: -4.605,
            dest_lon: 66.325,
            preferred_source: "ctx-tyrrhena",
            slope_penalty_factor: 2.0,
            max_slope_deg: 25.0
        })
    });

    // 7. Elevation profile
    await testEndpoint("Elevation Profile (80 samples)", `${API_BASE}/api/v1/terrain/elevation/profile?start_lat=-4.6&start_lon=66.317&end_lat=-4.64&end_lon=66.35&num_samples=80`);

    // 8. Climatology point
    await testEndpoint("Climatology Point", `${API_BASE}/api/v1/environmental/climatology/point?lat=18.38&lon=77.58&ls_deg=90.0&ltst_hours=14.0`);
}

run();
