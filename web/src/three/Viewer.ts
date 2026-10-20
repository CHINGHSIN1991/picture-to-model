import { MathUtils, Mesh, PerspectiveCamera, Sphere, Vector3 } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { createRenderer } from './createRenderer'
import { createScene } from './createScene'
import { disposeModel, loadModel } from './loadModel'
import { createLighting } from './createLighting'
import { createWaterMaterials } from './createWaterMaterials'

export function mountViewer(container: HTMLElement) {
  const renderer = createRenderer()
  const scene = createScene()
  const lighting = createLighting(scene, renderer)
  // Blender hero: 50 mm lens, 36 mm sensor, 4:3 frame.
  const camera = new PerspectiveCamera(MathUtils.radToDeg(2 * Math.atan(27 / 100)), 1, 0.01, 100)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.maxPolarAngle = Math.PI * 0.95
  container.append(renderer.domElement)

  let disposed = false
  let asset: Awaited<ReturnType<typeof loadModel>> | undefined
  let lastFitDistance = 0
  let debug: { update(): void; dispose(): void } | undefined
  const framingPoints: Vector3[] = []
  const azimuth = MathUtils.degToRad(-12)
  const elevation = MathUtils.degToRad(17)
  const heroDirection = new Vector3(Math.cos(elevation) * Math.sin(azimuth), Math.sin(elevation), Math.cos(elevation) * Math.cos(azimuth))

  function fitDistance() {
    if (!asset) return 6.8
    // Fit geometry in camera space, including depth. Empty bounding-box corners
    // overestimate a cone-shaped reef and make the subject unnecessarily small.
    // Keep the Blender camera distance when the viewport has sufficient room.
    const tanV = Math.tan(MathUtils.degToRad(camera.fov / 2))
    const tanH = tanV * camera.aspect
    let distance = 6.8
    for (const point of framingPoints) {
      distance = Math.max(distance, point.z + 1.08 * Math.max(Math.abs(point.x) / tanH, Math.abs(point.y) / tanV))
    }
    return distance
  }

  function resize() {
    if (disposed) return
    const width = Math.max(container.clientWidth, 1)
    const height = Math.max(container.clientHeight, 1)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
    renderer.setSize(width, height, false)
    if (asset) {
      const distance = fitDistance()
      // Preserve the user's orbit, pan and relative zoom when resizing.
      if (lastFitDistance) camera.position.sub(controls.target).multiplyScalar(distance / lastFitDistance).add(controls.target)
      else camera.position.copy(heroDirection).multiplyScalar(distance).add(controls.target)
      lastFitDistance = distance
      controls.maxDistance = Math.max(30, distance * 3)
      camera.far = Math.max(100, controls.maxDistance * 2)
      camera.updateProjectionMatrix()
      controls.update()
    }
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  window.addEventListener('resize', resize)
  resize()

  const ready = loadModel().then(async (loaded) => {
    if (disposed) {
      disposeModel(loaded.model)
      return
    }
    asset = loaded
    scene.add(loaded.model)
    const waterMaterials = createWaterMaterials(loaded.model, lighting.config)
    waterMaterials.apply()
    controls.target.copy(new Vector3(0, 0.8, 0).sub(loaded.center))
    const right = new Vector3().crossVectors(camera.up, heroDirection).normalize()
    const up = new Vector3().crossVectors(heroDirection, right).normalize()
    const vertex = new Vector3()
    loaded.model.traverse((object) => {
      const mesh = object as Mesh
      if (!mesh.isMesh) return
      const positions = mesh.geometry.attributes.position!
      for (let i = 0; i < positions.count; i++) {
        vertex.fromBufferAttribute(positions, i).applyMatrix4(mesh.matrixWorld).sub(controls.target)
        framingPoints.push(new Vector3(vertex.dot(right), vertex.dot(up), vertex.dot(heroDirection)))
      }
    })
    controls.minDistance = loaded.bounds.getBoundingSphere(new Sphere()).radius * 0.45
    resize()
    if (new URLSearchParams(window.location.search).has('debug')) {
      const { createLightingDebug } = await import('./createLightingDebug')
      if (disposed) return
      debug = createLightingDebug(lighting.config, () => {
        lighting.apply()
        waterMaterials.apply()
      })
    }
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let lastTime: number | undefined
    let waterTime = 0
    renderer.setAnimationLoop((time) => {
      const delta = lastTime === undefined ? 0 : Math.min((time - lastTime) / 1000, 0.1)
      lastTime = time
      if (lighting.config.caustics.animated && !reducedMotion.matches) waterTime += delta * lighting.config.caustics.speed
      controls.update()
      lighting.update(waterTime, controls.getDistance(), camera.aspect)
      waterMaterials.update(waterTime)
      renderer.render(scene, camera)
      debug?.update()
    })
  }).catch((error: unknown) => {
    dispose()
    throw error
  })

  function dispose() {
    if (disposed) return
    disposed = true
    observer.disconnect()
    window.removeEventListener('resize', resize)
    renderer.setAnimationLoop(null)
    controls.dispose()
    debug?.dispose()
    if (asset) disposeModel(asset.model)
    lighting.dispose()
    scene.clear()
    renderer.dispose()
    renderer.domElement.remove()
  }

  return { ready, dispose }
}
