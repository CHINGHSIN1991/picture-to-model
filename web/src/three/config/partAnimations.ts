// PROJECT_SPEC.md「逐件動畫」. Consumed by PartAnimator.
// `t` is departure: 0 = rest, 1 = the group's departed state under its mode.
import type { PartGroup } from './partGroups'

export type PartAnimationConfig = { spring: number; hideAtDeparture?: boolean } & (
  | { mode: 'stack'; dropHeight: number; order: 'height' | 'random'; stagger: number }
  | { mode: 'grow'; order: 'height' | 'random'; stagger: number; overshoot: number }
  | { mode: 'path'; offsets: [number, number, number][] }
  | { mode: 'orbit'; center: [number, number, number]; axis: [number, number, number]; angle: number }
  | { mode: 'explode'; center: [number, number, number]; distance: number }
)

// `boulders` has no mode: it stays at rest with the sand as the anchor (Step 09 decision).
export const partAnimations: Partial<Record<PartGroup, PartAnimationConfig>> = {
  rocks: { mode: 'stack', dropHeight: 1.5, order: 'height', stagger: 0.1, spring: 5, hideAtDeparture: true },
  corals: { mode: 'grow', order: 'random', stagger: 0.03, overshoot: 0.15, spring: 6 },
  kelp: { mode: 'grow', order: 'random', stagger: 0.03, overshoot: 0.15, spring: 6 },
  diver: { mode: 'path', offsets: [[-1.0, 3.0, 0.5], [-0.5, 1.2, 0.3], [0, 0, 0]], spring: 4, hideAtDeparture: true },
  fish: { mode: 'orbit', center: [0, 0.8, 0], axis: [0, 1, 0], angle: Math.PI * 2, spring: 6, hideAtDeparture: true },
}
