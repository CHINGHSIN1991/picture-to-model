// PROJECT_SPEC.md → Pointer. Optional fish repel is deferred until part animation.
export interface PointerConfig {
  mode: 'tilt' | 'none'
  /** Maximum additive rotation in radians. */
  maxRotationX: number
  maxRotationY: number
  /** Fraction of remaining distance covered per 60 Hz frame (0…1). */
  damping: number
  /** Response speed multiplier; 1 preserves the authored damping. */
  stiffness: number
}

export const pointerConfig: PointerConfig = {
  mode: 'tilt',
  maxRotationX: 0.08,
  maxRotationY: 0.15,
  damping: 0.08,
  stiffness: 1,
}
