// mockups/SECTIONS.md, one state per section. Plain data so Step 12 can tween it.
import type { PartGroup } from './partGroups'

export interface SectionState {
  id: string
  /** Model offset in scene units (metres); the hero framing is the origin. */
  position: [number, number, number]
  /** Model rotation in degrees. Y is cumulative (0 → −360) so tweens never take the long way round. */
  rotation: [number, number, number]
  scale: number
  camera: {
    /** Camera elevation above the reef in degrees (azimuth stays at the hero's −12°). */
    elevation: number
    /** Multiplier of the hero fit distance. */
    distance: number
  }
  /** Departure per part group at the end of the section: 0 = rest, 1 = departed (modes in partAnimations.ts). */
  parts: Record<PartGroup, number>
  /** Departure when the section is reached; groups listed here animate to `parts` while the section is pinned (Step 12/13). */
  partsOnEnter?: Partial<Record<PartGroup, number>>
  /** Coral emissive multiplier relative to lightingConfig.material.coralIntensity. */
  emissive: number
}

const rest = { rocks: 0, boulders: 0, corals: 0, kelp: 0, fish: 0, diver: 0 }

export const sections: SectionState[] = [
  {
    id: 'hero', position: [1.2, 0, 0], rotation: [0, 0, 0], scale: 0.92,
    camera: { elevation: 17, distance: 1 }, parts: { ...rest }, emissive: 1,
  },
  {
    id: 'upload', position: [-1.1, -0.2, 0], rotation: [0, -35, 0], scale: 0.9,
    camera: { elevation: 21, distance: 1 },
    parts: { ...rest, corals: 1, kelp: 1, fish: 1, diver: 1 }, partsOnEnter: { rocks: 1 }, emissive: 1,
  },
  {
    id: 'model', position: [1.0, -0.1, 0], rotation: [0, -100, 0], scale: 1.2,
    camera: { elevation: 13, distance: 1 },
    parts: { ...rest, fish: 1, diver: 1 }, partsOnEnter: { corals: 1, kelp: 1 }, emissive: 1.4,
  },
  {
    id: 'controls', position: [-1.5, 0.1, 0], rotation: [0, -160, 0], scale: 1.0,
    camera: { elevation: 9, distance: 1 },
    parts: { ...rest, fish: 1 }, partsOnEnter: { diver: 1 }, emissive: 1,
  },
  {
    id: 'interaction', position: [0.9, 0, 0], rotation: [0, -230, 0], scale: 0.9,
    camera: { elevation: 26, distance: 1 },
    parts: { ...rest }, partsOnEnter: { fish: 1 }, emissive: 1,
  },
  {
    id: 'cta', position: [0, -0.7, 0], rotation: [0, -360, 0], scale: 0.85,
    camera: { elevation: 30, distance: 1 }, parts: { ...rest }, emissive: 1,
  },
]

export const heroState = sections[0]!
