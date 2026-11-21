// AURELIA — travel poster entry for "The Poster for a Place That Isn't There".
// The finished poster lives at assets/entry.png. This program copies it into
// the harness output folder so the grader finds it as entry.png.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const poster = join(here, "assets", "entry.png");
// The harness sets MAKEFUN_OUTPUT_DIR to its own writable folder; outside
// the harness the poster lands in /output, where the grader looks for it.
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
const target = join(outDir, "entry.png");

try {
  if (!existsSync(poster)) {
    throw new Error(`poster missing: ${poster}`);
  }
  mkdirSync(outDir, { recursive: true });
  copyFileSync(poster, target);
  console.log(`wrote ${target}`);
} catch (err) {
  console.error(
    `failed to write entry.png: ${err instanceof Error ? err.message : err}`,
  );
  process.exit(1);
}
