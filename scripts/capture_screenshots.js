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
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    await new Promise((r) => setTimeout(r, 3000));

    const path1 = path.resolve(__dirname, "../docs/research/screenshots/08_science_explorer_panel.png");
    await page.screenshot({ path: path1, fullPage: false });
    console.log(`Saved screenshot 1 to: ${path1}`);

    // 2. Capture Discovery Map Markers and Docked Drawer
    console.log("Navigating to Map with Discovery Drawer...");
    await page.goto("http://localhost:3005/?tab=dashboard&drawer=discovery", {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    await new Promise((r) => setTimeout(r, 4000));

    const path2 = path.resolve(__dirname, "../docs/research/screenshots/09_discovery_map_markers.png");
    await page.screenshot({ path: path2, fullPage: false });
    console.log(`Saved screenshot 2 to: ${path2}`);

    // 3. Capture Traversability Panel
    console.log("Navigating to Terrain Traversability panel...");
    await page.goto("http://localhost:3005/?tab=terrain", {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    await new Promise((r) => setTimeout(r, 4000));

    const path3 = path.resolve(__dirname, "../docs/research/screenshots/10_terrain_traversability_panel.png");
    await page.screenshot({ path: path3, fullPage: false });
    console.log(`Saved screenshot 3 to: ${path3}`);

    // 4. Capture Marswalk Route Planning Panel
    console.log("Navigating to Marswalk Route Planning panel...");
    await page.goto("http://localhost:3005/?tab=route", {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    await new Promise((r) => setTimeout(r, 4000));

    // Click "Generate Marswalk Route" button
    try {
      const buttonSelector = "button";
      const buttons = await page.$$(buttonSelector);
      for (const btn of buttons) {
        const text = await page.evaluate((el) => el.innerText, btn);
        if (text && text.includes("Generate Marswalk Route")) {
          console.log("Clicking Generate Marswalk Route button...");
          await btn.click();
          await new Promise((r) => setTimeout(r, 3000));
          break;
        }
      }
    } catch (e) {
      console.warn("Could not trigger route button click:", e.message);
    }

    const path4 = path.resolve(__dirname, "../docs/research/screenshots/11_marswalk_route_planner.png");
    await page.screenshot({ path: path4, fullPage: false });
    console.log(`Saved screenshot 4 to: ${path4}`);

    console.log("All screenshots captured successfully!");
  } finally {
    await browser.close();
  }
}

capture().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
