import { DirectionalLight, Fog, HemisphereLight, PMREMGenerator, Scene, WebGLRenderer } from 'three'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { createWaterBackground } from './createWaterBackground'
import { lightingConfig, type LightConfig } from './lightingConfig'

export function createLighting(scene: Scene, renderer: WebGLRenderer) {
  const config = structuredClone(lightingConfig)
  const ambient = new HemisphereLight()
  const key = new DirectionalLight()
  const fill = new DirectionalLight()
  const rim = new DirectionalLight()
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -3.5, right: 3.5, top: 3.5, bottom: -3.5, near: 0.1, far: 20 })
  key.shadow.normalBias = 0.015
  key.shadow.bias = -0.0001
  scene.add(ambient, key, fill, rim)
  // Static model/lights: refresh shadows after loading and GUI changes, not every frame.
  renderer.shadowMap.autoUpdate = false
  renderer.shadowMap.needsUpdate = true
  const room = new RoomEnvironment()
  const pmrem = new PMREMGenerator(renderer)
  const environment = pmrem.fromScene(room, 0.04, 0.1, 100, { size: 128 })
  room.dispose()
  pmrem.dispose()
  scene.environment = environment.texture
  const fog = new Fog(config.fog.color, config.fog.near, config.fog.far)
  scene.fog = fog
  const water = createWaterBackground(config)
  scene.add(water.mesh)
  function setLight(light: DirectionalLight, values: LightConfig) {
    light.color.set(values.color)
    light.intensity = values.intensity
    light.position.fromArray(values.position)
  }
  function apply() {
    renderer.toneMappingExposure = config.exposure
    ambient.color.set(config.ambient.sky)
    ambient.groundColor.set(config.ambient.ground)
    ambient.intensity = config.ambient.intensity
    setLight(key, config.key)
    setLight(fill, config.fill)
    setLight(rim, config.rim)
    key.shadow.radius = config.shadow.radius
    key.shadow.intensity = config.shadow.intensity
    renderer.shadowMap.needsUpdate = true
    scene.environmentIntensity = config.environmentIntensity
    fog.color.set(config.fog.color)
    water.apply()
  }
  apply()
  return {
    config,
    apply,
    update(time: number, cameraDistance: number, aspect: number) {
      // Preserve haze depth when a narrow viewport forces the camera farther away.
      const offset = cameraDistance - config.fog.referenceDistance
      fog.near = config.fog.enabled ? Math.max(0, config.fog.near + offset) : 1e6
      fog.far = config.fog.enabled ? Math.max(fog.near + 0.1, config.fog.far + offset) : 1e6 + 1
      water.update(time, aspect)
    },
    dispose() {
      water.dispose()
      key.shadow.dispose()
      environment.dispose()
      scene.environment = null
      scene.fog = null
      scene.remove(ambient, key, fill, rim)
    },
  }
}
