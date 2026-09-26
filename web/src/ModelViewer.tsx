import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export function ModelViewer({ url }: { url: string }) {
  const container = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const element = container.current
    if (!element) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x1a1a1a)
    const camera = new THREE.PerspectiveCamera(
      45,
      element.clientWidth / element.clientHeight,
      0.01,
      100,
    )
    camera.position.set(2, 2, 2)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(element.clientWidth, element.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    element.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true

    scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 2))
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.5)
    keyLight.position.set(3, 5, 2)
    scene.add(keyLight)

    let frame = 0
    let disposed = false

    new GLTFLoader().load(
      url,
      (gltf) => {
        if (disposed) return
        scene.add(gltf.scene)
        const bounds = new THREE.Box3().setFromObject(gltf.scene)
        const center = bounds.getCenter(new THREE.Vector3())
        const size = bounds.getSize(new THREE.Vector3()).length() || 1
        controls.target.copy(center)
        camera.position.copy(center).add(new THREE.Vector3(size, size, size).multiplyScalar(0.6))
        camera.near = size / 100
        camera.far = size * 100
        camera.updateProjectionMatrix()
      },
      undefined,
      (error) => console.error('GLB load failed', error),
    )

    const render = () => {
      controls.update()
      renderer.render(scene, camera)
      frame = requestAnimationFrame(render)
    }
    render()

    const resize = () => {
      const { clientWidth, clientHeight } = element
      camera.aspect = clientWidth / clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(clientWidth, clientHeight)
    }
    const observer = new ResizeObserver(resize)
    observer.observe(element)

    return () => {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      controls.dispose()
      scene.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) return
        object.geometry.dispose()
        const materials = Array.isArray(object.material) ? object.material : [object.material]
        for (const material of materials) {
          for (const value of Object.values(material)) {
            if (value instanceof THREE.Texture) value.dispose()
          }
          material.dispose()
        }
      })
      renderer.dispose()
      // Browsers cap live WebGL contexts; release ours instead of waiting for GC.
      renderer.forceContextLoss()
      element.removeChild(renderer.domElement)
    }
  }, [url])

  return <div ref={container} data-testid="model-canvas" className="model-canvas" />
}
