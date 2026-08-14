/**
 * Generate tigo.ico and tray PNGs from SVG.
 * Usage: cd tools && npm install && node generate_logos.mjs
 */

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Resvg } from "@resvg/resvg-js";
import pngToIco from "png-to-ico";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const LOGOS = join(ROOT, "logos");

function rasterize(svgPath, size) {
  const svg = readFileSync(svgPath, "utf8");
  const resvg = new Resvg(svg, {
    fitTo: { mode: "width", value: size },
  });
  return resvg.render().asPng();
}

async function writeTray(svgRel, pngRel, size = 64) {
  const png = rasterize(join(LOGOS, svgRel), size);
  const out = join(LOGOS, pngRel);
  writeFileSync(out, png);
  console.log(`OK ${pngRel}`);
}

async function writeIco(svgRel, icoRel) {
  const sizes = [16, 32, 48, 64, 128, 256];
  const pngs = sizes.map((size) => rasterize(join(LOGOS, svgRel), size));
  const ico = await pngToIco(pngs);
  writeFileSync(join(LOGOS, icoRel), ico);
  console.log(`OK ${icoRel}`);
}

await writeTray("online/tigo-small.svg", "online/tigo-tray.png");
await writeTray("offline/tigo-small.svg", "offline/tigo-tray.png");
await writeIco("online/tigo.svg", "online/tigo.ico");
