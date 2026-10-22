<script setup lang="ts">
// Highlighted chips are included in every trip; the rest are add-ons.
const features = [
  { label: '夜潛', on: true },
  { label: '水下攝影', on: true },
  { label: '裝備全包', on: true },
  { label: '自由潛水', on: false },
  { label: '船宿行程', on: false },
  { label: '私人教練', on: false },
]
</script>

<template>
  <section id="interaction" class="section section-interaction" aria-labelledby="interaction-title">
    <span class="num right" aria-hidden="true">04</span>
    <div class="copy">
      <span class="rule" aria-hidden="true" />
      <p class="eyebrow">04 · 體驗</p>
      <h2 id="interaction-title">下水之後,<br>才是開始</h2>
      <p class="lede">夜潛看螢光珊瑚、放流潛水跟著洋流走、教練幫你拍水下照片。裝備、保險、船班全包,亮起的項目每趟都有,其餘可加購。</p>
      <ul class="prop chips">
        <li v-for="feature in features" :key="feature.label" :class="{ on: feature.on }">{{ feature.label }}</li>
      </ul>
    </div>
  </section>
</template>
