# Picture-to-Model — Web Viewer / Scene Editor

Vue 3 + TypeScript + Vite + TresJS(Three.js)。

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # vue-tsc 型別檢查 + 產出 dist/
```

## 模式(header 切換,或 `?mode=` 深連結)

| 模式 | URL | 用途 |
|---|---|---|
| 單一檢視 | `/` | 模型下拉切換、旋轉縮放 |
| 比較模式 | `/?mode=compare` | 左右並排 + 相機同步 + wireframe(decimate 前後對照) |
| 一致性驗證 | `/?mode=consistency` | Blender 渲染圖 vs live viewer 同角度並排(docs/render-consistency.md) |
| 編輯器 | `/?mode=editor` | Phase 4B Scene Editor:燈光 / 材質 / 相機 / 背景滑桿,只寫 scene.json |
| 🎯 嵌入頁 | `/?mode=embed&model=<GLB>&scene=<scene.json>&poster=<webp>` | 主產出:無 chrome、poster 載入佔位,iframe 嵌任意網站(scene / poster 可省略) |

## 靜態資產(public/)

| 目錄 | 版控 | 說明 |
|---|---|---|
| `public/hdri/` | ✅ | studio HDRI(與 Blender 端 `assets/` 同一張,IBL 用);另有 `_512` 降檔版給 embed(只做 IBL 時載,省 1.1MB) |
| `public/renders/` | ✅ | 一致性驗證頁的 Blender 渲染圖(來源 `output/<job_id>/preview.webp`) |
| `public/models/` | ❌ gitignore | GLB 較大且可由 pipeline 重新生成,**需自行複製**: |

```bash
cp ../output/<job_id>/web/model.glb public/models/<名字>.glb   # pipeline optimize stage 的壓縮版(meshopt + WebP)
# 未壓縮版在 ../output/<job_id>/model.glb;然後在 src/modelList.ts 加一行;一致性驗證頁的配對在 ConsistencyViewer.vue 的 pairs
```

### GLB 瘦身

pipeline 的 `optimize` stage 已自動產出 `output/<job_id>/web/model.glb`(`uv run scripts/optimize_glb.py output/<job_id>` 可單獨重跑)。
手動壓任一 GLB 仍可用:

```bash
npm run optimize:glb -- public/models/<名字>.glb public/models/<名字>.glb
# meshopt + 貼圖 WebP,實測 −49%~−89%;viewer 已掛 MeshoptDecoder(useGlb.ts),壓縮與否都能載
# 注意:script 已鎖 --simplify false(面數歸 Blender 管)與 --palette false(材質名是 scene.json override 的 key)
```
