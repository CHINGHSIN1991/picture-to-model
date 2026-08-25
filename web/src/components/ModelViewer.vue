<script setup lang="ts">
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import { computed } from 'vue'
import { Box3, Vector3 } from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

const props = defineProps<{ url: string }>()

const gltf = await new GLTFLoader().loadAsync(props.url)
const model = gltf.scene

const cameraPos = new Vector3(2.2, 1.4, 2.2)
const origin = new Vector3(0, 0, 0)
const keyLightPos = new Vector3(4, 6, 4)
const fillLightPos = new Vector3(-4, 2, -4)
const gridPos = new Vector3(0, -0.8, 0)

// AI 生成模型的原點與尺度不可預期:置中並縮放到單位大小
const normalized = computed(() => {
  const box = new Box3().setFromObject(model)
  const size = box.getSize(new Vector3())
  const center = box.getCenter(new Vector3())
  const scale = 1.6 / Math.max(size.x, size.y, size.z)
  model.position.sub(center).multiplyScalar(scale)
  model.position.y += (size.y * scale) / 2 - 0.8
  model.scale.setScalar(scale)
  return model
})
</script>

<template>
  <TresCanvas clear-color="#1a1a2e" shadows>
    <TresPerspectiveCamera :position="cameraPos" :look-at="origin" />
    <OrbitControls enable-damping :min-distance="1" :max-distance="8" />
    <TresAmbientLight :intensity="0.5" />
    <TresDirectionalLight :position="keyLightPos" :intensity="1.4" cast-shadow />
    <TresDirectionalLight :position="fillLightPos" :intensity="0.4" />
    <primitive :object="normalized" />
    <TresGridHelper :args="[10, 20, '#334', '#223']" :position="gridPos" />
  </TresCanvas>
</template>
