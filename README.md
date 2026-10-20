# picture-to-model

從「概念圖」到「可互動的 Three.js 網站」的 Blender → Web 3D 工作流程。
完整步驟見 [roadmap/README.md](roadmap/README.md),一次做一步,達到每步的完成條件再往下。
roadmap 是通用流程;本專案的專案值(asset 名稱、零件群組、動畫方式、sections)集中在 [PROJECT_SPEC.md](PROJECT_SPEC.md)。

## 目錄結構

```
PROJECT_SPEC.md       本專案的專案值(roadmap 裡的 <asset> 等佔位符查這裡)
roadmap/              步驟文件(00–17)與 pipeline 總覽
references/           概念圖、最終 reference(Step 01–02)
blender/
  scripts/            可從空場景重現的 Blender Python source(必存)
  scenes/             .blend 檔
  renders/graybox/    graybox 多角度 render(Step 03)
  renders/final/      完整模型 render(Step 05)
export/               驗證過的 <asset>.glb(Step 06)
mockups/              網站 mockup 圖(Step 09)
web/                  Vue 3 + Vite + Three.js 專案(Step 07 起)
```

## 環境(Step 00)

| 工具 | 需求 | 安裝方式 |
|---|---|---|
| Blender | 5.2 LTS | https://www.blender.org/download/ |
| Codex CLI | 最新 | `npm install -g @openai/codex` |
| Bun | ≥ 1.3.5 | `curl -fsSL https://bun.sh/install \| bash` |
| Blender Agent Studio | 最新 | `codex plugin marketplace add ifBars/blender-agent-studio` 然後 `codex plugin add blender-agent-studio@blender-agent-studio` |
| blender-to-web | 參考用 | clone 於 `../blender-to-web`(與本 repo 同層) |

`~/.zshrc` 需有:

```bash
export BLENDER_EXECUTABLE="/Applications/Blender.app/Contents/MacOS/Blender"
```

### Smoke test

不經 Codex、直接用 Blender headless 驗證環境:

```bash
blender --background --python blender/scripts/smoke-test.py
```

會產生 `blender/renders/smoke-test.png` 與 `blender/scenes/smoke-test.blend`。
經 Codex + Blender Agent Studio 的版本請用 [roadmap/00-environment-setup.md](roadmap/00-environment-setup.md) 內的 prompt。

## 細部模型與渲染檢查（Step 04–05）

```bash
blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/02_detail.py
```

入口腳本搭配 `blender/scripts/detail_geometry.py`，從空場景重建單峰珊瑚礁，輸出
`blender/scenes/02_detail.blend`、`blender/textures/reef_palette.png`、
`blender/renders/final/` 六視角與潛水員近照。64×64 色票會封裝在 `.blend` 內。
面數與分組報告位於 `blender/renders/final/build_report.json`。

Step 05 已完成：修正珊瑚／海草接合與穿插，以及沙地朝下的法線。
單一主峰、物件階層與共用網格保留，場景維持 49,420 triangles。

- [主視角](blender/renders/final/hero.png)
- [六視角總覽](blender/renders/final/contact_sheet.png)（上排 hero / front / left，下排 right / back / top）
- [檢查報告](blender/renders/final/final_report.md)
- [修正前快照](blender/revisions/detail_before_step05/)

重新載入場景執行接合、法線、材質與回歸檢查：

```bash
blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/03_inspect.py
```

此檢查使用保存的 Step 04 快照比對，輸出 `technical_checks.json`、
`scene_comparison.json` 與 `render_manifest.json`。

## Web 模型匯出（Step 06）

已產出 [reef.glb](export/reef.glb)：625,268 bytes（0.625 MB），49,420 triangles、
91 個網格節點共用 26 份幾何、一個材質及一張內嵌 64×64 色票。
重新匯入的幾何、階層、材質與九個視角均通過比對；glTF Validator 為 0 errors / 0 warnings。

```bash
blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/03_export.py
npm ci --prefix tools/gltf
npm --prefix tools/gltf run validate
```

- [匯出前後主視角比對](blender/renders/export/hero_comparison.png)（左：原場景，右：GLB 重新匯入）
- [重新匯入六視角總覽](blender/renders/export/contact_sheet.png)
- [Asset 報告](export/REPORT.md) · [Step 06 總結](summary/06-export-glb.md)

匯出檔保留獨立互動節點；網頁端 instancing 與實際 draw calls 會在後續 Web 階段處理。
GLB 與渲染影像依既有 `.gitignore` 規則由腳本重建。

## 最小 Three.js Viewer（Step 07）

已建立全螢幕模型檢視頁，包含基本燈光、與 Blender 接近的主視角、
OrbitControls、響應式尺寸與 DPR 上限 1.5。

```bash
cd web
bun install --frozen-lockfile
bun run dev
```

啟動時自動同步 `export/reef.glb`。拖曳旋轉、滾輪縮放、右鍵平移。
Production build 與四項 Chrome 瀏覽器測試通過，95 個 node 的名稱及父子關係均與 GLB 相符。

- [使用與驗證方式](web/README.md)
- [Step 07 總結與實際截圖](summary/07-minimal-threejs-viewer.md)

## 瀏覽器水下調光（Step 08）

已加入藍色水域、右上主光、冷色輪廓光、淡霧、水紋及微量珊瑚自發光。
所有參數集中在 `web/src/three/lightingConfig.ts`。
在 viewer 網址加上 `?debug` 可開啟調光面板與 FPS，並將設定輸出成 JSON。

Build 與七項瀏覽器測試通過；Apple M4 / Metal 在 1440×900、DPR 1.5、
開啟動畫及調光面板的 10 秒量測平均為 60.0 FPS。

- [Step 08 總結與比較圖](summary/08-web-lighting.md)
- [瀏覽器主視角](web/screenshots/lighting-v1.png)
- [效能量測報告](web/screenshots/lighting-report.json)

下一步為 Step 09：網站 mockup。

## 原則

1. 先概念圖,再建模。
2. 先 graybox,再細節。
3. 每一步都 render 檢查。
4. 永遠保存 Blender Python source,讓模型可重現。
5. 網站先做 mockup。
6. Web 效能(mobile fallback、offscreen pause、DPR 限制)是設計的一部分。
7. 動畫方式是資料不是程式:零件怎麼動寫在 PROJECT_SPEC,程式讀 config,不寫死任何一種效果。
