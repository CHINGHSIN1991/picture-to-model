// Step 09: screenshot the HTML mockup sources (mockups/src/homepage-0N.html) into
// mockups/homepage-0N.png (1440 wide, full page) and homepage-0N-mobile.png (390 wide).
// Runs from web/ so it can reuse the installed Playwright: `bun run mockups`.
import { chromium } from '@playwright/test'
import { readdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const src = new URL('../../mockups/src/', import.meta.url)
const out = new URL('../../mockups/', import.meta.url)
const only = process.argv.slice(2)
const pages = (await readdir(src)).filter((f) => /^homepage-\d\d\.html$/.test(f)).sort()
  .filter((f) => !only.length || only.includes(f.replace('.html', '')))
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
const report = []
try {
  for (const file of pages) {
    const name = file.replace('.html', '')
    for (const [suffix, viewport] of [['', { width: 1440, height: 900 }], ['-mobile', { width: 390, height: 844 }]]) {
      const page = await browser.newPage({ viewport, deviceScaleFactor: 1 })
      await page.goto(new URL(file, src).href, { waitUntil: 'networkidle' })
      await page.evaluate(() => document.fonts.ready)
      const path = fileURLToPath(new URL(`${name}${suffix}.png`, out))
      await page.screenshot({ path, fullPage: true })
      const size = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.scrollHeight])
      report.push({ file: `${name}${suffix}.png`, viewport, page: size })
      await page.close()
    }
  }
} finally {
  await browser.close()
}
await writeFile(new URL('render-report.json', out), `${JSON.stringify({ renderedAt: new Date().toISOString(), pages: report }, null, 2)}\n`)
console.log(JSON.stringify(report, null, 2))
