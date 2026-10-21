import { DynamicDrawUsage, InstancedMesh, Mesh, type Group } from 'three'
import type { Model } from './Model'
import { partGroupNames, partGroups } from './config/partGroups'

/** Keep named nodes as invisible transform proxies; batches share their exact parent space. */
export function buildModelInstances(model: Pick<Model, 'groups' | 'scene'>) {
  const batches: { mesh: InstancedMesh; sources: Mesh[] }[] = []
  let before = 0
  model.scene.traverse((node) => { if (node instanceof Mesh && node.visible) before++ })
  for (const name of partGroupNames) {
    if (!partGroups[name].instancing) continue
    const candidates = new Map<string, Mesh[]>()
    for (const node of model.groups[name]) {
      if (!(node instanceof Mesh) || node.children.length || !node.parent) continue
      const materials = Array.isArray(node.material) ? node.material : [node.material]
      const key = [node.parent.uuid, node.geometry.uuid, ...materials.map((material) => material.uuid)].join('/')
      if (!candidates.has(key)) candidates.set(key, [])
      candidates.get(key)!.push(node)
    }
    for (const sources of candidates.values()) {
      if (sources.length < 4) continue
      const source = sources[0]!
      const mesh = new InstancedMesh(source.geometry, source.material, sources.length)
      mesh.name = `${name}__${source.name}`
      mesh.castShadow = source.castShadow
      mesh.receiveShadow = source.receiveShadow
      mesh.instanceMatrix.setUsage(DynamicDrawUsage)
      ;(source.parent as Group).add(mesh)
      sources.forEach((node) => { node.visible = false })
      batches.push({ mesh, sources })
    }
  }
  function sync() {
    for (const { mesh, sources } of batches) {
      sources.forEach((node, i) => {
        node.updateMatrix()
        mesh.setMatrixAt(i, node.matrix)
      })
      mesh.instanceMatrix.needsUpdate = true
      // Animated instances can leave their original bounds, including when reversing.
      mesh.computeBoundingSphere()
      mesh.computeBoundingBox()
    }
  }
  sync()
  const instancedNodes = batches.reduce((total, batch) => total + batch.sources.length, 0)
  return {
    sync,
    report: { before, after: before - instancedNodes + batches.length, instancedNodes, batches: batches.length },
  }
}
