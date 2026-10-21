import { Box3, CatmullRomCurve3, MathUtils, Quaternion, Vector3, type Object3D } from 'three'
import type { Model } from './Model'
import { partAnimations, type PartAnimationConfig } from './config/partAnimations'
import { partGroupNames, type PartGroup } from './config/partGroups'

interface Transform { position: Vector3; quaternion: Quaternion; scale: Vector3 }
type Mode = PartAnimationConfig['mode']
type PreparedMode = (out: Transform, t: number) => void
type ModeFactory<K extends Mode> = (rest: Transform, config: Extract<PartAnimationConfig, { mode: K }>) => PreparedMode

// Prepare curves/vectors once; frame updates allocate no Three.js objects.
const modes: { [K in Mode]: ModeFactory<K> } = {
  stack: (rest, cfg) => (out, t) => { out.position.y = rest.position.y - cfg.dropHeight * t },
  grow: (rest, cfg) => (out, t) => {
    const arrival = 1 - t
    // Back easing overshoots near completion, then returns exactly to authored scale.
    const back = arrival - 1
    const scale = 1 + (cfg.overshoot * 10 + 1) * back ** 3 + cfg.overshoot * 10 * back ** 2
    out.scale.copy(rest.scale).multiplyScalar(Math.max(0, scale))
  },
  path: (rest, cfg) => {
    const curve = new CatmullRomCurve3(cfg.offsets.map((p) => new Vector3(...p)))
    const offset = new Vector3()
    return (out, t) => { out.position.copy(rest.position).add(curve.getPoint(1 - t, offset)) }
  },
  orbit: (rest, cfg) => {
    const center = new Vector3(...cfg.center)
    const axis = new Vector3(...cfg.axis).normalize()
    const rotation = new Quaternion()
    return (out, t) => {
      rotation.setFromAxisAngle(axis, cfg.angle * t)
      out.position.copy(rest.position).sub(center).applyQuaternion(rotation).add(center)
      out.quaternion.copy(rest.quaternion).premultiply(rotation)
    }
  },
  explode: (rest, cfg) => {
    const direction = rest.position.clone().sub(new Vector3(...cfg.center)).normalize()
    return (out, t) => { out.position.addScaledVector(direction, cfg.distance * t) }
  },
}

function seed(name: string) {
  let hash = 2166136261
  for (const char of name) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619)
  return hash >>> 0
}

export class PartAnimator {
  private progress: Partial<Record<PartGroup, number>> = {}
  private entries: {
    group: PartGroup; node: Object3D; rest: Transform; out: Transform; mode: PreparedMode
    cfg: PartAnimationConfig; delay: number; span: number; current: number
  }[] = []

  constructor(private model: Model, configs = partAnimations) {
    for (const group of partGroupNames) {
      const cfg = configs[group]
      if (!cfg) continue
      const nodes = [...model.groups[group]]
      // Rock pivots all sit on the sand; use the top of each piece to order low → high.
      const heights = new Map(nodes.map((node) => [node, new Box3().setFromObject(node).max.y]))
      if ('order' in cfg) nodes.sort((a, b) => cfg.order === 'height'
        ? heights.get(a)! - heights.get(b)! || a.name.localeCompare(b.name)
        : seed(a.name) - seed(b.name))
      // Long groups must retain a nonzero animation interval (35 × .03 exceeds 1).
      const span = 'stagger' in cfg ? Math.min(0.8, Math.max(0, cfg.stagger) * (nodes.length - 1)) : 0
      nodes.forEach((node, index) => {
        const rest = { position: node.position.clone(), quaternion: node.quaternion.clone(), scale: node.scale.clone() }
        const factory = modes[cfg.mode] as (rest: Transform, cfg: PartAnimationConfig) => PreparedMode
        this.entries.push({
          group, node, rest, cfg, mode: factory(rest, cfg), span,
          delay: nodes.length > 1 ? span * index / (nodes.length - 1) : 0,
          current: 0,
          out: { position: rest.position.clone(), quaternion: rest.quaternion.clone(), scale: rest.scale.clone() },
        })
      })
    }
  }

  setProgress(parts: Partial<Record<PartGroup, number>>) { Object.assign(this.progress, parts) }

  /** Snap for initial/deep-link/reduced-motion states; otherwise each node has independent damping. */
  update(dt: number, snap = false) {
    let changed = false
    for (const entry of this.entries) {
      const { node, rest, out, cfg } = entry
      const arrival = 1 - MathUtils.clamp(this.progress[entry.group] ?? 0, 0, 1)
      const target = 1 - MathUtils.clamp((arrival - entry.delay) / (1 - entry.span), 0, 1)
      let current = snap ? target : entry.current + (target - entry.current) * (1 - Math.exp(-cfg.spring * dt))
      if (Math.abs(current - target) < 1e-5) current = target
      if (current === entry.current) continue
      entry.current = current
      out.position.copy(rest.position)
      out.quaternion.copy(rest.quaternion)
      out.scale.copy(rest.scale)
      // Exact t=0 restoration avoids accumulated rotations or floating-point drift.
      if (current !== 0) entry.mode(out, current)
      if (cfg.hideAtDeparture) out.scale.multiplyScalar(MathUtils.clamp((1 - current) / 0.15, 0, 1))
      node.position.copy(out.position)
      node.quaternion.copy(out.quaternion)
      node.scale.copy(out.scale)
      changed = true
    }
    if (changed) this.model.syncInstances()
    return changed
  }
}
