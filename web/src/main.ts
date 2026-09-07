import { createApp } from 'vue'
import './style.css'

// 🎯 Embed 頁獨立成 chunk:?mode=embed 只載 EmbedViewer(+ three / tresjs 共用 chunk),
// 不載編輯器 / 比較 / 一致性 / 減面策略頁的程式碼——嵌入頁首屏重量最敏感(D-1 4G < 3s)。
const mode = new URLSearchParams(location.search).get('mode')
const root =
  mode === 'embed'
    ? import('./components/EmbedViewer.vue')
    : import('./App.vue')

root.then(({ default: Root }) => createApp(Root).mount('#app'))
