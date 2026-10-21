<script setup lang="ts">
const features = [
  { label: 'scroll 敘事', on: true },
  { label: '游標跟隨', on: true },
  { label: '逐件動畫', on: true },
  { label: '手機 fallback', on: false },
  { label: '離開畫面暫停', on: false },
  { label: 'DPR 上限', on: false },
]
</script>

<template>
  <section id="interaction" class="section section-interaction" aria-labelledby="interaction-title">
    <span class="num right" aria-hidden="true">04</span>
    <div class="copy">
      <span class="rule" aria-hidden="true" />
      <p class="eyebrow">04 · 互動</p>
      <h2 id="interaction-title">放進網站,<br>就會動</h2>
      <p class="lede">捲動時模型穿過頁面,零件依設定堆起、長出、環繞;游標跟隨、手機靜態 fallback、離開畫面暫停,全部內建。</p>
      <ul class="prop chips">
        <li v-for="feature in features" :key="feature.label" :class="{ on: feature.on }">{{ feature.label }}</li>
      </ul>
    </div>
  </section>
</template>
