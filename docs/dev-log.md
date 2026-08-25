# 開發紀錄(Dev Log)

> 記錄每次程式碼更新的內容與對應的實測結果。
> 新的紀錄加在最上面;實測數據以 `output/<job_id>/metadata.json` 為準。

---

## 2026-08-25 — Phase 2 Step 2-1 / 2-2:Blender headless 環境 + 自動 cleanup

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/run_blender.py` | 新增。Blender headless 包裝器(跑在 uv venv):自動尋找執行檔(`.env` 的 `BLENDER_BIN` → PATH → `/Applications/Blender.app`),subprocess 呼叫 bpy 腳本、串流輸出、回傳 exit code、timeout 保護(預設 1800s)。 |
| `scripts/blender/_util.py` | 新增。bpy 共用工具:`--` 後引數解析、場景重置、GLB 匯入/匯出、選取、三角形計數。供後續 `setup_material.py`、`render.py` 等重用。 |
| `scripts/blender/cleanup_model.py` | 新增。核心修整腳本:合併 mesh(脫離 parent、清空 mesh 物件)→ 正規化(置中原點、最長邊縮放到 1 單位)→ 合併重複頂點 → 重算法線 → 刪內部面 → 匯出高模 → Collapse Decimate 到目標面數(預設 30K tris)→ 匯出 Web 版。統計自動寫回 `metadata.json` 的 `cleanup` 欄位。支援 `--job-dir` 自動推導路徑、`--keep-interior` 除錯旗標。 |
| `web/src/App.vue` | 模型清單加入 `/models/model.glb`(優化版),可與 `model_raw.glb` 切換比較。 |

使用方式:

```bash
uv run scripts/run_blender.py cleanup_model -- --job-dir output/<job_id>
```

### 實測結果

- 環境:Blender **5.2.0 LTS**(headless,`--background`),macOS(Apple Silicon)
- 測試模型:`output/160724017c66`(vintage-radio,Tripo PBR 模型)

| 項目 | 原始(model_raw.glb) | 高模(model_high.glb) | Web 版(model.glb) |
|---|---|---|---|
| 三角形數 | 501,102 | 500,932 | **30,000** |
| 檔案大小 | 15.1 MB | 15.1 MB | **1.6 MB**(-89%) |

- 修整統計:合併重複頂點 **6,821** 個、移除內部面 **170** 個、decimate ratio **0.0599**
- 耗時:**5.2 秒**(匯入 → 修整 → 雙版本匯出全程)
- 驗證:Web 版重新匯入 Blender 確認——30,000 tris、尺寸正規化為最長邊 1.0(dims ≈ 0.617 × 1.0 × 0.539)、材質貼圖完整保留
- 已知警告:glTF 匯出時出現 `More than one shader node tex image used for a texture`(Tripo 材質有多個 tex image 節點共用同一貼圖,取第一個 sampler),外觀未見異常,待 Step 2-3 `setup_material.py` 清理孤兒節點時一併處理

### 待辦 / 下一步

- [ ] 在 viewer 肉眼比較優化版 vs 原始版(decimate 對 UV/外觀的破壞程度)
- [ ] 用其餘測試素材(coral-mound、fishbowl)驗證 cleanup 邊界情況
- [ ] Step 2-3:`setup_material.py`(PBR 材質連結檢查、color space 修正、孤兒節點清理)
- [ ] Step 2-4:手動建 `assets/studio.blend` 攝影棚場景
- [ ] `web/public/models/` 為二進位產物,建議加入 `.gitignore`

---

## 2026-08-25 — Phase 1:Viewer 頁面(TresJS)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `web/src/components/ModelViewer.vue` | 新增。TresJS 3D 場景:透視相機、OrbitControls(damping、距離 1~8)、環境光 + 主/補兩盞方向光、地面網格。`GLTFLoader.loadAsync` top-level await 載入(需包 `<Suspense>`),以 `Box3` 自動置中並縮放到約 1.6 單位。 |
| `web/src/App.vue` | 改寫為 viewer 頁面:標題列 + 模型下拉選單,`<Suspense>` 包 `ModelViewer`,`:key` 切換重建。深色全版面佈局。 |
| scaffold 清理 | 刪除 `HelloWorld.vue`、`hero.png`、`vite.svg`、`vue.svg`。 |

### 實測結果

- 瀏覽器可載入 15.1 MB 的 `model_raw.glb`,拖曳旋轉、縮放正常
- AI 模型原點/尺度不可預期的問題由 viewer 端 bounding box 正規化解決(cleanup 上線後改由 pipeline 端正規化)

---

## 2026-08-25 — Phase 1:生成腳本 + 測試素材(commit `f955e76`)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/generate_model.py` | 新增。圖片 → Tripo API(上傳 → 建任務 → 輪詢 → 下載)→ `output/<job_id>/model_raw.glb` + `metadata.json`。支援 `--no-pbr`、`--check-balance`。 |
| `test-assets/` | 三類測試素材:hard-surface(vintage-radio)、organic(coral-mound)、reflective(fishbowl),各含多視角圖。 |

### 實測結果(job `160724017c66`)

- 輸入:`test-assets/hard-surface/vintage-radio/front.png`(單張)
- Provider:Tripo(`image_to_model`,PBR 開啟),輸出欄位 `pbr_model`
- 生成耗時:**112.1 秒**,GLB **15.1 MB**(501,102 tris)
- API 回傳同時附 `rendered_image` 預覽圖
