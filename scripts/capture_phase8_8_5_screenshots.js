const path = require("path");
const puppeteer = require(path.resolve(__dirname, "../frontend/node_modules/puppeteer"));

async function captureAll() {
  console.log("Launching Puppeteer browser for Phase 8.8.5 validation...");
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

  const screenshotsDir = path.resolve(__dirname, "../docs/research/screenshots");

  try {
    const page = await browser.newPage();

    // 1. 12_phase8_8_5_global_map.png
    console.log("1. Capturing 12_phase8_8_5_global_map.png...");
    await page.goto("http://localhost:3005/?tab=dashboard", {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    await new Promise((r) => setTimeout(r, 4000));
    const path12 = path.join(screenshotsDir, "12_phase8_8_5_global_map.png");
    await page.screenshot({ path: path12, fullPage: false });
    console.log(`Saved: ${path12}`);

    // 2. 13_phase8_8_5_single_route.png
    console.log("2. Capturing 13_phase8_8_5_single_route.png...");
    await page.goto("http://localhost:3005/?tab=route", {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    await new Promise((r) => setTimeout(r, 3000));

    // Click "Generate Marswalk Route"
    const buttons = await page.$$("button");
    for (const btn of buttons) {
      const text = await page.evaluate((el) => el.innerText, btn);
      if (text && text.includes("Generate Marswalk Route")) {
        console.log("Found and clicking 'Generate Marswalk Route' button...");
        await btn.click();
        await new Promise((r) => setTimeout(r, 5000));
        break;
      }
    }
    const path13 = path.join(screenshotsDir, "13_phase8_8_5_single_route.png");
    await page.screenshot({ path: path13, fullPage: false });
    console.log(`Saved: ${path13}`);

    // 3. 14_phase8_8_5_elevation_profile.png
    console.log("3. Capturing 14_phase8_8_5_elevation_profile.png...");
    // Switch to intelligence tab
    const tabButtons = await page.$$("button");
    for (const btn of tabButtons) {
      const text = await page.evaluate((el) => el.innerText, btn);
      if (text && (text.includes("Scientific Intelligence") || text.includes("Scientific Analysis"))) {
        console.log("Clicking Scientific Intelligence tab...");
        await btn.click();
        await new Promise((r) => setTimeout(r, 3000));
        break;
      }
    }
    const path14 = path.join(screenshotsDir, "14_phase8_8_5_elevation_profile.png");
    await page.screenshot({ path: path14, fullPage: false });
    console.log(`Saved: ${path14}`);

    // 4. 15_phase8_8_5_terrain_analysis.png
    console.log("4. Capturing 15_phase8_8_5_terrain_analysis.png...");
    // Scroll down to terrain intelligence section
    await page.evaluate(() => {
      window.scrollBy(0, 450);
    });
    await new Promise((r) => setTimeout(r, 1000));
    const path15 = path.join(screenshotsDir, "15_phase8_8_5_terrain_analysis.png");
    await page.screenshot({ path: path15, fullPage: false });
    console.log(`Saved: ${path15}`);

    // 5. 16_phase8_8_5_geological_context.png
    console.log("5. Capturing 16_phase8_8_5_geological_context.png...");
    await page.evaluate(() => {
      window.scrollBy(0, 500);
    });
    await new Promise((r) => setTimeout(r, 1000));
    const path16 = path.join(screenshotsDir, "16_phase8_8_5_geological_context.png");
    await page.screenshot({ path: path16, fullPage: false });
    console.log(`Saved: ${path16}`);

    // 6. 17_phase8_8_5_thermal_context.png
    console.log("6. Capturing 17_phase8_8_5_thermal_context.png...");
    await page.evaluate(() => {
      window.scrollBy(0, 500);
    });
    await new Promise((r) => setTimeout(r, 1000));
    const path17 = path.join(screenshotsDir, "17_phase8_8_5_thermal_context.png");
    await page.screenshot({ path: path17, fullPage: false });
    console.log(`Saved: ${path17}`);

    // 7. 18_phase8_8_5_multi_stop_route.png
    console.log("7. Capturing 18_phase8_8_5_multi_stop_route.png...");
    // Scroll back to top
    await page.evaluate(() => {
      window.scrollTo(0, 0);
    });
    await new Promise((r) => setTimeout(r, 1000));

    // Switch to Multi-Stop Traverse tab
    const multiButtons = await page.$$("button");
    for (const btn of multiButtons) {
      const text = await page.evaluate((el) => el.innerText, btn);
      if (text && text.includes("Multi-Stop Science Traverse")) {
        console.log("Clicking Multi-Stop Science Traverse tab...");
        await btn.click();
        await new Promise((r) => setTimeout(r, 2000));
        break;
      }
    }

    // Click "Calculate & Optimize Multi-Stop Traverse"
    const optButtons = await page.$$("button");
    for (const btn of optButtons) {
      const text = await page.evaluate((el) => el.innerText, btn);
      if (text && (text.includes("Calculate & Optimize") || text.includes("Optimize Multi-Stop"))) {
        console.log("Clicking Calculate & Optimize Traverse button...");
        await btn.click();
        await new Promise((r) => setTimeout(r, 8000));
        break;
      }
    }
    const path18 = path.join(screenshotsDir, "18_phase8_8_5_multi_stop_route.png");
    await page.screenshot({ path: path18, fullPage: false });
    console.log(`Saved: ${path18}`);

    // 8. 19_phase8_8_5_multi_stop_intelligence.png
    console.log("8. Capturing 19_phase8_8_5_multi_stop_intelligence.png...");
    // Click intelligence tab or button for multi-stop
    const intelBtns = await page.$$("button");
    for (const btn of intelBtns) {
      const text = await page.evaluate((el) => el.innerText, btn);
      if (text && (text.includes("Scientific Intelligence") || text.includes("Traverse Intelligence"))) {
        console.log("Clicking Traverse Intelligence view...");
        await btn.click();
        await new Promise((r) => setTimeout(r, 3000));
        break;
      }
    }
    const path19 = path.join(screenshotsDir, "19_phase8_8_5_multi_stop_intelligence.png");
    await page.screenshot({ path: path19, fullPage: false });
    console.log(`Saved: ${path19}`);

    // 9. 20_phase8_8_5_edge_case_handling.png
    console.log("9. Capturing 20_phase8_8_5_edge_case_handling.png...");
    // Go to single-leg tab, set an out-of-bounds or extreme condition to trigger error alert
    const singleBtns = await page.$$("button");
    for (const btn of singleBtns) {
      const text = await page.evaluate((el) => el.innerText, btn);
      if (text && text.includes("Single Destination")) {
        await btn.click();
        await new Promise((r) => setTimeout(r, 1000));
        break;
      }
    }

    // Set max slope to 1 degree on Tyrrhena to trigger impassable terrain error
    await page.evaluate(() => {
      const inputs = document.querySelectorAll("input[type='number']");
      for (const inp of inputs) {
        if (inp.value === "25" || inp.value === "20") {
          inp.value = "1.0";
          inp.dispatchEvent(new Event("input", { bubbles: true }));
          inp.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
    });

    // Click Generate Marswalk Route
    const genBtns = await page.$$("button");
    for (const btn of genBtns) {
      const text = await page.evaluate((el) => el.innerText, btn);
      if (text && text.includes("Generate Marswalk Route")) {
        await btn.click();
        await new Promise((r) => setTimeout(r, 3000));
        break;
      }
    }
    const path20 = path.join(screenshotsDir, "20_phase8_8_5_edge_case_handling.png");
    await page.screenshot({ path: path20, fullPage: false });
    console.log(`Saved: ${path20}`);

    console.log("All 9 screenshots captured successfully!");
  } finally {
    await browser.close();
  }
}

captureAll().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
