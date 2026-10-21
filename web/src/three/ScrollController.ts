import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { sections, type SectionState } from './config/sections'
import { partGroupNames } from './config/partGroups'

gsap.registerPlugin(ScrollTrigger)

function flatten(state: SectionState): Record<string, number> {
  return {
    x: state.position[0], y: state.position[1], z: state.position[2],
    rx: state.rotation[0], ry: state.rotation[1], rz: state.rotation[2], scale: state.scale,
    elevation: state.camera.elevation, distance: state.camera.distance, emissive: state.emissive,
    ...Object.fromEntries(partGroupNames.map((name) => [`part_${name}`, state.parts[name]])),
  }
}

/** DOM geometry and GSAP only. Each section owns a separate numeric state, never a Three object. */
export class ScrollController {
  private records: { state: Record<string, number>; timeline: gsap.core.Timeline; trigger: ScrollTrigger }[] = []
  private steps: { wrapper: HTMLElement; section: HTMLElement; originalStyle: string | null }[]
  private reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
  private layoutReducedMotion = this.reducedMotion.matches
  private observer: ResizeObserver
  private refreshFrame = 0
  private disposed = false

  constructor(private container: HTMLElement, private states: SectionState[] = sections) {
    this.steps = states.map((state) => {
      const section = container.querySelector<HTMLElement>(`#${state.id}`)
      if (!section || !section.parentElement?.classList.contains('story-step')) throw new Error(`Missing story section: ${state.id}`)
      const wrapper = section.parentElement
      return { wrapper, section, originalStyle: wrapper.getAttribute('style') }
    })
    this.rebuild()
    this.observer = new ResizeObserver(this.scheduleRefresh)
    this.steps.forEach(({ section }) => this.observer.observe(section))
    window.addEventListener('resize', this.scheduleRefresh)
    this.reducedMotion.addEventListener('change', this.onPreference)
    window.addEventListener('click', this.onClick)
    window.addEventListener('hashchange', this.onHash)
    // Initial hash navigation may have run before the additional hold distances existed.
    this.onHash()
    void document.fonts.ready.then(() => { if (!this.disposed) this.scheduleRefresh() })
  }

  private rebuild() {
    this.layoutReducedMotion = this.reducedMotion.matches
    this.records.forEach(({ trigger, timeline }) => { trigger.kill(); timeline.kill() })
    this.records = []
    this.steps.forEach(({ wrapper, section }, index) => {
      const hold = !this.reducedMotion.matches && Boolean(this.states[index]!.partsOnEnter)
      wrapper.classList.toggle('story-hold', hold)
      wrapper.style.height = `${section.offsetHeight + (hold ? window.innerHeight : 0)}px`
      wrapper.style.setProperty('--pin-top', `${Math.min(0, window.innerHeight - section.offsetHeight)}px`)
    })
    this.states.forEach((target, index) => {
      const previous = this.states[Math.max(0, index - 1)]!
      const { wrapper } = this.steps[index]!
      const state = flatten(previous)
      const hold = wrapper.classList.contains('story-hold')
      const entry = hold ? { ...target, parts: { ...target.parts, ...target.partsOnEnter } } : target
      // Incoming travel ends when the section reaches its sticky position. The remaining
      // viewport of scroll changes only parts while the copy stays in place.
      const travel = hold ? Math.max(window.innerHeight, this.steps[index]!.section.offsetHeight) : wrapper.offsetHeight
      const timeline = gsap.timeline({ paused: true })
        .fromTo(state, flatten(previous), { ...flatten(entry), duration: travel, ease: 'none', immediateRender: false })
      if (hold) timeline.to(state, { ...flatten(target), duration: window.innerHeight, ease: 'none' })
      const trigger = ScrollTrigger.create({
        id: `story-${target.id}`, trigger: wrapper, start: 'top bottom', end: 'bottom bottom',
        scrub: true, animation: timeline,
      })
      this.records.push({ state, timeline, trigger })
    })
    this.records.forEach(({ trigger }) => trigger.refresh())
    ScrollTrigger.update()
  }

  private scheduleRefresh = () => {
    if (this.disposed || this.refreshFrame) return
    this.refreshFrame = requestAnimationFrame(() => { this.refreshFrame = 0; this.rebuild() })
  }

  private onPreference = () => {
    if (this.layoutReducedMotion === this.reducedMotion.matches) return
    const id = this.states[this.visibleIndex()]!.id
    this.rebuild()
    this.navigate(id, 'instant')
  }

  private visibleIndex() {
    let index = 0
    this.steps.forEach(({ wrapper }, i) => { if (wrapper.getBoundingClientRect().top <= innerHeight * 0.5) index = i })
    return index
  }

  /** Read once per render frame, after GSAP has updated all section timelines. */
  getState(): SectionState {
    // Reconcile as well as listening: a preference can change during startup/refresh
    // before a browser delivers its MediaQueryList change notification.
    if (this.layoutReducedMotion !== this.reducedMotion.matches) this.onPreference()
    if (this.reducedMotion.matches) {
      return this.states[this.visibleIndex()]!
    }
    let index = 0
    this.records.forEach(({ trigger }, i) => { if (window.scrollY > trigger.start) index = i })
    const record = this.records[index]
    if (!record) return this.states[0]!
    const value = record.state
    return {
      id: this.states[index]!.id,
      position: [value.x!, value.y!, value.z!], rotation: [value.rx!, value.ry!, value.rz!],
      scale: value.scale!, camera: { elevation: value.elevation!, distance: value.distance! }, emissive: value.emissive!,
      parts: Object.fromEntries(partGroupNames.map((name) => [name, value[`part_${name}`]!])) as SectionState['parts'],
    }
  }

  private navigate(id: string, behavior: ScrollBehavior) {
    const index = this.states.findIndex((state) => state.id === id)
    if (index < 0) return
    const wrapper = this.steps[index]!.wrapper
    window.scrollTo({ top: window.scrollY + wrapper.getBoundingClientRect().top, behavior })
    ScrollTrigger.update()
  }

  private onClick = (event: MouseEvent) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    const link = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('a[href]') : null
    if (!link || !this.container.parentElement?.contains(link) || link.target || link.hasAttribute('download')) return
    const url = new URL(link.href)
    if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search) return
    const id = url.hash.slice(1)
    if (!this.states.some((state) => state.id === id)) return
    event.preventDefault()
    history.pushState(null, '', url.hash)
    this.navigate(id, this.reducedMotion.matches ? 'instant' : 'smooth')
  }

  private onHash = () => { this.navigate(location.hash.slice(1), 'instant') }

  dispose() {
    if (this.disposed) return
    this.disposed = true
    cancelAnimationFrame(this.refreshFrame)
    this.observer.disconnect()
    window.removeEventListener('resize', this.scheduleRefresh)
    this.reducedMotion.removeEventListener('change', this.onPreference)
    window.removeEventListener('click', this.onClick)
    window.removeEventListener('hashchange', this.onHash)
    this.records.forEach(({ trigger, timeline }) => { trigger.kill(); timeline.kill() })
    this.records = []
    this.steps.forEach(({ wrapper, originalStyle }) => {
      wrapper.classList.remove('story-hold')
      if (originalStyle === null) wrapper.removeAttribute('style')
      else wrapper.setAttribute('style', originalStyle)
    })
  }
}
