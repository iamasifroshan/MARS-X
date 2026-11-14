const path = require("path");
const puppeteer = require(path.resolve(__dirname, "../frontend/node_modules/puppeteer"));

async function capture() {
  console.log("Launching Puppeteer browser...");
  const browser = await puppeteer.launch({
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-web-security",
      "--enable-webgl",
      "--ignore-gpu-blocklist",
    ],
    defaultViewport: { width: 1440, height: 900 },
  });

  try {
    const page = await browser.newPage();

    // 1. Capture Science Explorer Panel
    console.log("Navigating to Science Discovery panel...");
    await page.goto("http://localhost:3005/?tab=discovery", {
      waitUntil: "networkidle2",
      timeout: 30000,
    });
    // Wait for candidate discoveries to load
    await page.waitForSelector("h1", { timeout: 10000 });
    await new Promise((r) => setTimeout(r, 3000));

    const path1 = path.resolve(__dirname, "../docs/research/screenshots/08_science_explorer_panel.png");
    await page.screenshot({ path: path1, fullPage: false });
    console.log(`Saved screenshot 1 to: ${path1}`);

    // 2. Capture Discovery Map Markers and Docked Drawer
    console.log("Navigating to Map with Discovery Drawer...");
    await page.goto("http://localhost:3005/?tab=dashboard&drawer=discovery", {
      waitUntil: "networkidle2",
      timeout: 30000,
    });
    // Wait for map canvas and drawer
    await new Promise((r) => setTimeout(r, 4000));

    const path2 = path.resolve(__dirname, "../docs/research/screenshots/09_discovery_map_markers.png");
    await page.screenshot({ path: path2, fullPage: false });
    console.log(`Saved screenshot 2 to: ${path2}`);

    console.log("All screenshots captured successfully!");
  } finally {
    await browser.close();
  }
}

capture().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
