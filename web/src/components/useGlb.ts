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
