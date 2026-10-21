<script setup lang="ts">
import { lightingConfig } from '../three/lightingConfig'

// Static preview of the serializable Step 08 config; live editing stays behind `?debug` for now.
const rows = [
  { label: '曝光', value: lightingConfig.exposure.toFixed(2), percent: lightingConfig.exposure / 2 },
  { label: '主光', value: lightingConfig.key.intensity.toFixed(1), percent: lightingConfig.key.intensity / 5 },
  { label: '霧氣', value: lightingConfig.caustics.strength.toFixed(2), percent: lightingConfig.caustics.strength / 0.6 },
]
const water = [lightingConfig.water.top, lightingConfig.water.bottom]
</script>

<template>
  <section id="controls" class="section section-controls" aria-labelledby="controls-title">
    <span class="num" aria-hidden="true">03</span>
    <div class="copy right">
      <span class="rule" aria-hidden="true" />
      <p class="eyebrow">03 · 調光</p>
      <h2 id="controls-title">材質、光線、相機,<br>全是設定檔</h2>
      <p class="lede">在瀏覽器裡拖一下滑桿,場景立刻改變。每個參數都是 JSON,可以存下來、分享、套到下一個模型。</p>
      <figure class="prop panel">
        <figcaption class="label">lighting.json</figcaption>
        <div v-for="row in rows" :key="row.label" class="row">
          <span>{{ row.label }}</span>
          <div class="bar"><i :style="{ width: `${Math.round(row.percent * 100)}%` }" /></div>
          <span>{{ row.value }}</span>
        </div>
        <div class="row">
          <span>水色</span>
          <div><span v-for="color in water" :key="color" class="swatch" :style="{ background: color }" /></div>
          <span>{{ water[0] }}</span>
        </div>
      </figure>
    </div>
  </section>
</template>
