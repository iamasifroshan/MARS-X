// scripts/test_deployed_backend.mjs
const backendUrl = 'https://mars-x-backend.onrender.com';

async function testFrontendCalls() {
  const endpoints = [
    { name: 'Health Check', path: '/health' },
    { name: 'API Status', path: '/api/v1/status' },
    { name: 'Dataset Catalogue', path: '/api/v1/datasets' },
    { name: 'THEMIS Metadata', path: '/api/v1/themis/metadata' },
    { name: 'Environmental Metadata', path: '/api/v1/environmental/metadata' },
    { name: 'Atmospheric Pressure Estimate', path: '/api/v1/environmental/pressure/estimate?elevation_m=2000' },
    { name: 'Solar Geometry Calculation', path: '/api/v1/environmental/solar-geometry?lat=-4.6&lon=66.3&ls_deg=90' },
    { name: 'MCD Climatology Coverage', path: '/api/v1/environmental/climatology/coverage' },
    { name: 'Candidate Science Discoveries', path: '/api/v1/discovery/list' },
  ];

  console.log(`[MARS-X] Testing frontend queries to deployed cloud backend: ${backendUrl}\n`);
  let successCount = 0;

  for (const ep of endpoints) {
    const t0 = Date.now();
    try {
      const res = await fetch(`${backendUrl}${ep.path}`, {
        headers: { Accept: 'application/json' },
      });
      const elapsed = Date.now() - t0;
      const data = await res.json();
      const summary = Array.isArray(data) ? `Array(${data.length})` : typeof data === 'object' && data !== null ? `Object(${Object.keys(data).length} keys)` : String(data);
      console.log(`PASS [HTTP ${res.status}] ${ep.name.padEnd(30)} -> ${elapsed}ms | ${summary}`);
      if (res.ok) successCount++;
    } catch (err) {
      console.error(`FAIL: ${ep.name} (${ep.path}) -> ${err.message}`);
    }
  }

  console.log(`\n[MARS-X] Results: ${successCount}/${endpoints.length} endpoints succeeded.`);
  if (successCount !== endpoints.length) {
    process.exit(1);
  }
}

testFrontendCalls();
