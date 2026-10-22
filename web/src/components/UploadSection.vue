<script setup lang="ts">
import concept from '../assets/final-concept-800.webp'
</script>

<template>
  <section id="upload" class="section section-upload" aria-labelledby="upload-title">
    <span class="num" aria-hidden="true">01</span>
    <figure class="prop input">
      <figcaption class="label">潛點 · 珊瑚花園</figcaption>
      <img :src="concept" width="800" height="600" loading="lazy" decoding="async" alt="珊瑚花園潛點插畫">
      <span class="arrow" aria-hidden="true" />
    </figure>
    <div class="copy right">
      <span class="rule" aria-hidden="true" />
      <p class="eyebrow">01 · 潛點</p>
      <h2 id="upload-title">從一座礁<br>開始</h2>
      <p class="lede">水深 5 到 18 公尺,能見度常年 20 公尺以上,硬珊瑚、海扇與成群的小丑魚就在岸邊。第一次下水,就從這裡開始。</p>
      <dl class="stats">
        <div><dt>最大水深</dt><dd>18 m</dd></div>
        <div><dt>能見度</dt><dd>20 m+</dd></div>
        <div><dt>水溫</dt><dd>27°C</dd></div>
      </dl>
    </div>
  </section>
</template>
