import { MathUtils, PerspectiveCamera } from 'three'
import { createRenderer } from './createRenderer'
import { createScene } from './createScene'
import { createLighting } from './createLighting'
import { createWaterMaterials } from './createWaterMaterials'
import { createCameraController } from './CameraController'
import { collectFramingPoints } from './framing'
import { loadModel, type Model } from './Model'
import { heroState, type SectionState } from './config/sections'

export interface SceneOptions {
  modelUrl?: string
  /** Load the lil-gui lighting panel (same tool as the Step 08 viewer). */
  debug?: boolean
  /** Initial section state; defaults to the hero. */
  state?: SectionState
}

/** The only object Vue talks to. It takes a container element and numbers; it never reads the DOM beyond sizing. */
export interface SceneHandle {
  ready: Promise<void>
  setSectionState(state: SectionState): void
  /** Normalised pointer (−1…1). Stored for Step 11; unused until then. */
  setPointer(x: number, y: number): void
  pause(): void
  resume(): void
  dispose(): void
}

export function mountScene(container: HTMLElement, options: SceneOptions = {}): SceneHandle {
  const renderer = createRenderer()
  renderer.domElement.setAttribute('aria-hidden', 'true')
  renderer.domElement.removeAttribute('role')
  renderer.domElement.removeAttribute('aria-label')
  const scene = createScene()
  const lighting = createLighting(scene, renderer)
  // Blender hero: 50 mm lens, 36 mm sensor, 4:3 frame.
  const camera = new PerspectiveCamera(MathUtils.radToDeg(2 * Math.atan(27 / 100)), 1, 0.01, 100)
  const cameraController = createCameraController(camera)
  container.append(renderer.domElement)

  let disposed = false
  let paused = false
  let model: Model | undefined
  let waterMaterials: ReturnType<typeof createWaterMaterials> | undefined
  let debug: { update(): void; dispose(): void } | undefined
  let state: SectionState = structuredClone(options.state ?? heroState)
  const pointer = { x: 0, y: 0 }

  function applyState() {
    if (!model) return
    model.root.position.fromArray(state.position)
    model.root.rotation.set(
      MathUtils.degToRad(state.rotation[0]), MathUtils.degToRad(state.rotation[1]), MathUtils.degToRad(state.rotation[2]))
    model.root.scale.setScalar(state.scale)
    model.root.updateMatrixWorld(true)
    cameraController.applyState(state)
    // Lights are static, so shadows only need refreshing when the model moves.
    renderer.shadowMap.needsUpdate = true
  }

  function resize() {
    if (disposed) return
    const width = Math.max(container.clientWidth, 1)
    const height = Math.max(container.clientHeight, 1)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
    renderer.setSize(width, height, false)
    cameraController.setViewport(width / height)
    renderer.shadowMap.needsUpdate = true
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  window.addEventListener('resize', resize)
  resize()

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
  let lastTime: number | undefined
  let waterTime = 0
  function frame(time: number) {
    const delta = lastTime === undefined ? 0 : Math.min((time - lastTime) / 1000, 0.1)
    lastTime = time
    if (lighting.config.caustics.animated && !reducedMotion.matches) waterTime += delta * lighting.config.caustics.speed
    lighting.update(waterTime, cameraController.distance, camera.aspect)
    waterMaterials?.update(waterTime)
    renderer.render(scene, camera)
    debug?.update()
  }

  const ready = loadModel(options.modelUrl ?? `${import.meta.env.BASE_URL}models/reef.glb`).then(async (loaded) => {
    if (disposed) {
      loaded.dispose()
      return
    }
    model = loaded
    scene.add(model.root)
    waterMaterials = createWaterMaterials(model.scene, lighting.config)
    waterMaterials.apply()
    // Fit the authored hero view once; section states orbit and offset from there.
    cameraController.setFramingPoints(collectFramingPoints(model.scene, cameraController.target, cameraController.heroDirection))
    applyState()
    if (options.debug) {
      const { createLightingDebug } = await import('./createLightingDebug')
      if (disposed) return
      debug = createLightingDebug(lighting.config, () => {
        lighting.apply()
        waterMaterials?.apply()
      })
    }
    if (!paused) renderer.setAnimationLoop(frame)
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
    debug?.dispose()
    model?.dispose()
    lighting.dispose()
    scene.clear()
    renderer.dispose()
    renderer.domElement.remove()
  }

  return {
    ready,
    setSectionState(next) {
      state = structuredClone(next)
      applyState()
    },
    setPointer(x, y) {
      pointer.x = x
      pointer.y = y
    },
    pause() {
      paused = true
      renderer.setAnimationLoop(null)
      lastTime = undefined
    },
    resume() {
      if (!paused || disposed) return
      paused = false
      if (model) renderer.setAnimationLoop(frame)
    },
    dispose,
  }
}

