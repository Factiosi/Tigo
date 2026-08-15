/**
 * Generate raster assets from SVG sources in icons/.
 * Usage: cd tools && npm install && node generate_icons.mjs
 */

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Resvg } from "@resvg/resvg-js";
import pngToIco from "png-to-ico";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const ICONS = join(ROOT, "icons");

function rasterize(svgPath, size) {
  const svg = readFileSync(svgPath, "utf8");
  const resvg = new Resvg(svg, {
    fitTo: { mode: "width", value: size },
  });
  return resvg.render().asPng();
}

async function writePng(svgRel, pngRel, size) {
  const png = rasterize(join(ICONS, svgRel), size);
  const out = join(ICONS, pngRel);
  writeFileSync(out, png);
  console.log(`OK ${pngRel}`);
}

async function writeIco(svgRel, icoRel) {
  const sizes = [16, 32, 48, 64, 128, 256];
  const pngs = sizes.map((size) => rasterize(join(ICONS, svgRel), size));
  const ico = await pngToIco(pngs);
  writeFileSync(join(ICONS, icoRel), ico);
  console.log(`OK ${icoRel}`);
}

await writePng("tray-active.svg", "tray-active.png", 64);
await writePng("tray-idle.svg", "tray-idle.png", 64);
await writeIco("app.svg", "app.ico");

const menuIcons = [
  ["menu/start.svg", "menu/start.png"],
  ["menu/stop.svg", "menu/stop.png"],
  ["menu/open.svg", "menu/open.png"],
  ["menu/quit.svg", "menu/quit.png"],
];
for (const [svgRel, pngRel] of menuIcons) {
  await writePng(svgRel, pngRel, 16);
}
