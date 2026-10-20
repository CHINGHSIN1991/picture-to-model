import { Color, DirectionalLight, HemisphereLight, Scene } from 'three'

export function createScene() {
  const scene = new Scene()
  scene.background = new Color('#0c2d3c')
  scene.add(new HemisphereLight('#c4e3ff', '#69766e', 1.2))

  // Blender Z-up → glTF Y-up: (x, y, z) → (x, z, -y).
  const key = new DirectionalLight('#fff0dc', 3.5)
  key.position.set(-3, 5, 4)
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -3.5, right: 3.5, top: 3.5, bottom: -3.5, near: 0.1, far: 20 })
  key.shadow.normalBias = 0.015
  key.shadow.bias = -0.0001

  const fill = new DirectionalLight('#b3d6ff', 1.8)
  fill.position.set(4, 3, 1.5)
  const rim = new DirectionalLight('#99d9ff', 1.8)
  rim.position.set(0, 4.5, -3.5)
  scene.add(key, fill, rim)
  return scene
}
