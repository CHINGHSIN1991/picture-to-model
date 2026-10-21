/** Combines independent visibility gates without owning a render loop. */
export class VisibilityController {
  private readonly visible = new Set<Element>()
  private readonly observer: IntersectionObserver
  private manualPaused = false
  private disposed = false
  private active: boolean | undefined

  constructor(regions: Element[], private readonly scene: { pause(): void; resume(): void }) {
    // Resolve the initial state before an asynchronous model load can start rendering.
    for (const region of regions) {
      const rect = region.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.right > 0
        && rect.top < innerHeight && rect.left < innerWidth) this.visible.add(region)
    }
    this.observer = new IntersectionObserver((entries) => {
      if (this.disposed) return
      for (const entry of entries) {
        if (entry.isIntersecting && entry.intersectionRect.width > 0 && entry.intersectionRect.height > 0) {
          this.visible.add(entry.target)
        } else this.visible.delete(entry.target)
      }
      this.sync()
    }, { threshold: [0, 0.001] })
    for (const region of regions) this.observer.observe(region)
    document.addEventListener('visibilitychange', this.sync)
    this.sync()
  }

  private sync = () => {
    if (this.disposed) return
    const active = !this.manualPaused && document.visibilityState === 'visible' && this.visible.size > 0
    if (active === this.active) return
    this.active = active
    if (active) this.scene.resume()
    else this.scene.pause()
  }

  pause() {
    this.manualPaused = true
    this.sync()
  }

  resume() {
    this.manualPaused = false
    this.sync()
  }

  dispose() {
    if (this.disposed) return
    this.disposed = true
    this.observer.disconnect()
    document.removeEventListener('visibilitychange', this.sync)
    this.visible.clear()
  }
}
