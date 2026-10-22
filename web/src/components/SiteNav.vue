<script setup lang="ts">
const links = [
  { href: '#upload', label: '潛點' },
  { href: '#model', label: '行程' },
  { href: '#controls', label: '課程' },
  { href: '#interaction', label: '體驗' },
  { href: '#cta', label: '預約' },
]
</script>

<template>
  <header class="nav">
    <a class="nav-brand" href="#hero">Blue Reef Dive</a>
    <nav aria-label="頁面導覽">
      <ul>
        <li v-for="link in links" :key="link.href"><a :href="link.href">{{ link.label }}</a></li>
      </ul>
    </nav>
  </header>
</template>
