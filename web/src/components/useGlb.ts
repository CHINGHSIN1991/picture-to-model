// 共用 GLB loader:同時掛 MeshoptDecoder 與 DRACOLoader,兩種 gltf-transform 壓縮
// (EXT_meshopt_compression / KHR_draco_mesh_compression)與未壓縮的 GLB 都吃得下。
// - Draco 為 optimize stage 預設(2026-09-04 定案:<model-viewer> 原生支援 Draco、載不了 meshopt,
//   且 Draco 檔更小)。three r185 的 DRACOLoader 以 import.meta.url 定位解碼器,Vite 會把
//   draco_decoder.wasm / draco_wasm_wrapper.js 當資產打進 dist/assets/——不必手動託管 WASM。
// - meshopt 保留(decoder 隨 three 內建),舊產物與 --compress meshopt 仍可載。
// EXT_texture_webp / KHR_mesh_quantization 由 GLTFLoader 原生支援。
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'

const draco = new DRACOLoader()
draco.setDecoderConfig({ type: 'wasm' })

const loader = new GLTFLoader()
loader.setMeshoptDecoder(MeshoptDecoder)
loader.setDRACOLoader(draco)

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
