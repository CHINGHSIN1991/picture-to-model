# Blender → Web 3D 工作 Roadmap

從「概念圖」到「可互動的 Three.js 網站」的完整工作流程。
每個步驟一份獨立文件，照順序執行即可。

> 來源整理自影片《GPT 6 Astra + Blender = INSANE 3D Websites》、
> `cth9191/blender-to-web` 與 `ifBars/blender-agent-studio`，
> 並依照本專案目標（圖片 → Blender 3D → 可調材質/光線 → 放入網站的平台）做了調整。

## 核心原則

1. **先概念圖,再建模** — 不要讓 AI 直接在 Blender 裡「想設計」。
2. **先 Graybox,再細節** — 先確認輪廓與比例,再投入材質。
3. **每一步都要 render 檢查** — `.blend` 檔存在不代表完成。
4. **永遠保存 Blender Python source** — 讓模型可重現、可修改、可自動 regenerate。
5. **網站也先做 mockup** — 不要邊寫 CSS 邊想畫面。
6. **Web 端效能是設計的一部分** — mobile fallback、offscreen pause、DPR 限制、audit。

## 步驟索引

| # | 文件 | 階段 | 產出 |
|---|------|------|------|
| 00 | [00-environment-setup.md](./00-environment-setup.md) | 環境 | Blender / Codex / Bun / Blender Agent Studio / blender-to-web |
| 01 | [01-concept-images.md](./01-concept-images.md) | 概念 | `references/concept-*.png` |
| 02 | [02-pick-reference-and-analyze.md](./02-pick-reference-and-analyze.md) | 概念 | `references/final-concept.png` + 建模分析 |
| 03 | [03-graybox.md](./03-graybox.md) | Blender | graybox `.blend` + `.py` + 多角度 render |
| 04 | [04-detailed-model.md](./04-detailed-model.md) | Blender | 完整模型 `.blend` + `.py` |
| 05 | [05-render-and-inspect.md](./05-render-and-inspect.md) | Blender | 多角度 render 比對、修正 |
| 06 | [06-export-glb.md](./06-export-glb.md) | Export | 驗證過的 `.glb` + 報告 |
| 07 | [07-minimal-threejs-viewer.md](./07-minimal-threejs-viewer.md) | Web | 最簡 Three.js viewer |
| 08 | [08-web-lighting.md](./08-web-lighting.md) | Web | 瀏覽器端光線 / 材質調整 |
| 09 | [09-website-mockup.md](./09-website-mockup.md) | 設計 | `mockups/homepage-*.png` |
| 10 | [10-implement-website.md](./10-implement-website.md) | Web | Vue 3 + Vite + Three.js + GSAP 專案 |
| 11 | [11-pointer-interaction.md](./11-pointer-interaction.md) | 互動 | 滑鼠跟隨互動 |
| 12 | [12-scroll-storytelling.md](./12-scroll-storytelling.md) | 互動 | Scroll 驅動的敘事動畫 |
| 13 | [13-decomposable-model.md](./13-decomposable-model.md) | 互動 | 可拆解 / 重組的模型結構 |
| 14 | [14-mobile-fallback.md](./14-mobile-fallback.md) | 效能 | 手機靜態圖 fallback |
| 15 | [15-offscreen-pause.md](./15-offscreen-pause.md) | 效能 | 離開畫面暫停 render |
| 16 | [16-dpr-limit.md](./16-dpr-limit.md) | 效能 | DPR 上限 |
| 17 | [17-performance-audit.md](./17-performance-audit.md) | 效能 | 效能 audit 報告 |
| — | [pipeline-overview.md](./pipeline-overview.md) | 總覽 | 完整 pipeline 圖與本專案調整版 |

## 建議的專案目錄結構

```
blender-to-model/
├─ roadmap/                 ← 本資料夾
├─ references/              ← 概念圖、最終 reference
│  ├─ concept-01.png
│  ├─ concept-02.png
│  └─ final-concept.png
├─ blender/
│  ├─ scripts/              ← 可重現的 Python source(必存)
│  │  ├─ 01_graybox.py
│  │  └─ 02_detail.py
│  ├─ scenes/               ← .blend 檔
│  └─ renders/              ← 各角度 render
│     ├─ graybox/
│     └─ final/
├─ export/
│  └─ reef.glb
├─ mockups/                 ← 網站 mockup 圖
│  ├─ homepage-01.png
│  └─ final-homepage.png
└─ web/                     ← Vue 3 + Vite + Three.js 專案
```

## 怎麼使用這份 Roadmap

- 每份文件包含:**目標、為什麼、前置條件、操作步驟、可直接複製的 prompt、完成條件 (Definition of Done)、常見問題**。
- 一次只做一步,每一步的「完成條件」都達到了才往下。
- prompt 都是給 Codex(搭配 Blender Agent Studio)用的,可直接貼上。
