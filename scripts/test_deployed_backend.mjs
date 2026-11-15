// scripts/test_deployed_backend.mjs
const backendUrl = process.argv[2] || 'https://mars-x-backend.onrender.com';

async function testFrontendCalls() {
  const endpoints = [
    { name: 'Health Check', path: '/health', method: 'GET' },
    { name: 'API Status', path: '/api/v1/status', method: 'GET' },
    { name: 'Dataset Catalogue', path: '/api/v1/datasets', method: 'GET' },
    { name: 'THEMIS Metadata', path: '/api/v1/themis/metadata', method: 'GET' },
    { name: 'Environmental Metadata', path: '/api/v1/environmental/metadata', method: 'GET' },
    { name: 'Atmospheric Pressure Estimate', path: '/api/v1/environmental/pressure/estimate?elevation_m=2000', method: 'GET' },
    { name: 'Solar Geometry Calculation', path: '/api/v1/environmental/solar-geometry?lat=-4.6&lon=66.3&ls_deg=90', method: 'GET' },
    { name: 'MCD Climatology Coverage', path: '/api/v1/environmental/climatology/coverage', method: 'GET' },
    { name: 'Candidate Science Discoveries', path: '/api/v1/discovery/list', method: 'GET' },
    { name: 'System Storage Diagnostics', path: '/api/v1/system/storage', method: 'GET' },
    { name: 'Marswalk Metadata', path: '/api/v1/marswalk/metadata', method: 'GET' },
    { name: 'Elevation Profile', path: '/api/v1/terrain/elevation/profile?start_lat=-4.600&start_lon=66.317&end_lat=-4.605&end_lon=66.325&num_samples=10', method: 'GET' },
    { name: 'Point Elevation', path: '/api/v1/terrain/elevation/point?lat=-4.6&lon=66.317', method: 'GET' },
    {
      name: 'Marswalk Route',
      path: '/api/v1/marswalk/route',
      method: 'POST',
      body: {
        source_dataset: 'ctx-tyrrhena',
        start_lat: -4.600,
        start_lon: 66.317,
        dest_lat: -4.605,
        dest_lon: 66.325,
      },
    },
    { name: 'TES Thermal Point', path: '/api/v1/thermal/point?lat=-4.6&lon=66.317', method: 'GET' },
  ];

  console.log(`[MARS-X] Testing API endpoints against: ${backendUrl}\n`);
  let successCount = 0;

  for (const ep of endpoints) {
    const t0 = Date.now();
    try {
      const opts = {
        method: ep.method,
        headers: { Accept: 'application/json' },
      };
      if (ep.body) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(ep.body);
      }

      const res = await fetch(`${backendUrl}${ep.path}`, opts);
      const elapsed = Date.now() - t0;
      const data = await res.json();
      const summary = Array.isArray(data)
        ? `Array(${data.length})`
        : typeof data === 'object' && data !== null
        ? `Object(${Object.keys(data).length} keys)`
        : String(data);

      const isExpected = res.ok || (res.status === 503 && data.detail && data.detail.includes('unavailable'));
      const statusLabel = res.ok ? 'PASS' : res.status === 503 ? 'INFO-503' : 'WARN';
      console.log(`[HTTP ${res.status}] ${statusLabel.padEnd(8)} ${ep.name.padEnd(32)} -> ${elapsed}ms | ${summary}`);
      if (res.ok) successCount++;
    } catch (err) {
      console.error(`FAIL: ${ep.name} (${ep.path}) -> ${err.message}`);
    }
  }

  console.log(`\n[MARS-X] Results: ${successCount}/${endpoints.length} endpoints succeeded (HTTP 200).`);
}

testFrontendCalls();
