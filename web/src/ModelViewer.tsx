import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

function disposeObject(root: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>()
  const materials = new Set<THREE.Material>()
  const textures = new Set<THREE.Texture>()
  root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return
    geometries.add(object.geometry)
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      materials.add(material)
      for (const value of Object.values(material))
        if (value instanceof THREE.Texture) textures.add(value)
    }
    if (object instanceof THREE.SkinnedMesh) object.skeleton.dispose()
  })
  for (const geometry of geometries) geometry.dispose()
  for (const material of materials) material.dispose()
  for (const texture of textures) {
    texture.dispose()
    if (typeof ImageBitmap !== 'undefined' && texture.image instanceof ImageBitmap)
      texture.image.close()
  }
}

function ViewerScene({ url, onRetry }: { url: string; onRetry: () => void }) {
  const container = useRef<HTMLDivElement | null>(null)
  const actions = useRef<{ reset: () => void; zoom: (factor: number) => void } | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const element = container.current
    if (!element) return
    let disposed = false
    let failed = false
    let frame = 0
    let loadTimer = 0
    let renderer: THREE.WebGLRenderer | undefined
    let controls: OrbitControls | undefined
    let observer: ResizeObserver | undefined
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100)
    const fail = (message: string) => {
      if (disposed || failed) return
      failed = true
      cancelAnimationFrame(frame)
      window.clearTimeout(loadTimer)
      setError(message)
      setStatus('error')
    }
    const contextLost = (event: Event) => {
      event.preventDefault()
      fail('3D 顯示連線已中斷，請重新載入預覽。')
    }

    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.outputColorSpace = THREE.SRGBColorSpace
      renderer.toneMapping = THREE.ACESFilmicToneMapping
      renderer.domElement.dataset.testid = 'model-canvas'
      renderer.domElement.setAttribute('aria-label', '3D 模型預覽：拖曳旋轉、滾輪縮放、方向鍵平移')
      renderer.domElement.tabIndex = 0
      renderer.domElement.addEventListener('webglcontextlost', contextLost)
      element.appendChild(renderer.domElement)
      controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      controls.listenToKeyEvents(renderer.domElement)
      scene.add(new THREE.HemisphereLight(0xffffff, 0x88917b, 2.4))
      const keyLight = new THREE.DirectionalLight(0xffffff, 3)
      keyLight.position.set(3, 5, 4)
      scene.add(keyLight)
      const fillLight = new THREE.DirectionalLight(0xc4d8ff, 1)
      fillLight.position.set(-3, 1, -2)
      scene.add(fillLight)

      let bounds: THREE.Box3 | null = null
      const fit = () => {
        if (!bounds || !controls) return
        const center = bounds.getCenter(new THREE.Vector3())
        const radius = Math.max(bounds.getBoundingSphere(new THREE.Sphere()).radius, 0.001)
        const halfFov = THREE.MathUtils.degToRad(camera.fov / 2)
        const limitingFov = Math.min(halfFov, Math.atan(Math.tan(halfFov) * camera.aspect))
        const distance = (radius / Math.sin(limitingFov)) * 1.25
        controls.target.copy(center)
        camera.position
          .copy(center)
          .add(new THREE.Vector3(1, 0.65, 1.3).normalize().multiplyScalar(distance))
        camera.near = radius / 100
        camera.far = distance + radius * 100
        camera.updateProjectionMatrix()
        controls.minDistance = radius * 1.15
        controls.maxDistance = Math.max(radius * 30, distance * 2)
        controls.update()
        controls.saveState()
      }
      const resize = () => {
        const width = Math.max(element.clientWidth, 1)
        const height = Math.max(element.clientHeight, 1)
        camera.aspect = width / height
        camera.updateProjectionMatrix()
        renderer!.setSize(width, height)
        fit()
      }
      resize()
      observer = new ResizeObserver(resize)
      observer.observe(element)
      const render = () => {
        if (disposed || failed) return
        controls!.update()
        try {
          renderer!.render(scene, camera)
        } catch {
          fail('3D 預覽無法繪製，請重新載入或使用支援 WebGL 的瀏覽器。')
          return
        }
        frame = requestAnimationFrame(render)
      }
      loadTimer = window.setTimeout(() => fail('模型載入逾時，請確認連線後重新載入預覽。'), 30000)
      new GLTFLoader().load(
        url,
        (gltf) => {
          window.clearTimeout(loadTimer)
          if (disposed || failed) {
            disposeObject(gltf.scene)
            return
          }
          const modelBounds = new THREE.Box3().setFromObject(gltf.scene)
          let hasMesh = false
          gltf.scene.traverse((object) => {
            if (object instanceof THREE.Mesh && object.geometry.getAttribute('position')?.count)
              hasMesh = true
          })
          if (
            !hasMesh ||
            modelBounds.isEmpty() ||
            !Number.isFinite(modelBounds.getSize(new THREE.Vector3()).length())
          ) {
            disposeObject(gltf.scene)
            fail('模型沒有可顯示的幾何內容，請重新執行示範任務。')
            return
          }
          scene.add(gltf.scene)
          bounds = modelBounds
          fit()
          actions.current = {
            reset: fit,
            zoom: (factor) => {
              const offset = camera.position.clone().sub(controls!.target)
              offset.setLength(
                THREE.MathUtils.clamp(
                  offset.length() * factor,
                  controls!.minDistance,
                  controls!.maxDistance,
                ),
              )
              camera.position.copy(controls!.target).add(offset)
              controls!.update()
            },
          }
          // Ready means the downloaded GLB is in the scene and a render has succeeded.
          render()
          if (!failed) setStatus('ready')
        },
        undefined,
        () => fail('模型載入失敗，請確認本機服務仍在執行，再重新載入預覽。'),
      )
    } catch {
      queueMicrotask(() =>
        fail('無法啟動 3D 預覽。請啟用瀏覽器硬體加速，或使用支援 WebGL 的瀏覽器。'),
      )
    }
    return () => {
      disposed = true
      cancelAnimationFrame(frame)
      window.clearTimeout(loadTimer)
      observer?.disconnect()
      actions.current = null
      controls?.dispose()
      disposeObject(scene)
      if (renderer) {
        renderer.domElement.removeEventListener('webglcontextlost', contextLost)
        renderer.dispose()
        renderer.forceContextLoss()
        renderer.domElement.remove()
      }
    }
  }, [url])

  return (
    <div className="viewer-shell">
      <div ref={container} className="model-canvas" />
      {status === 'loading' && (
        <div className="viewer-overlay" role="status">
          <span className="loading-ring" />
          <p>正在載入 3D 模型…</p>
        </div>
      )}
      {status === 'error' && (
        <div className="viewer-overlay" role="alert">
          <p>{error}</p>
          <button className="button secondary" onClick={onRetry}>
            重新載入預覽
          </button>
        </div>
      )}
      {status === 'ready' && (
        <>
          <span className="viewer-ready" data-testid="model-ready">
            <span className="status-dot" />
            模型已就緒
          </span>
          <div className="viewer-controls">
            <button onClick={() => actions.current?.zoom(0.8)} aria-label="放大模型">
              ＋
            </button>
            <button onClick={() => actions.current?.zoom(1.25)} aria-label="縮小模型">
              −
            </button>
            <button onClick={() => actions.current?.reset()}>重設視角</button>
          </div>
          <p className="viewer-hint">拖曳旋轉 · 滾輪縮放 · 右鍵拖曳平移</p>
        </>
      )}
    </div>
  )
}

export function ModelViewer({ url }: { url: string }) {
  const [attempt, setAttempt] = useState(0)
  return (
    <ViewerScene
      key={`${url}:${attempt}`}
      url={url}
      onRetry={() => setAttempt((value) => value + 1)}
    />
  )
}
