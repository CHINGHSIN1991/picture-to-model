// 共用 GLB loader:掛上 MeshoptDecoder,才吃得下 gltf-transform 壓過的
// EXT_meshopt_compression GLB(npm run optimize:glb);未壓縮的 GLB 照常載。
// EXT_texture_webp / KHR_mesh_quantization 由 GLTFLoader 原生支援。
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'

const loader = new GLTFLoader()
loader.setMeshoptDecoder(MeshoptDecoder)

export function loadGlb(url: string): Promise<GLTF> {
  return loader.loadAsync(url)
}

// 快取版(同 useHdri 的作法):比較模式切換變體時不必重新下載 + 重新解析多 MB 的 GLB。
// 回傳的是共用實例——呼叫端必須 clone scene 後再改動(位置/縮放/材質指派),
// 會直接改動材質屬性的呼叫端(editor/embed)請用未快取的 loadGlb。
const glbCache = new Map<string, Promise<GLTF>>()

export function loadGlbShared(url: string): Promise<GLTF> {
  let p = glbCache.get(url)
  if (!p) {
    p = loader.loadAsync(url)
    p.catch(() => glbCache.delete(url)) // 失敗不留快取,重試時可再載
    glbCache.set(url, p)
  }
  return p
}
