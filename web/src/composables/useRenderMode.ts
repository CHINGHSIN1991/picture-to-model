// Step 14: live Three.js scene or a still WebP. Decided once at startup from several signals,
// never from the viewport width alone, so a narrow desktop window keeps the live scene.
export type RenderMode = 'live' | 'static'

export interface RenderSignals {
  reducedMotion: boolean
  saveData: boolean
  /** A WebGL 2 or WebGL 1 context could be created. */
  webgl: boolean
  /** gl.MAX_TEXTURE_SIZE, 0 when WebGL is unavailable. */
  maxTextureSize: number
  cores: number
  /** navigator.deviceMemory in GB (Chromium only); 4 when unknown. */
  memory: number
  dpr: number
  width: number
  height: number
  /** (pointer: coarse) — the primary input is touch. */
  coarsePointer: boolean
  /** (any-pointer: fine) — a mouse, trackpad or pen is attached. */
  finePointer: boolean
  touchPoints: number
}

export interface RenderDecision {
  mode: RenderMode
  /** Which rule decided; exposed as `data-mode-reason` for inspection. */
  reason: string
}

export const renderModeConfig = {
  /** Shadow maps are 2048 px (createLighting.ts); smaller GPUs cannot render the scene as authored. */
  minTextureSize: 2048,
  /** Touch devices whose shorter side is below this many CSS px get the still. */
  touchShortSide: 768,
  maxCoresForStatic: 2,
  maxMemoryForStatic: 2,
  /** Many device pixels on a small core count means a weak GPU behind a sharp display. */
  highDprPixels: 3000,
  highDprCores: 4,
}

export function decideRenderMode(signals: RenderSignals, override?: string | null): RenderDecision {
  if (override === 'live' || override === 'static') return { mode: override, reason: 'query' }
  if (signals.reducedMotion) return { mode: 'static', reason: 'reduced-motion' }
  if (signals.saveData) return { mode: 'static', reason: 'save-data' }
  if (!signals.webgl) return { mode: 'static', reason: 'no-webgl' }
  if (signals.maxTextureSize < renderModeConfig.minTextureSize) return { mode: 'static', reason: 'small-texture' }
  // iPads report a desktop UA; the touch point count and the missing fine pointer tell them apart.
  const touch = (signals.coarsePointer && !signals.finePointer) || signals.touchPoints > 1
  if (touch && Math.min(signals.width, signals.height) < renderModeConfig.touchShortSide) return { mode: 'static', reason: 'touch-small-screen' }
  if (signals.cores <= renderModeConfig.maxCoresForStatic || signals.memory <= renderModeConfig.maxMemoryForStatic) return { mode: 'static', reason: 'low-end' }
  if (signals.width * signals.dpr > renderModeConfig.highDprPixels && signals.cores <= renderModeConfig.highDprCores) return { mode: 'static', reason: 'high-dpr-few-cores' }
  return { mode: 'live', reason: 'capable' }
}

interface NavigatorHints extends Navigator {
  deviceMemory?: number
  connection?: { saveData?: boolean }
}

function probeWebgl() {
  const canvas = document.createElement('canvas')
  let gl: WebGLRenderingContext | WebGL2RenderingContext | null = null
  try {
    gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl')
  } catch {
    gl = null
  }
  if (!gl) return { webgl: false, maxTextureSize: 0 }
  const maxTextureSize = Number(gl.getParameter(gl.MAX_TEXTURE_SIZE)) || 0
  gl.getExtension('WEBGL_lose_context')?.loseContext()
  return { webgl: true, maxTextureSize }
}

export function readRenderSignals(): RenderSignals {
  const hints = navigator as NavigatorHints
  return {
    reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    saveData: hints.connection?.saveData === true,
    ...probeWebgl(),
    cores: navigator.hardwareConcurrency || 2,
    memory: hints.deviceMemory ?? 4,
    dpr: window.devicePixelRatio || 1,
    width: window.innerWidth,
    height: window.innerHeight,
    coarsePointer: matchMedia('(pointer: coarse)').matches,
    finePointer: matchMedia('(any-pointer: fine)').matches,
    touchPoints: navigator.maxTouchPoints || 0,
  }
}

/** `?mode=live|static` forces a mode for art direction, asset capture and tests. */
export function useRenderMode(query = new URLSearchParams(window.location.search)): RenderDecision {
  return decideRenderMode(readRenderSignals(), query.get('mode'))
}
