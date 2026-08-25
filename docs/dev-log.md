# 開發紀錄(Dev Log)

> 記錄每次程式碼更新的內容與對應的實測結果。
> 新的紀錄加在最上面;實測數據以 `output/<job_id>/metadata.json` 為準。

---

## 2026-08-25 — cleanup 修正:非水密網格的內部面誤刪防護 + TRELLIS.2 實測

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/blender/cleanup_model.py` | `repair_mesh()` 刪除內部面前先計算選中比例:超過 `MAX_INTERIOR_RATIO`(50%)視為 `select_interior_faces` 對非水密網格的誤判,跳過刪除並記警告。 |

**觸發案例**:TRELLIS.2 的輸出網格不是水密的(上游刻意停用 hole filling),`select_interior_faces` 把 196,738 / 199,953 個面誤判為內部面——修正前模型被刪到只剩 916 tris,修正後完整保留。回歸測試:Tripo 兩個 job(水密網格)行為不變(內部面移除 170 / 198 個)。

### TRELLIS.2 本地生成實測(vintage-radio,front.png,pipeline=512)

| 項目 | TRELLIS.2 本地(M4 24GB) | Tripo API |
|---|---|---|
| 生成耗時 | **451.7s** + 貼圖烘焙 167s ≈ **10.3 分** | **112.1s** |
| 原始輸出 | 1,824,936 tris → 內部簡化 ~200K tris、8.85 MB(KDTree 烘焙 1024 貼圖) | 501,102 tris、15.1 MB |
| cleanup 後 Web 版 | 36,649 tris、6.9 MB(decimate ratio 0.1518) | 30,000 tris、1.6 MB |
| 材質 | basecolor(KDTree 烘焙,無 Metal 加速) | 完整 PBR(basecolor + ORM + normal) |

- Web 版 36,649 tris 超過 30K 目標:Decimate modifier 的 ratio 按面數比例估算,對三角形分布不均的網格會有偏差,可接受;要精準就得迭代式 decimate(暫不做)
- 成果已放入 viewer(`trellis_radio.glb`),可與 Tripo 版(`model.glb`)比較模式對照
- 初步結論:**Tripo 品質與速度目前領先**(PBR 完整、水密網格、快 5 倍);TRELLIS.2 本地的優勢是免費、資料不出機器,若裝 Xcode Metal Toolchain 烘焙品質/速度可再提升

---

## 2026-08-25 — 測試:fishbowl(reflective 素材)全 pipeline 驗證

### 測試內容

以 `test-assets/reflective/fishbowl/front.png` 走完整流程:Tripo 生成 → cleanup → 材質檢查 → viewer(job `940b1dd831ac`)。目的:驗證 cleanup 對玻璃/反射類模型的邊界情況。

### 實測結果

| 階段 | 數據 |
|---|---|
| Tripo 生成 | **104.9s**、15.1 MB(501,284 tris) |
| cleanup | 高模 501,086 tris / Web 版 **30,000 tris**(ratio 0.0599)、**1.54 MB**(-90%),合併重複頂點 6,089、移除內部面 **198**,耗時 6.4s |
| setup_material | 1 材質、0 需修復(Tripo 輸出同樣符合 glTF PBR 標準) |

- 與 vintage-radio(hard-surface)數據幾乎同量級,pipeline 對不同類型素材行為一致
- **重要發現:Tripo 把玻璃烘成不透明表面**——GLB 內沒有 `alphaMode` / `KHR_materials_transmission`,反射與內容物全烘進 basecolor 貼圖。反射/透明類商品要呈現真實玻璃感,需在後製階段處理(Phase 3 可評估:偵測玻璃區域補 transmission 材質,或接受烘焙結果)
- 已複製到 `web/public/models/fishbowl{,_raw}.glb` 並加入 viewer 模型清單,可用比較模式肉眼確認內部面移除(198 個)沒有破壞雙層玻璃壁

### 待辦 / 下一步

- [ ] 比較模式肉眼檢查 fishbowl 玻璃壁完整性與 decimate 品質
- [ ] 剩餘素材:coral-mound(organic)驗證

---

## 2026-08-25 — Viewer:新增比較模式(decimate 前後並排對照)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `web/src/components/CompareViewer.vue` | 新增。左右雙 pane 並排比較:各自可選模型(預設左=原始、右=優化版),顯示三角形數與檔案大小,右側顯示相對左側的減少百分比(面數/檔案)。 |
| `web/src/components/cameraSync.ts` | 新增。共享相機狀態型別:由滑鼠所在 pane 發布 position/target,另一側跟隨。 |
| `web/src/components/ModelViewer.vue` | 擴充(向下相容):可選的 `sync`/`paneId` props 實現雙 canvas 相機同步(經 cientos OrbitControls 的 `instance` expose 與 `change` 事件);載入後統計三角形數(geometry index/position count)與檔案大小(HEAD content-length),以 `loaded` 事件回報。單一模式行為不變。 |
| `web/src/App.vue` | header 加入「單一檢視 / 比較模式」切換;比較模式隱藏單選下拉、顯示操作提示。 |

### 實測結果

- `npm run build`(含 `vue-tsc -b` 型別檢查)通過
- 相機同步機制:拖曳任一側,兩邊視角同步(以 pointerenter/pointerdown 決定發布方,避免回饋迴圈)
- 待肉眼驗證:model.glb(30K tris)vs model_raw.glb(501K tris)的外觀差異 → `npm run dev` 後切到比較模式

---

## 2026-08-25 — Phase 2 Step 2-3:setup_material.py(PBR 材質檢查與修復)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/blender/setup_material.py` | 新增。材質修復腳本:(1) 修 Image Texture 的 color space——連到 Base Color / Emission 用 sRGB,其餘一律 Non-Color;(2) 從 Material Output 反向走訪,移除沒有貢獻到輸出的孤兒節點;(3) 無材質的 mesh 補中性灰 Principled BSDF(#8A8A8A、Roughness 0.5)避免渲染全黑。統計寫進 `metadata.json` 的 `material` 欄位。支援 `--job-dir`(就地修復 model_high.glb + model.glb)或 `--input/--output` 單檔模式。 |

使用方式:

```bash
uv run scripts/run_blender.py setup_material -- --job-dir output/<job_id>
```

### 實測結果

- 對 `output/160724017c66` 執行:兩檔各 1 個材質,**0 個需要修復**(1.0s)——Tripo 輸出的節點結構已完全符合 glTF PBR 標準(BaseColor→Base Color、ORM→Separate Color→Metallic/Roughness、Normal→Normal Map),color space 也正確
- 三條修復路徑以測試案例驗證:
  - 無材質 cube → 正確補上 fallback 灰材質 ✅
  - 場景內單元測試(colorspace 設錯 ×2 + 孤兒節點 ×1)→ 全部斷言通過 ✅
- **前次記錄的 glTF 匯出警告已查明**:`More than one shader node tex image` 是 Blender 5.2 匯出器對「Metallic 與 Roughness 經 Separate Color 分接同一張 ORM 貼圖」的**誤報**(同一節點被計兩次),資料本身正確、無法也不需從資料端修,可忽略
- 注意:colorspace 修復在「匯入 GLB → 匯出」流程中理論上不會觸發(Blender glTF 匯入器會自動設對),它的價值在 Phase 3 自行烘焙/替換貼圖時作為安全網

### 待辦 / 下一步

- [ ] Step 2-4:手動建 `assets/studio.blend` 攝影棚場景(需 GUI 操作)
- [ ] Step 2-5+:setup_camera / setup_lighting / render 自動渲染商品圖

---

## 2026-08-25 — 本地生成方案評估:安裝 trellis-mac(TRELLIS.2 on Apple Silicon)

> 動機:除了 Tripo API,評估本地模型生成的可行性(免 API 費用、資料不出機器)。
> 選用 [shivampkumar/trellis-mac](https://github.com/shivampkumar/trellis-mac):Microsoft TRELLIS.2 的 Apple Silicon 移植版。
> 官方 TRELLIS.2 需 NVIDIA GPU(24GB VRAM、CUDA 12.4、僅 Linux),Mac 無法直接使用。

### 安裝環境

- 安裝位置:`~/Develop/trellis-mac`(獨立 repo,不在本專案內)
- 硬體:Apple M4、24GB 統一記憶體(官方建議的最低門檻)
- 軟體:Python 3.11.16(uv venv)、PyTorch 2.13.0(**MPS 可用**)

### 安裝過程與問題排解

| 步驟 | 結果 |
|---|---|
| `setup.sh`(clone 相依 repo + TRELLIS.2、建 venv、裝套件、套 MPS patch) | ✅ 完成 |
| Metal 加速後端 ×4(mtlbvh / mtldiffrast / mtlmesh / mtlgemm) | ❌ 編譯失敗:需要 `metal` 離線編譯器,本機只有 Command Line Tools 沒有完整 Xcode。自動 fallback 到 torch / 純 Python 路徑,**功能不受影響**,僅 texture 烘焙較慢、曲面貼圖品質稍差 |
| `o_voxel`(texture baking 後處理,Apple fork) | ⚠️ 初次失敗:缺 Eigen 標頭。修復:`brew install eigen` 後以 `CPATH=/opt/homebrew/include/eigen3` 重裝 → ✅ 成功 |
| HuggingFace 授權 | `hf auth login`(Read token)。兩個 gated model 需在網站申請:`briaai/RMBG-2.0`(同意即通過)、`facebook/dinov3-vitl16-pretrain-lvd1689m`(Meta 表單審核,當日通過) |

若之後想開啟 Metal 加速:App Store 裝 Xcode → `xcodebuild -downloadComponent MetalToolchain` → 重跑 `setup.sh`。

### 使用方式

```bash
cd ~/Develop/trellis-mac && source .venv/bin/activate
python generate.py <image.png> --output <name>   # 選項:--pipeline-type 512|1024|1024_cascade、--texture-size、--no-texture、--seed
```

### 實測結果

- 測試輸入:`test-assets/hard-surface/vintage-radio/front.png`(與 Tripo job `160724017c66` 同一張,方便對照)
- 首次執行下載約 16GB 權重(TRELLIS.2-4B + dinov3 + RMBG-2.0)
- 生成 **451.7s** + KDTree 貼圖烘焙 **167s**(無 Metal 加速的 fallback 路徑)≈ 10.3 分鐘
- 輸出:1,824,936 tris → 內部簡化 ~200K tris,`vintage-radio.glb` 8.85 MB(1024 貼圖)
- 詳細數據與 Tripo 對照見上方「TRELLIS.2 實測」條目

### 待辦 / 下一步

- [ ] 補上實測數據(耗時、面數、GLB 大小),與 Tripo 版本(112.1s、501K tris、15.1MB)比較品質
- [ ] 確認 TRELLIS.2 輸出能否直接接進現有 Blender cleanup pipeline
- [ ] 評估是否把本地生成整合進 `scripts/generate_model.py`(`--provider trellis`)

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
