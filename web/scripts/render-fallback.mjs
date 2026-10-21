// Step 14: capture the hero state from the live renderer and encode the stills as WebP.
// Same renderer, camera and lighting as the page, so the fallback matches the 3D composition.
// Usage: bun run dev (another terminal), then `bun run render:fallback`.
import { chromium } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'

const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:5173'
const output = new URL('../public/fallback/', import.meta.url)
const quality = Number(process.env.FALLBACK_QUALITY ?? 0.82)
// One composition per orientation; each is captured at 2x and downscaled for the 1x variant.
const compositions = [
  { name: 'portrait', width: 390, height: 844 },
  { name: 'landscape', width: 1440, height: 900 },
]
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
const errors = []
try {
  const report = []
  for (const composition of compositions) {
    // Device pixels at DPR 1 give the renderer a full-resolution 2x frame (the page caps DPR at 1.5).
    const page = await browser.newPage({ viewport: { width: composition.width * 2, height: composition.height * 2 }, deviceScaleFactor: 1 })
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
    // Freeze water and parts at their initial frame; `mode=live` overrides the reduced-motion rule.
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto(`${baseUrl}/?state=1&mode=live`)
    await page.locator('.site[data-state="ready"][data-mode="live"]').waitFor()
    await page.waitForTimeout(600)
    await page.addStyleTag({ content: 'main, .nav { visibility: hidden !important; }' })
    await page.waitForTimeout(100)
    const png = await page.screenshot({ type: 'png' })
    await page.close()
    // Chrome encodes WebP from a canvas; no native cwebp needed.
    const encoder = await browser.newPage()
    const encoded = await encoder.evaluate(async ({ png, width, height, quality }) => {
      const image = new Image()
      image.src = `data:image/png;base64,${png}`
      await image.decode()
      const encode = async (w, h) => {
        const canvas = document.createElement('canvas')
        canvas.width = w
        canvas.height = h
        const context = canvas.getContext('2d')
        context.imageSmoothingQuality = 'high'
        context.drawImage(image, 0, 0, w, h)
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/webp', quality))
        const dataUrl = await new Promise((resolve) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result)
          reader.readAsDataURL(blob)
        })
        return dataUrl.split(',')[1]
      }
      return { source: [image.naturalWidth, image.naturalHeight], x2: await encode(width * 2, height * 2), x1: await encode(width, height) }
    }, { png: png.toString('base64'), width: composition.width, height: composition.height, quality })
    await encoder.close()
    for (const [suffix, data] of [['@2x', encoded.x2], ['', encoded.x1]]) {
      const bytes = Buffer.from(data, 'base64')
      const name = `hero-${composition.name}${suffix}.webp`
      await writeFile(new URL(name, output), bytes)
      report.push({ file: name, bytes: bytes.length, size: suffix ? [composition.width * 2, composition.height * 2] : [composition.width, composition.height] })
    }
    console.log(`${composition.name}: captured ${encoded.source.join('×')} from the live hero`)
  }
  await writeFile(new URL('manifest.json', output), `${JSON.stringify({ generatedAt: new Date().toISOString(), baseUrl, quality, state: 'hero', files: report }, null, 2)}\n`)
  for (const item of report) console.log(`${item.file}: ${item.size.join('×')} ${(item.bytes / 1024).toFixed(1)} KB`)
  if (errors.length) {
    console.error('Browser errors:', errors)
    process.exitCode = 1
  }
} finally {
  await browser.close()
}
