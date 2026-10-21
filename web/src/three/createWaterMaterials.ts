import { Mesh, MeshStandardMaterial, Object3D } from 'three'
import type { LightingConfig } from './lightingConfig'

export function createWaterMaterials(model: Object3D, config: LightingConfig) {
  const materials = new Set<MeshStandardMaterial>()
  const coralVariants = new Map<MeshStandardMaterial, MeshStandardMaterial>()
  let emissiveMultiplier = 1
  const uniforms = {
    waterTime: { value: 0 },
    causticStrength: { value: config.caustics.strength },
    causticScale: { value: config.caustics.scale },
  }
  model.traverse((object) => {
    if (!(object instanceof Mesh)) return
    const selectedCoral = /^Coral_(Branch|Brain|Tube)/.test(object.name)
    const prepare = (source: MeshStandardMaterial) => {
      if (!source.isMeshStandardMaterial) return source
      let material = source
      if (selectedCoral) {
        if (!coralVariants.has(source)) coralVariants.set(source, source.clone())
        material = coralVariants.get(source)!
        material.emissiveMap = material.map
      }
      materials.add(material)
      return material
    }
    object.material = Array.isArray(object.material)
      ? object.material.map(prepare)
      : prepare(object.material)
  })
  for (const material of materials) {
    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, uniforms)
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', `#include <common>
          varying vec3 vWaterPosition;`)
        .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
          vWaterPosition = worldPosition.xyz;`)
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>
          varying vec3 vWaterPosition;
          uniform float waterTime, causticStrength, causticScale;`)
        .replace('#include <opaque_fragment>', `
          vec2 waterUv = vWaterPosition.xz * causticScale;
          float wave = sin(waterUv.x + sin(waterUv.y * 1.2 + waterTime))
                     * sin(waterUv.y - waterTime * 0.7 + sin(waterUv.x * 0.8));
          float caustic = pow(1.0 - abs(wave), 12.0);
          float facingUp = smoothstep(0.05, 0.85, inverseTransformDirection(normal, viewMatrix).y);
          outgoingLight *= 1.0 + caustic * facingUp * causticStrength;
          #include <opaque_fragment>
        `)
    }
    material.customProgramCacheKey = () => 'reef-water-v1'
    material.needsUpdate = true
  }
  return {
    apply() {
      uniforms.causticStrength.value = config.caustics.strength
      uniforms.causticScale.value = config.caustics.scale
      for (const material of materials) {
        material.roughness = config.material.roughness
        material.metalness = config.material.metalness
      }
      for (const material of coralVariants.values()) {
        material.emissive.set(config.material.coralEmissive)
        material.emissiveIntensity = config.material.coralIntensity * emissiveMultiplier
      }
    },
    update(time: number) {
      uniforms.waterTime.value = time
    },
    setEmissiveMultiplier(value: number) {
      emissiveMultiplier = value
      for (const material of coralVariants.values()) material.emissiveIntensity = config.material.coralIntensity * value
    },
    // Materials and the shared palette are owned/disposed by the loaded model.
  }
}
