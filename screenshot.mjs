import puppeteer from "puppeteer";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.dirname(fileURLToPath(import.meta.url));
const site = process.argv[2];

if (!site) {
  const sitesDir = path.join(repoRoot, "sites");
  const available = fs.existsSync(sitesDir) ? fs.readdirSync(sitesDir) : [];
  console.error("Usage: node screenshot.mjs sites/<site-name> [url] [label]");
  if (available.length) console.error(`Available sites: ${available.join(", ")}`);
  process.exit(1);
}

const outDir = path.join(path.resolve(repoRoot, site), "temporary screenshots");
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

const url = process.argv[3] || "http://localhost:3000";
const label = process.argv[4];

function nextIndex() {
  const files = fs.existsSync(outDir) ? fs.readdirSync(outDir) : [];
  const nums = files
    .map((f) => f.match(/^screenshot-(\d+)/))
    .filter(Boolean)
    .map((m) => parseInt(m[1], 10));
  return (nums.length ? Math.max(...nums) : 0) + 1;
}

const browser = await puppeteer.launch();
const page = await browser.newPage();
await page.setViewport({ width: 470, height: 900 });
await page.goto(url, { waitUntil: "networkidle0" });

const n = nextIndex();
const fileName = label ? `screenshot-${n}-${label}.png` : `screenshot-${n}.png`;
const filePath = path.join(outDir, fileName);

await page.screenshot({ path: filePath, fullPage: true });
await browser.close();

console.log(`Saved ${filePath}`);
