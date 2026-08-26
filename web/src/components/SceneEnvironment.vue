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
}>()

const { scene } = useTresContext()

watchEffect(() => {
  props.texture.mapping = EquirectangularReflectionMapping
  scene.value.environment = props.texture
  scene.value.environmentIntensity = props.intensity ?? 1
  if (props.background) scene.value.background = new Color(props.background)
})
</script>

<template><!-- 無視覺輸出,只設定 scene 環境 --></template>
