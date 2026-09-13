/* Capture ContractIQ UI screenshots for the presentation deck. */
const { chromium } = require("playwright");
const fs = require("fs");
const BASE = "http://localhost:5173";
const OUT = "D:/ContractIQ/reports/deck_assets";
const CID = "6e60c2ff5ca94b03bf0321cefa1eab3f";

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 900 },
    deviceScaleFactor: 2,
  });

  const shots = [
    ["overview", `${BASE}/`, 9000],
    ["analyze", `${BASE}/analyze`, 5000],
    ["detail", `${BASE}/contracts/${CID}`, 9000],
    ["intelligence", `${BASE}/intelligence`, 5000],
  ];

  for (const [name, url, wait] of shots) {
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(wait);
    await page.screenshot({ path: `${OUT}/ui_${name}.png` });
    console.log("saved", name);
  }

  // Detail page: scroll the intelligence rail for the Risk Orb close-up
  await page.goto(`${BASE}/contracts/${CID}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(8000);
  const orb = await page.$('text=/Risk/i');
  fs.mkdirSync(OUT, { recursive: true });
  await browser.close();
  console.log("done");
})().catch((e) => { console.error(e); process.exit(1); });
