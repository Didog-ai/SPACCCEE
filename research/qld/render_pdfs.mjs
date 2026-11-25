// Render every out/catalogues/*.html to a PDF next to it. Run: node research/qld/render_pdfs.mjs
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import { readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = join(dirname(fileURLToPath(import.meta.url)), 'out', 'catalogues');
const browser = await chromium.launch();
const page = await browser.newPage();
for (const f of readdirSync(dir).filter((f) => f.endsWith('.html'))) {
  await page.goto('file://' + join(dir, f));
  await page.pdf({ path: join(dir, `Pinnacle-Trailers-Range-${f.replace('.html', '')}.pdf`), format: 'A4', printBackground: true });
  console.log('pdf', f);
}
await browser.close();
