// Render each .panel in diagrams.html to a crisp 2x PNG using the preinstalled Chromium.
//   npm i puppeteer-core   (then)   node render.mjs
import puppeteer from 'puppeteer-core';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const OUT = join(__dirname, '..', 'img');

const browser = await puppeteer.launch({
  executablePath: CHROME,
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--force-color-profile=srgb'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 2 });
await page.goto('file://' + join(__dirname, 'diagrams.html'), { waitUntil: 'networkidle0' });

const panels = { '1-problem': '#d1', '2-fix': '#d2', '3-under-hood': '#d3' };
for (const [name, sel] of Object.entries(panels)) {
  const el = await page.$(sel);
  await el.screenshot({ path: join(OUT, `visual-${name}.png`) });
  console.log('wrote', `visual-${name}.png`);
}
await browser.close();
