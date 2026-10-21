<script setup lang="ts">
const links = [
  { href: '#upload', label: '流程' },
  { href: '#model', label: '建模' },
  { href: '#controls', label: '調光' },
  { href: '#interaction', label: '互動' },
  { href: '#cta', label: '開始使用' },
]
</script>

<template>
  <header class="nav">
    <a class="nav-brand" href="#hero">Picture to Model</a>
    <nav aria-label="頁面導覽">
      <ul>
        <li v-for="link in links" :key="link.href"><a :href="link.href">{{ link.label }}</a></li>
      </ul>
    </nav>
  </header>
</template>
