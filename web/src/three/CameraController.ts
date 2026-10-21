import { PerspectiveCamera, Vector3 } from 'three'
import { fitDistance, viewDirection } from './framing'
import type { SectionState } from './config/sections'

export interface CameraOptions {
  /** Blender hero camera: azimuth −12°, 50 mm lens on a 36 mm sensor, target (0, 0.8, 0). */
  azimuth: number
  target: [number, number, number]
  /** Authored hero distance; narrow viewports move further back to keep the asset in frame. */
  minimumDistance: number
  /** Below this aspect the look target rises so the model composes in the lower half under the copy. */
  narrowAspect: number
  narrowTargetLift: number
}

export const cameraOptions: CameraOptions = {
  azimuth: -12, target: [0, 0.8, 0], minimumDistance: 6.8, narrowAspect: 0.8, narrowTargetLift: 2.4,
}

/** Owns the camera. It only receives numbers: a section state, framing points and the viewport aspect. */
export function createCameraController(camera: PerspectiveCamera, options: CameraOptions = cameraOptions) {
  const target = new Vector3().fromArray(options.target)
  let framingPoints: Vector3[] = []
  let heroDistance = options.minimumDistance
  let elevation = 17
  let distanceFactor = 1
  const direction = new Vector3()

  function place() {
    const lookAt = target.clone()
    if (camera.aspect < options.narrowAspect) lookAt.y += options.narrowTargetLift
    direction.copy(viewDirection(options.azimuth, elevation))
    camera.position.copy(direction).multiplyScalar(heroDistance * distanceFactor).add(lookAt)
    camera.lookAt(lookAt)
    camera.updateMatrixWorld()
  }

  return {
    get distance() { return heroDistance * distanceFactor },
    get heroDirection() { return viewDirection(options.azimuth, 17) },
    target,
    setFramingPoints(points: Vector3[]) {
      framingPoints = points
      this.setViewport(camera.aspect)
    },
    setViewport(aspect: number) {
      camera.aspect = aspect
      camera.updateProjectionMatrix()
      heroDistance = fitDistance(framingPoints, camera, options.minimumDistance)
      camera.far = Math.max(100, heroDistance * 6)
      camera.updateProjectionMatrix()
      place()
    },
    applyState(state: SectionState) {
      elevation = state.camera.elevation
      distanceFactor = state.camera.distance
      place()
    },
  }
}
