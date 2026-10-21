import { MathUtils, PerspectiveCamera } from 'three'
import { createRenderer } from './createRenderer'
import { createScene } from './createScene'
import { createLighting } from './createLighting'
import { createWaterMaterials } from './createWaterMaterials'
import { createCameraController } from './CameraController'
import { collectFramingPoints } from './framing'
import { loadModel, type Model } from './Model'
import { heroState, type SectionState } from './config/sections'
import { InteractionController } from './InteractionController'
import { PartAnimator } from './PartAnimator'

export interface SceneOptions {
  modelUrl?: string
  /** Load the lil-gui lighting panel (same tool as the Step 08 viewer). */
  debug?: boolean
  /** Initial section state; defaults to the hero. */
  state?: SectionState
  /** A plain-data source sampled by the render loop (e.g. ScrollController). */
  stateSource?: () => SectionState
}

/** The only object Vue talks to. Takes a container and numbers; input listeners live in the controller. */
export interface SceneHandle {
  ready: Promise<void>
  setSectionState(state: SectionState): void
  /** Normalised pointer (−1…1); follows the same damping and motion preferences as window input. */
  setPointer(x: number, y: number): void
  pause(): void
  resume(): void
  inspect(): SceneSnapshot
  dispose(): void
}

export interface SceneSnapshot {
  state: SectionState
  rotation: number[]
  calls: number
  triangles: number
  instances?: ReturnType<Model['buildInstances']>
  parts: Record<string, { position: number[]; scale: number[] }>
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
  let partAnimator: PartAnimator | undefined
  let instanceReport: ReturnType<Model['buildInstances']> | undefined
  let waterMaterials: ReturnType<typeof createWaterMaterials> | undefined
  let debug: { update(): void; dispose(): void } | undefined
  let state: SectionState = structuredClone(options.state ?? heroState)
  const interaction = new InteractionController()
  let appliedState = ''

  function applyRotation(delta: number) {
    if (!model) return
    const pointer = interaction.update(delta)
    const x = MathUtils.degToRad(state.rotation[0]) + pointer.x
    const y = MathUtils.degToRad(state.rotation[1]) + pointer.y
    const z = MathUtils.degToRad(state.rotation[2])
    if (model.root.rotation.x === x && model.root.rotation.y === y && model.root.rotation.z === z) return
    model.root.rotation.set(x, y, z)
    renderer.shadowMap.needsUpdate = true
  }

  function applyState() {
    if (!model) return
    model.root.position.fromArray(state.position)
    applyRotation(0)
    model.root.scale.setScalar(state.scale)
    model.root.updateMatrixWorld(true)
    cameraController.applyState(state)
    waterMaterials?.setEmissiveMultiplier(state.emissive)
    partAnimator?.setProgress(state.parts)
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
    const next = options.stateSource?.() ?? state
    const key = JSON.stringify(next)
    if (key !== appliedState) {
      state = next
      applyState()
      appliedState = key
    }
    applyRotation(delta)
    if (partAnimator?.update(delta, reducedMotion.matches)) renderer.shadowMap.needsUpdate = true
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
    instanceReport = model.buildInstances()
    console.info('[reef-landing] instances', JSON.stringify(instanceReport))
    partAnimator = new PartAnimator(model)
    state = options.stateSource?.() ?? state
    applyState()
    partAnimator.update(0, true)
    appliedState = JSON.stringify(state)
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
    interaction.dispose()
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
      interaction.setPointer(x, y)
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
    inspect() {
      return {
        state: structuredClone(state), rotation: model ? model.root.rotation.toArray().slice(0, 3) as number[] : [],
        calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, instances: instanceReport,
        parts: Object.fromEntries(Object.values(model?.groups ?? {}).flat().map((node) => [node.name, {
          position: node.position.toArray(), scale: node.scale.toArray(),
        }])),
      }
    },
    dispose,
  }
}

