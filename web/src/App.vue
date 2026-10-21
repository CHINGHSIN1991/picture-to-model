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
const story = ref<HTMLElement>()
const query = new URLSearchParams(window.location.search)
// `?state=N` locks the scene for art direction, without scroll binding.
const preview = Number(query.get('state'))
const { status, message } = useThreeScene(stage, {
  debug: query.has('debug'),
  state: preview >= 1 && preview <= sections.length ? sections[preview - 1] : undefined,
}, story)

const sectionComponents = [HeroSection, UploadSection, ModelSection, ControlsSection, InteractionSection, CtaSection]
</script>

<template>
  <div class="site" :data-state="status">
    <div ref="stage" class="stage" aria-hidden="true" />
    <p v-if="status === 'error'" class="scene-error" role="alert">{{ message }}</p>
    <SiteNav />
    <main ref="story">
      <div v-for="(component, index) in sectionComponents" :key="sections[index]!.id" class="story-step">
        <component :is="component" />
      </div>
    </main>
  </div>
</template>
