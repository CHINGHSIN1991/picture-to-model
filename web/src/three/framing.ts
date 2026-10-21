import { MathUtils, Mesh, Object3D, PerspectiveCamera, Vector3 } from 'three'

/** Unit vector from the look target towards a camera at the given Blender-style angles. */
export function viewDirection(azimuthDeg: number, elevationDeg: number) {
  const azimuth = MathUtils.degToRad(azimuthDeg)
  const elevation = MathUtils.degToRad(elevationDeg)
  return new Vector3(Math.cos(elevation) * Math.sin(azimuth), Math.sin(elevation), Math.cos(elevation) * Math.cos(azimuth))
}

/**
 * Project every vertex into the camera basis (right, up, towards camera) relative to the target.
 * Fitting these points, rather than bounding-box corners, keeps a cone-shaped reef large in frame.
 */
export function collectFramingPoints(model: Object3D, target: Vector3, direction: Vector3) {
  const right = new Vector3().crossVectors(new Vector3(0, 1, 0), direction).normalize()
  const up = new Vector3().crossVectors(direction, right).normalize()
  const points: Vector3[] = []
  const vertex = new Vector3()
  model.updateMatrixWorld(true)
  model.traverse((object) => {
    const mesh = object as Mesh
    if (!mesh.isMesh) return
    const positions = mesh.geometry.attributes.position!
    for (let i = 0; i < positions.count; i++) {
      vertex.fromBufferAttribute(positions, i).applyMatrix4(mesh.matrixWorld).sub(target)
      points.push(new Vector3(vertex.dot(right), vertex.dot(up), vertex.dot(direction)))
    }
  })
  return points
}

/** Smallest camera distance (never below `minimum`) that keeps every framing point inside the view. */
export function fitDistance(points: Vector3[], camera: PerspectiveCamera, minimum: number, margin = 1.08) {
  const tanV = Math.tan(MathUtils.degToRad(camera.fov / 2))
  const tanH = tanV * camera.aspect
  let distance = minimum
  for (const point of points) {
    distance = Math.max(distance, point.z + margin * Math.max(Math.abs(point.x) / tanH, Math.abs(point.y) / tanV))
  }
  return distance
}
