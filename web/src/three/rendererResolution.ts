import { rendererConfig } from './config/renderer'

export function getRendererPixelRatio() {
  return Math.min(window.devicePixelRatio, rendererConfig.maxPixelRatio)
}

/** A display/zoom change can change DPR without changing the CSS viewport size. */
export function observePixelRatio(onChange: () => void) {
  let query: MediaQueryList
  let disposed = false
  function watch() {
    query = window.matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`)
    query.addEventListener('change', changed)
  }
  function changed() {
    if (disposed) return
    query.removeEventListener('change', changed)
    // Re-arm at the new DPR so subsequent display changes are also observed.
    watch()
    onChange()
  }
  watch()
  return () => {
    disposed = true
    query.removeEventListener('change', changed)
  }
}
