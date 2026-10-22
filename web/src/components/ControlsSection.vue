<script setup lang="ts">
// Course ladder: days on site per level, bar length relative to the longest course.
const rows = [
  { label: '體驗潛水', value: '1 天', percent: 0.25 },
  { label: 'Open Water', value: '3 天', percent: 0.75 },
  { label: 'Advanced', value: '2 天', percent: 0.5 },
  { label: '深度上限', value: '30 m', percent: 1 },
]
</script>

<template>
  <section id="controls" class="section section-controls" aria-labelledby="controls-title">
    <span class="num" aria-hidden="true">03</span>
    <div class="copy right">
      <span class="rule" aria-hidden="true" />
      <p class="eyebrow">03 · 課程</p>
      <h2 id="controls-title">從體驗潛,<br>到進階證照</h2>
      <p class="lede">體驗潛水、Open Water、Advanced,每一級都由專屬教練小班帶領。學科在線上先看完,到了現場直接下水。</p>
      <figure class="prop panel">
        <figcaption class="label">課程階梯</figcaption>
        <div v-for="row in rows" :key="row.label" class="row">
          <span>{{ row.label }}</span>
          <div class="bar"><i :style="{ width: `${Math.round(row.percent * 100)}%` }" /></div>
          <span>{{ row.value }}</span>
        </div>
      </figure>
    </div>
  </section>
</template>
