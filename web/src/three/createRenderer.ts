import { ACESFilmicToneMapping, PCFShadowMap, SRGBColorSpace, WebGLRenderer } from 'three'
import { rendererConfig } from './config/renderer'
import { getRendererPixelRatio } from './rendererResolution'

export function createRenderer() {
  const renderer = new WebGLRenderer({ antialias: rendererConfig.antialias, powerPreference: rendererConfig.powerPreference })
  renderer.outputColorSpace = SRGBColorSpace
  renderer.toneMapping = ACESFilmicToneMapping
  renderer.toneMappingExposure = 1
  renderer.setPixelRatio(getRendererPixelRatio())
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = PCFShadowMap
  renderer.domElement.setAttribute('aria-label', '珊瑚礁與潛水員 3D 模型，可拖曳旋轉')
  renderer.domElement.setAttribute('role', 'img')
  return renderer
}
