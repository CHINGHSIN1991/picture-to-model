# summary/ — 各 Step 總結

每份文件對應一個 roadmap step,內容固定為四節:**這一步做了什麼 / 產出 / 技術說明 / Takeaway**。
roadmap 是「該怎麼做」,這裡是「實際做了什麼、結果如何、學到什麼」。
每份開頭的「代表結果」放一張代表圖與一段代表程式碼或資料;圖片集中在 [assets/](assets/),原檔在 `blender/renders/` 或 `web/screenshots/`。

| Step | 總結 | 狀態 | 關鍵結果 |
|---|---|---|---|
| 00 | [環境準備](00-environment-setup.md) | 完成 | Blender 5.2.0 LTS headless smoke test 通過 |
| 01 | [概念圖](01-concept-images.md) | 完成 | 一張概念圖通過六項評估,幾何警訊已列出 |
| 02 | [選定 reference 與建模分析](02-pick-reference-and-analyze.md) | 完成 | MODEL_PLAN + PROJECT_SPEC,專案值與 roadmap 分離 |
| 03 | [Graybox](03-graybox.md) | 完成 | 單峰山體重建,7,786 tri,91 物件 / 26 unique meshes |
| 04 | [完整模型](04-detailed-model.md) | 完成 | 49,420 tri / 16,690 unique,一張 64×64 色票、一個材質 |
| 05 | [Render 檢查與修正](05-render-and-inspect.md) | 完成 | 接合 / 互穿 / 法線問題歸零,回歸比對全通過 |
| 06 | [匯出 GLB](06-export-glb.md) | 完成 | 0.625 MB、95 nodes / 26 meshes，重新匯入與 validator 通過 |
| 07 | [最小 Three.js Viewer](07-minimal-threejs-viewer.md) | 完成 | 全螢幕模型檢視、相機取景、OrbitControls、四項瀏覽器測試通過 |
| 08 | [瀏覽器水下調光](08-web-lighting.md) | 完成 | 集中 config、debug 調光面板、水光與霧氣，M4 / Metal 實測 60 FPS |
| 09 | [網站 Mockup](09-website-mockup.md) | 完成 | 平台產品頁;三張 HTML 合成候選,選定編輯排版;SECTIONS.md 定 6 段與繞行一圈的零件狀態 |
| 10 | [網站實作](10-implement-website.md) | 完成 | 固定 canvas + 六個 section 元件，Three/Vue 分離，config 皆 plain object，十項測試通過 |
| 11 | [滑鼠跟隨互動](11-pointer-interaction.md) | 完成 | 微幅傾斜、阻尼回正、動態偏好與觸控停用，13 項瀏覽器測試通過 |
| 12–17 | Web 後續階段 | 未開始 | — |

## 跨 step 的共同 takeaway

1. **每一步的 Definition of Done 都寫成程式**:`02_detail.py` 末尾的 `assert`、`03_inspect.py` 的 `errors` list,搭配 `--python-exit-code 1`,重跑腳本等於跑測試。
2. **結構用程式保證,不靠調參**:單一 summit vertex、向上單調收窄、decimate ratio 由預算反推、UV 指向色塊中心。
3. **隨機流分離 + 固定 seed**:地形、每類零件、擺放各自獨立,改一處不會牽動其他。
4. **每次迭代都留基準快照 + 機器可讀的 review**:`iteration_review.json`、`scene_comparison.json`、`render_manifest.json` 的 SHA-256,讓「只改了該改的」可以被證明。
5. **render 是必要但不充分的檢查**:Step 05 的幾何量測抓到 render 看不出的 64 個接合問題。
6. **Blender 只負責靜態 mesh、階層、一張色票**:動畫、擺動、氣泡、光束全部留給 Web,scope 才守得住。
