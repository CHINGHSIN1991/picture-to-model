import GUI from 'lil-gui'
import Stats from 'stats.js'
import type { LightingConfig } from './lightingConfig'

export function createLightingDebug(config: LightingConfig, apply: () => void) {
  const gui = new GUI({ title: '水下調光', width: 280 })
  gui.domElement.dataset.lightingDebug = ''
  gui.domElement.style.maxWidth = 'calc(100vw - 20px)'
  gui.domElement.style.maxHeight = 'calc(100dvh - 20px)'
  gui.domElement.style.overflowY = 'auto'
  gui.add(config, 'exposure', 0.3, 2, 0.01).name('曝光')
  gui.add(config, 'environmentIntensity', 0, 2, 0.01).name('環境反射')
  const ambient = gui.addFolder('環境光')
  ambient.addColor(config.ambient, 'sky').name('天空色')
  ambient.addColor(config.ambient, 'ground').name('地面色')
  ambient.add(config.ambient, 'intensity', 0, 4, 0.01).name('強度')
  ambient.close()
  for (const [id, label] of [['key', '主光'], ['fill', '補光'], ['rim', '輪廓光']] as const) {
    const folder = gui.addFolder(label)
    folder.addColor(config[id], 'color').name('顏色')
    folder.add(config[id], 'intensity', 0, 8, 0.01).name('強度')
    for (const [index, axis] of ['X', 'Y', 'Z'].entries()) {
      folder.add(config[id].position, String(index) as '0' | '1' | '2', -8, 8, 0.1).name(axis)
    }
    folder.close()
  }
  const shadow = gui.addFolder('陰影')
  shadow.add(config.shadow, 'radius', 1, 8, 0.1).name('柔化半徑')
  shadow.add(config.shadow, 'intensity', 0, 1, 0.01).name('深度')
  shadow.close()
  const fog = gui.addFolder('霧氣')
  fog.add(config.fog, 'enabled').name('啟用')
  fog.addColor(config.fog, 'color').name('顏色')
  fog.add(config.fog, 'near', 0, 12, 0.1).name('起點')
  fog.add(config.fog, 'far', 6, 40, 0.1).name('終點')
  fog.close()
  const water = gui.addFolder('水光')
  water.addColor(config.water, 'top').name('上方水色')
  water.addColor(config.water, 'bottom').name('下方水色')
  water.addColor(config.water, 'rayColor').name('光束色')
  water.add(config.water, 'rayStrength', 0, 0.5, 0.01).name('光束強度')
  water.add(config.caustics, 'strength', 0, 0.8, 0.01).name('水紋強度')
  water.add(config.caustics, 'scale', 1, 12, 0.1).name('水紋密度')
  water.add(config.caustics, 'speed', 0, 1, 0.01).name('速度')
  water.add(config.caustics, 'animated').name('動畫')
  water.close()
  const material = gui.addFolder('材質')
  material.add(config.material, 'roughness', 0.1, 1, 0.01).name('粗糙度')
  material.add(config.material, 'metalness', 0, 1, 0.01).name('金屬度')
  material.addColor(config.material, 'coralEmissive').name('珊瑚發光色')
  material.add(config.material, 'coralIntensity', 0, 0.5, 0.01).name('珊瑚發光強度')
  material.close()
  gui.add({ exportConfig: () => console.info('[reef-viewer] lightingConfig', JSON.stringify(config, null, 2)) }, 'exportConfig').name('輸出設定至 Console')
  gui.add({ reset: () => gui.reset() }, 'reset').name('還原設定')
  gui.onChange(apply)
  for (const controller of gui.controllersRecursive()) {
    controller.domElement.querySelectorAll('input').forEach((input) => input.setAttribute('aria-label', controller.$name.textContent ?? ''))
  }
  const stats = new Stats()
  stats.dom.dataset.lightingStats = ''
  stats.dom.style.top = '52px'
  document.body.append(stats.dom)
  return {
    update: () => stats.update(),
    dispose() {
      gui.destroy()
      stats.dom.remove()
    },
  }
}
