async function test() {
  const endpoints = [
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8000/api/v1/status",
    "http://127.0.0.1:8000/api/v1/discovery/list?limit=5",
    "http://127.0.0.1:8000/api/v1/terrain/elevation/profile?start_lat=-4.60&start_lon=66.317&end_lat=-4.64&end_lon=66.350&num_samples=80",
    "http://127.0.0.1:8000/api/v1/terrain/layers",
    "http://127.0.0.1:8000/api/v1/marswalk/multi-stop/metadata",
    "http://127.0.0.1:8000/api/v1/environmental/metadata"
  ];
  for (const url of endpoints) {
    const t0 = Date.now();
    try {
      const res = await fetch(url, { headers: { Origin: "http://localhost:3005" } });
      const elapsed = Date.now() - t0;
      console.log(`${res.status} [${elapsed}ms] ${url.split("?")[0]} CORS: ${res.headers.get("access-control-allow-origin")}`);
    } catch (e) {
      console.error(`FAILED: ${url}`, e.message);
    }
  }

  // Test Marswalk POST
  const t0 = Date.now();
  const routeRes = await fetch("http://127.0.0.1:8000/api/v1/marswalk/route", {
    method: "POST",
    headers: { "Content-Type": "application/json", Origin: "http://localhost:3005" },
    body: JSON.stringify({
      start_lat: -4.60,
      start_lon: 66.317,
      dest_lat: -4.64,
      dest_lon: 66.35,
      mode: "walking",
      max_slope_deg: 25.0
    })
  });
  const routeElapsed = Date.now() - t0;
  console.log(`${routeRes.status} [${routeElapsed}ms] /api/v1/marswalk/route CORS: ${routeRes.headers.get("access-control-allow-origin")}`);
  if (routeRes.ok) {
    const data = await routeRes.json();
    console.log(`Route ID: ${data.route_id}, Status: ${data.status}, Length: ${data.total_distance_m}m`);
    console.log("Keys in route response:", Object.keys(data));
    
    // Test Route Intelligence
    const t1 = Date.now();
    const intelRes = await fetch(`http://127.0.0.1:8000/api/v1/marswalk/analysis/route/${encodeURIComponent(data.route_id)}`, {
      headers: { Origin: "http://localhost:3005" }
    });
    const intelElapsed = Date.now() - t1;
    console.log(`${intelRes.status} [${intelElapsed}ms] /api/v1/marswalk/analysis/route/${data.route_id} CORS: ${intelRes.headers.get("access-control-allow-origin")}`);
    if (intelRes.ok) {
      const intel = await intelRes.json();
      console.log("Intelligence units:", intel.geological_units?.length, "science targets:", intel.summary?.science_opportunity_count);
    }
  } else {
    console.error("Route error:", await routeRes.text());
  }
}

test();
