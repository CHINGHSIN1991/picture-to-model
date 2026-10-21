<script setup lang="ts">
import concept from '../assets/final-concept-800.webp'
</script>

<template>
  <section id="upload" class="section section-upload" aria-labelledby="upload-title">
    <span class="num" aria-hidden="true">01</span>
    <figure class="prop input">
      <figcaption class="label">輸入 · 概念圖</figcaption>
      <img :src="concept" width="800" height="600" loading="lazy" decoding="async" alt="示範用的珊瑚礁概念圖">
      <span class="arrow" aria-hidden="true" />
    </figure>
    <div class="copy right">
      <span class="rule" aria-hidden="true" />
      <p class="eyebrow">01 · 上傳</p>
      <h2 id="upload-title">從一張圖<br>開始</h2>
      <p class="lede">平台讀圖,分析輪廓、比例與零件,先堆出 graybox 的山體,確認剪影之後才加細節。你不用開 Blender。</p>
      <dl class="stats">
        <div><dt>張圖</dt><dd>1</dd></div>
        <div><dt>Graybox tri</dt><dd>7,786</dd></div>
        <div><dt>視角檢查</dt><dd>6</dd></div>
      </dl>
    </div>
  </section>
</template>
