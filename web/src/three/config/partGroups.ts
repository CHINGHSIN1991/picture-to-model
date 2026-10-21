// PROJECT_SPEC.md「零件群組」. Plain data: patterns are strings, compiled by Model.ts.
export interface PartGroupConfig {
  /** RegExp source matched against GLB node names. */
  match: string
  /** Whether Step 13 may merge this group into an InstancedMesh. */
  instancing: boolean
  /** Authored pivot, documented for the animation modes that depend on it. */
  origin: string
}

export const partGroups = {
  rocks: { match: '^Rock_(Peak|Tier)_', instancing: false, origin: '底面中心' },
  boulders: { match: '^Rock_Boulder_', instancing: true, origin: '底面中心' },
  corals: { match: '^Coral_', instancing: true, origin: '與岩塊的接觸點' },
  kelp: { match: '^Kelp_', instancing: true, origin: '根部' },
  fish: { match: '^Fish_[A-C]_', instancing: true, origin: '身體中心' }, // not the Fish_Root container
  diver: { match: '^Diver$', instancing: false, origin: '胸口' },
} satisfies Record<string, PartGroupConfig>

export type PartGroup = keyof typeof partGroups
export const partGroupNames = Object.keys(partGroups) as PartGroup[]
