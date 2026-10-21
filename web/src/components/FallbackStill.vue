<script setup lang="ts">
// Step 14: the still that replaces the live scene. Captured from the same renderer, camera and
// lighting as the hero state (scripts/render-fallback.mjs), one composition per orientation.
const base = `${import.meta.env.BASE_URL}fallback/`
const portrait = `${base}hero-portrait.webp 1x, ${base}hero-portrait@2x.webp 2x`
const landscape = `${base}hero-landscape.webp 1x, ${base}hero-landscape@2x.webp 2x`
</script>

<template>
  <picture class="still">
    <source media="(orientation: landscape)" type="image/webp" :srcset="landscape">
    <img :src="`${base}hero-portrait.webp`" :srcset="portrait" alt="" decoding="async" fetchpriority="high">
  </picture>
</template>
