<script setup lang="ts">
import { ref } from 'vue'
import { useThreeScene } from './composables/useThreeScene'
import { sections } from './three/config/sections'
import SiteNav from './components/SiteNav.vue'
import HeroSection from './components/HeroSection.vue'
import UploadSection from './components/UploadSection.vue'
import ModelSection from './components/ModelSection.vue'
import ControlsSection from './components/ControlsSection.vue'
import InteractionSection from './components/InteractionSection.vue'
import CtaSection from './components/CtaSection.vue'

const stage = ref<HTMLDivElement>()
const query = new URLSearchParams(window.location.search)
// `?state=N` previews section N's 3D state while scroll binding (Step 12) does not exist yet.
const preview = Number(query.get('state'))
const { status, message } = useThreeScene(stage, {
  debug: query.has('debug'),
  state: preview >= 1 && preview <= sections.length ? sections[preview - 1] : undefined,
})
</script>

<template>
  <div class="site" :data-state="status">
    <div ref="stage" class="stage" aria-hidden="true" />
    <p v-if="status === 'error'" class="scene-error" role="alert">{{ message }}</p>
    <SiteNav />
    <main>
      <HeroSection />
      <UploadSection />
      <ModelSection />
      <ControlsSection />
      <InteractionSection />
      <CtaSection />
    </main>
  </div>
</template>
