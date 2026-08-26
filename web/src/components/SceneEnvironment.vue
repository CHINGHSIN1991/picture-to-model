<script setup lang="ts">
// 把等距長方 HDRI 掛到 scene.environment,所有 MeshStandardMaterial 自動獲得 IBL。
// 必須放在 <TresCanvas> 內(useTresContext 需要 canvas 供應的 context)。
import { useTresContext } from '@tresjs/core'
import { Color, EquirectangularReflectionMapping, type Texture } from 'three'
import { watchEffect } from 'vue'

const props = defineProps<{
  texture: Texture
  // 對映 Blender World Background 的 Strength(setup_lighting.py 為 0.4)
  intensity?: number
  // 純色背景(一致性驗證用白底);不設則沿用 canvas clear color
  background?: string
  // 直接以 HDRI 當背景(editor 的 background.type = environment)
  envAsBackground?: boolean
  // HDRI 繞垂直軸旋轉(度)。對映 Blender 端 Mapping 節點的 Z 旋轉;
  // 兩端旋轉方向的正負號一致性待目視校驗(studio HDRI 各向性低,影響小)
  rotation?: number
}>()

const { scene } = useTresContext()

watchEffect(() => {
  props.texture.mapping = EquirectangularReflectionMapping
  scene.value.environment = props.texture
  scene.value.environmentIntensity = props.intensity ?? 1
  const rad = ((props.rotation ?? 0) * Math.PI) / 180
  scene.value.environmentRotation.set(0, rad, 0)
  scene.value.backgroundRotation.set(0, rad, 0)
  scene.value.background = props.envAsBackground
    ? props.texture
    : props.background
      ? new Color(props.background)
      : null
})
</script>

<template><!-- 無視覺輸出,只設定 scene 環境 --></template>
