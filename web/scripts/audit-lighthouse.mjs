import { spawn } from 'node:child_process'
import { mkdir, readFile, writeFile, unlink } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'

const stage = process.argv[2] ?? 'after'
if (!['before', 'after'].includes(stage)) throw new Error('Use before or after')
const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:4180'
const output = new URL(`../reports/performance/${stage}/`, import.meta.url)
await mkdir(output, { recursive: true })
const runs = []
for (let i = 1; i <= Number(process.env.LH_RUNS ?? 3); i++) {
  const path = new URL(`lighthouse-${i}`, output).pathname
  const args = [new URL('../node_modules/lighthouse/cli/index.js', import.meta.url).pathname, baseUrl,
    '--only-categories=performance', '--output=json', '--output=html', `--output-path=${path}`, '--chrome-flags=--headless', '--quiet']
  await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, { stdio: 'inherit', env: { ...process.env,
      CHROME_PATH: process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' } })
    child.once('error', reject)
    child.once('exit', (code) => code === 0 ? resolve() : reject(new Error(`Lighthouse exited ${code}`)))
  })
  const report = JSON.parse(await readFile(`${path}.report.json`, 'utf8'))
  if (report.runtimeError) throw new Error(JSON.stringify(report.runtimeError))
  const metric = (id) => report.audits[id].numericValue
  runs.push({ run: i, version: report.lighthouseVersion, score: report.categories.performance.score * 100,
    fcpMs: metric('first-contentful-paint'), lcpMs: metric('largest-contentful-paint'), cls: metric('cumulative-layout-shift'),
    tbtMs: metric('total-blocking-time'), speedIndexMs: metric('speed-index'), settings: report.configSettings,
    environment: report.environment, warnings: report.runWarnings })
  await writeFile(`${path}.report.html.gz`, gzipSync(await readFile(`${path}.report.html`)))
  await unlink(`${path}.report.html`)
  console.log(stage, 'run', i, JSON.stringify({ score: runs.at(-1).score, lcpMs: runs.at(-1).lcpMs, cls: runs.at(-1).cls, tbtMs: runs.at(-1).tbtMs }))
}
const median = (key) => [...runs].sort((a, b) => a[key] - b[key])[Math.floor(runs.length / 2)][key]
const summary = { stage, baseUrl, measuredAt: new Date().toISOString(), runs,
  median: Object.fromEntries(['score', 'fcpMs', 'lcpMs', 'cls', 'tbtMs', 'speedIndexMs'].map((key) => [key, median(key)])) }
await writeFile(new URL('lighthouse-summary.json', output), `${JSON.stringify(summary, null, 2)}\n`)
