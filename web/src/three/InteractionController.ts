import { pointerConfig, type PointerConfig } from './config/pointer'

/** Window input → damped offsets. No model, camera, or section state ownership. */
export class InteractionController {
  private target = { x: 0, y: 0 }
  private current = { x: 0, y: 0 }
  private reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
  private finePointer = window.matchMedia('(any-pointer: fine)')
  private disposed = false

  constructor(private cfg: PointerConfig = pointerConfig) {
    window.addEventListener('pointermove', this.onMove, { passive: true })
    window.addEventListener('pointerleave', this.onLeave)
    window.addEventListener('pointerout', this.onOut)
    window.addEventListener('pointercancel', this.onLeave)
    window.addEventListener('blur', this.onLeave)
    document.addEventListener('visibilitychange', this.onVisibility)
    this.reducedMotion.addEventListener('change', this.onPreference)
    this.finePointer.addEventListener('change', this.onPreference)
  }

  private get enabled() {
    return !this.disposed && this.cfg.mode === 'tilt' && !this.reducedMotion.matches && this.finePointer.matches
  }

  /** Same normalised input path for DOM events and SceneHandle.setPointer(). */
  setPointer(x: number, y: number) {
    if (!this.enabled) return
    const clamp = (value: number) => Number.isFinite(value) ? Math.max(-1, Math.min(1, value)) : 0
    this.target.x = clamp(y) * this.cfg.maxRotationX
    this.target.y = clamp(x) * this.cfg.maxRotationY
  }

  private onMove = (event: PointerEvent) => {
    if (event.pointerType !== 'mouse' && event.pointerType !== 'pen') return
    this.setPointer(event.clientX / Math.max(window.innerWidth, 1) * 2 - 1,
      event.clientY / Math.max(window.innerHeight, 1) * 2 - 1)
  }

  private onLeave = () => { this.target.x = 0; this.target.y = 0 }
  // pointerout bubbles from DOM children; only a null destination means window exit.
  private onOut = (event: PointerEvent) => { if (!event.relatedTarget) this.onLeave() }
  private onVisibility = () => { if (document.hidden) this.onLeave() }
  private onPreference = () => {
    this.onLeave()
    this.current.x = 0
    this.current.y = 0
  }

  /** Frame-rate independent exponential damping; no overshoot beyond the configured bounds. */
  update(deltaSeconds: number): Readonly<{ x: number; y: number }> {
    if (!this.enabled) this.onPreference()
    const alpha = 1 - Math.pow(1 - Math.max(0, Math.min(1, this.cfg.damping)),
      Math.max(0, deltaSeconds) * 60 * Math.max(0, this.cfg.stiffness))
    for (const axis of ['x', 'y'] as const) {
      this.current[axis] += (this.target[axis] - this.current[axis]) * alpha
      if (Math.abs(this.target[axis] - this.current[axis]) < 1e-6) this.current[axis] = this.target[axis]
    }
    return this.current
  }

  dispose() {
    if (this.disposed) return
    this.disposed = true
    window.removeEventListener('pointermove', this.onMove)
    window.removeEventListener('pointerleave', this.onLeave)
    window.removeEventListener('pointerout', this.onOut)
    window.removeEventListener('pointercancel', this.onLeave)
    window.removeEventListener('blur', this.onLeave)
    document.removeEventListener('visibilitychange', this.onVisibility)
    this.reducedMotion.removeEventListener('change', this.onPreference)
    this.finePointer.removeEventListener('change', this.onPreference)
    this.onPreference()
  }
}
