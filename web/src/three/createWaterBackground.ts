import { Color, Mesh, PlaneGeometry, ShaderMaterial } from 'three'
import type { LightingConfig } from './lightingConfig'

export function createWaterBackground(config: LightingConfig) {
  const uniforms = {
    topColor: { value: new Color(config.water.top) },
    bottomColor: { value: new Color(config.water.bottom) },
    rayColor: { value: new Color(config.water.rayColor) },
    rayStrength: { value: config.water.rayStrength },
    time: { value: 0 },
    aspect: { value: 1 },
  }
  const material = new ShaderMaterial({
    uniforms,
    depthTest: false,
    depthWrite: false,
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position.xy, 1.0, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 topColor, bottomColor, rayColor;
      uniform float rayStrength, time, aspect;
      varying vec2 vUv;
      void main() {
        vec3 water = mix(bottomColor, topColor, smoothstep(0.0, 1.0, vUv.y));
        // Screen-space light shafts: a depth cue, not a volume simulation.
        float spread = (vUv.x - 0.7) * min(aspect, 2.0) / (1.35 - vUv.y);
        float rays = pow(max(0.0, sin(spread * 18.0 + sin(time * 0.17) * 0.25)), 4.0);
        rays *= 0.65 + 0.35 * sin(spread * 29.0 + 1.4);
        water += rayColor * rays * rayStrength * smoothstep(0.25, 1.0, vUv.y);
        gl_FragColor = vec4(water, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  })
  const mesh = new Mesh(new PlaneGeometry(2, 2), material)
  mesh.name = 'Water_Background'
  mesh.frustumCulled = false
  mesh.renderOrder = -1
  return {
    mesh,
    apply() {
      uniforms.topColor.value.set(config.water.top)
      uniforms.bottomColor.value.set(config.water.bottom)
      uniforms.rayColor.value.set(config.water.rayColor)
      uniforms.rayStrength.value = config.water.rayStrength
    },
    update(time: number, aspect: number) {
      uniforms.time.value = time
      uniforms.aspect.value = aspect
    },
    dispose() {
      mesh.removeFromParent()
      mesh.geometry.dispose()
      material.dispose()
    },
  }
}
