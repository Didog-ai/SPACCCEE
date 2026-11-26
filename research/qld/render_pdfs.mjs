// Render every out/catalogues/*.html to a PDF next to it, plus a JPEG of each page in out/previews/
// (the sales pack shows those images, because the artifact viewer can't open PDFs).
// Run: node research/qld/render_pdfs.mjs [market_dir]   (default: research/qld)
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import { readdirSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { resolve } from 'node:path';
const out = join(process.argv[2] ? resolve(process.argv[2]) : dirname(fileURLToPath(import.meta.url)), 'out');
const dir = join(out, 'catalogues');
const previews = join(out, 'previews');
mkdirSync(previews, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 1.4 });
for (const f of readdirSync(dir).filter((f) => f.endsWith('.html'))) {
  const id = f.replace('.html', '');
  await page.goto('file://' + join(dir, f));
  await page.pdf({ path: join(dir, `Pinnacle-Trailers-Range-${id}.pdf`), format: 'A4', printBackground: true });
  const pages = page.locator('section.page');
  const n = await pages.count();
  for (let i = 0; i < n; i++) {
    await pages.nth(i).screenshot({ path: join(previews, `${id}-p${i + 1}.jpg`), type: 'jpeg', quality: 72 });
  }
  console.log('pdf + previews', f, n);
}
await browser.close();
