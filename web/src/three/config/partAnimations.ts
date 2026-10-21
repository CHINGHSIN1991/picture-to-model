// PROJECT_SPEC.md「逐件動畫」. Consumed by Step 13's PartAnimator; nothing here is executed yet.
// `t` is departure: 0 = rest, 1 = the group's departed state under its mode.
import type { PartGroup } from './partGroups'

export type PartAnimationConfig =
  | { mode: 'stack'; dropHeight: number; order: 'height' | 'random'; stagger: number }
  | { mode: 'grow'; order: 'height' | 'random'; stagger: number; overshoot: number }
  | { mode: 'path'; offsets: [number, number, number][] }
  | { mode: 'orbit'; center: [number, number, number]; axis: [number, number, number]; angle: number }

// `boulders` has no mode: it stays at rest with the sand as the anchor (Step 09 decision).
export const partAnimations: Partial<Record<PartGroup, PartAnimationConfig>> = {
  rocks: { mode: 'stack', dropHeight: 1.5, order: 'height', stagger: 0.1 },
  corals: { mode: 'grow', order: 'random', stagger: 0.03, overshoot: 0.15 },
  kelp: { mode: 'grow', order: 'random', stagger: 0.03, overshoot: 0.15 },
  diver: { mode: 'path', offsets: [[-1.0, 3.0, 0.5], [-0.5, 1.2, 0.3], [0, 0, 0]] },
  fish: { mode: 'orbit', center: [0, 0.8, 0], axis: [0, 1, 0], angle: Math.PI * 2 },
}
