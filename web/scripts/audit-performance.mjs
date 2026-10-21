import { chromium } from '@playwright/test'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import { gzipSync, brotliCompressSync } from 'node:zlib'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import assert from 'node:assert/strict'

const stage = process.argv[2] ?? 'after'
if (!['before', 'after'].includes(stage)) throw new Error('Use before or after')
const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:4180'
const output = new URL(`../reports/performance/${stage}/`, import.meta.url)
await mkdir(output, { recursive: true })
const file = (name) => new URL(name, output).pathname
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
const errors = [], downloads = [], rendering = []
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex')
const threeD = /\/Scene-|\/ScrollController-|\/framing-|\.glb/
try {
  for (const scenario of [
    { name: 'desktop-live', options: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 } },
    { name: 'phone-static', options: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true } },
    { name: 'desktop-reduced', options: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' } },
  ]) {
    const context = await browser.newContext(scenario.options)
    const page = await context.newPage()
    page.on('pageerror', (error) => errors.push(`${scenario.name}: ${error.message}`))
    const requests = []
    page.on('request', (request) => requests.push(new URL(request.url()).pathname))
    // Count actual production WebGL calls, including shadow passes, without app debug hooks.
    await page.addInitScript(() => {
      window.__auditGPU = { calls: 0, triangles: 0 }
      for (const [name, countIndex, instancesIndex] of [['drawElements', 1, -1], ['drawArrays', 2, -1], ['drawElementsInstanced', 1, 4], ['drawArraysInstanced', 2, 3]]) {
        const original = WebGL2RenderingContext.prototype[name]
        WebGL2RenderingContext.prototype[name] = function (...args) {
          window.__auditGPU.calls++
          if (args[0] === this.TRIANGLES) window.__auditGPU.triangles += args[countIndex] / 3 * (instancesIndex < 0 ? 1 : args[instancesIndex])
          return original.apply(this, args)
        }
      }
    })
    await page.goto(baseUrl)
    await page.locator('.site[data-state="ready"]').waitFor()
    await page.waitForTimeout(1500)
    const download = await page.evaluate(() => ({
      mode: document.querySelector('.site').dataset.mode,
      resources: performance.getEntriesByType('resource').map((entry) => ({ path: new URL(entry.name).pathname,
        transferBytes: entry.transferSize, encodedBytes: entry.encodedBodySize, decodedBytes: entry.decodedBodySize })),
      navigation: performance.getEntriesByType('navigation').map((entry) => ({ transferBytes: entry.transferSize, encodedBytes: entry.encodedBodySize })),
      image: document.querySelector('.still img')?.currentSrc,
    }))
    download.name = scenario.name
    download.threeDRequests = requests.filter((path) => threeD.test(path))
    download.transferredBytes = download.resources.reduce((sum, item) => sum + item.transferBytes, 0) + download.navigation[0].transferBytes
    if (scenario.name !== 'desktop-live') { assert.equal(download.mode, 'static'); assert.deepEqual(download.threeDRequests, []) }
    downloads.push(download)
    if (scenario.name === 'desktop-live') {
      for (const moving of [false, true]) {
        const metrics = await page.evaluate(async (moving) => {
          const canvas = document.querySelector('canvas'), gl = canvas.getContext('webgl2')
          const extension = gl.getExtension('WEBGL_debug_renderer_info')
          const gpu = extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)
          const frames = await new Promise((resolve) => {
            let start, previous, counts = { ...window.__auditGPU }
            const frames = [], max = document.documentElement.scrollHeight - innerHeight
            function sample(time) {
              start ??= time
              const now = { ...window.__auditGPU }
              if (previous !== undefined) frames.push({ ms: time - previous, calls: now.calls - counts.calls, triangles: now.triangles - counts.triangles })
              previous = time; counts = now
              if (moving) {
                window.scrollTo({ top: max * (0.5 - 0.5 * Math.cos((time - start) / 5000 * Math.PI * 2)), behavior: 'instant' })
                window.dispatchEvent(new PointerEvent('pointermove', { pointerType: 'mouse', clientX: innerWidth * (0.5 + 0.4 * Math.sin(time / 500)), clientY: innerHeight * 0.7 }))
              }
              if (time - start < 5000) requestAnimationFrame(sample)
              else resolve(frames)
            }
            requestAnimationFrame(sample)
          })
          const values = frames.map((frame) => frame.ms).sort((a, b) => a - b)
          const active = frames.filter((frame) => frame.calls > 0)
          const calls = active.map((frame) => frame.calls).sort((a, b) => a - b)
          const triangles = active.map((frame) => frame.triangles).sort((a, b) => a - b)
          return { moving, gpu, css: [canvas.clientWidth, canvas.clientHeight], buffer: [canvas.width, canvas.height], dpr: canvas.width / canvas.clientWidth,
            sampledFrames: frames.length, activeFrames: active.length, averageFps: frames.length * 1000 / frames.reduce((sum, frame) => sum + frame.ms, 0), p95FrameMs: values[Math.floor(values.length * 0.95)],
            calls: { min: calls[0], median: calls[Math.floor(calls.length / 2)], max: calls.at(-1) },
            triangles: { min: triangles[0], median: triangles[Math.floor(triangles.length / 2)], max: triangles.at(-1) } }
        }, moving)
        rendering.push(metrics)
      }
      // Stable hero capture for before/after comparison. No forced-static mode.
      await page.emulateMedia({ reducedMotion: 'reduce' })
      await page.goto(`${baseUrl}/?mode=live`)
      await page.locator('.site[data-state="ready"]').waitFor()
      await page.waitForTimeout(300)
      await page.screenshot({ path: file('desktop-hero.png'), scale: 'css' })
      await page.screenshot({ path: file('desktop-full.png'), fullPage: true, scale: 'css' })
    } else await page.screenshot({ path: file(`${scenario.name}.png`), scale: 'css' })
    await context.close()
  }
  const inventory = []
  for (const name of await readdir(new URL('../dist/assets/', import.meta.url))) {
    const bytes = await readFile(new URL(`../dist/assets/${name}`, import.meta.url))
    inventory.push({ name, bytes: bytes.length, gzipBytes: gzipSync(bytes).length, brotliBytes: brotliCompressSync(bytes).length, sha256: hash(bytes) })
  }
  const bytes = await readFile(new URL('../dist/models/reef.glb', import.meta.url))
  const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8'))
  const triangles = gltf.nodes.filter((node) => node.mesh !== undefined).reduce((total, node) => total + gltf.meshes[node.mesh].primitives.reduce((n, primitive) => n + gltf.accessors[primitive.indices].count / 3, 0), 0)
  const binOffset = 20 + bytes.readUInt32LE(12) + 8
  const textures = gltf.images.map((image) => {
    const view = gltf.bufferViews[image.bufferView], data = bytes.subarray(binOffset + view.byteOffset, binOffset + view.byteOffset + view.byteLength)
    return { mimeType: image.mimeType, embeddedBytes: view.byteLength, width: data.readUInt32BE(16), height: data.readUInt32BE(20) }
  })
  assert.deepEqual(errors, [])
  const report = { stage, measuredAt: new Date().toISOString(), baseUrl, browser: browser.version(), revision: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    method: 'Vite production preview, fresh contexts, unthrottled real GPU; 5-second RAF windows after warmup with actual WebGL draw calls including shadow passes. ResourceTiming includes headers; gzip/Brotli inventory is potential compression, not served compression. Desktop screenshot uses forced live + reduced motion for stable comparisons.',
    downloads, rendering, inventory, glb: { bytes: bytes.length, gzipBytes: gzipSync(bytes).length, sha256: hash(bytes), triangles, materials: gltf.materials.length, textures }, errors }
  await writeFile(file('performance.json'), `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify({ stage, downloads: downloads.map(({ name, transferredBytes, threeDRequests }) => ({ name, transferredBytes, threeDRequests })), rendering, glb: report.glb }, null, 2))
} finally {
  await browser.close()
}
