# 開發紀錄(Dev Log)

> 記錄每次程式碼更新的內容與對應的實測結果。
> 新的紀錄加在最上面;實測數據以 `output/<job_id>/metadata.json` 為準。

---

## 2026-08-26 — Embed 重量瘦身:GLB meshopt + WebP、HDRI 512 降檔(3.3MB → 1.33MB)

> 上一條的待辦「embed 重量瘦身」。方案定案:**meshopt 取代原規劃的 Draco**——
> Draco 解碼器要另外託管 WASM 檔,meshopt 的 decoder 隨 three 內建(`three/examples/jsm/libs/meshopt_decoder.module.js`),
> 靜態託管少一組檔案;壓縮率在本專案的模型上已足夠。

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `web/package.json` | devDependency `@gltf-transform/cli`;npm script **`optimize:glb`** = `gltf-transform optimize --compress meshopt --texture-compress webp --simplify false --palette false`(關 simplify:面數由 Blender decimate 管;關 palette:材質**名稱是 `materials_override` 的 key**,不能被合併改名)。 |
| `web/src/components/useGlb.ts` | 新增。共用 GLB loader,掛 `MeshoptDecoder`;三個載入點(ModelViewer / EditorViewport / EmbedScene)全部改走它——壓縮與未壓縮 GLB 都吃。 |
| `web/src/components/useHdri.ts` | 快取改以 URL 為 key;新增 `HDRI_URL_EMBED`(512×256 降檔版)。 |
| `web/src/components/EmbedScene.vue` | HDRI 解析度依 scene.json 決定:只做 IBL 用 512 版(PMREM 立方貼圖僅 ~256px,理論無感);背景 `type=environment`(HDRI 上畫面)才載 1k。scene fetch 先行、HDRI 與 GLB 並行載入。 |
| `web/public/hdri/studio_small_08_512.hdr` | 新增(380KB;OpenCV INTER_AREA 從 1k 縮)。1k 版保留給 editor / 一致性頁(亮度校正基準不動)。 |

### 實測結果

- **fishbowl.glb 1.54MB → 704KB(−54%)**:mesh 714KB 走 meshopt+quantization、三張 2048² JPEG 轉 WebP;`gltf-transform inspect` 確認材質名 `tripo_material_…` 保留(scene.json override 的 key)
- 其餘 demo GLB(本地檔):coral 2.11→1.08MB、model 1.66→0.77MB、**radio_baked 4.42→0.50MB(−89%)**、trellis_radio 6.9→1.57MB
- **A/B 像素比對**(headless Chrome 同角度截圖):壓縮前後 mean abs diff 1.03/255、非白面積完全一致 33.3%(差異 = WebP 有損 + 玻璃折射放大的量化雜訊,目視無感);HDRI 1k vs 512 mean abs diff **0.104**(0.27% 像素 >10)
- **Embed 一組 payload:GLB 704KB + hdr 389KB + scene 1KB + poster 233KB ≈ 1.33MB**(原 3.3MB,−60%)
- 單一檢視(壓縮後 model.glb)渲染正常、無 console 錯誤;`npm run build` 通過

### 待辦 / 下一步

- [ ] 貼圖 KTX2/Basis(GPU 記憶體 22MB/張 → 可再降;選配)
- [ ] pipeline 尾端自動跑 optimize(現為手動 `npm run optimize:glb -- in.glb out.glb`;4A worker 待辦)

---

## 2026-08-26 — 🎯 Embed 主產出落地:嵌入頁 + scene.json 載入 + poster 獨立產出

> 依目標校正(主產出 = 嵌入網站的互動模型)實作 P0/P1 缺口;iframe 實嵌驗證通過。

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `web/src/editor/sceneRig.ts` | 新增。scene.json → three.js 的**共用套用模組**(editor Viewport 與 Embed 頁共用):`spherical` / `focalToFov` / `normalizeModel` / `lightRigs` / `cameraRig` / `createMaterialRig`(含 Standard→Physical 升級的 defines 修補)。 |
| `web/src/components/EmbedViewer.vue` + `EmbedScene.vue` | 新增。**嵌入頁**:`?mode=embed&model=<GLB>&scene=<scene.json>&poster=<webp>`——無 app chrome、poster 當載入佔位(載完淡出)、fetch scene.json 經 `mergeScene` 補預設後以 sceneRig 套用;無 scene 參數時用 pipeline 預設攝影棚。 |
| `web/src/components/EditorViewport.vue` | 重構:改用 sceneRig(行為不變,transmission 滑桿煙霧測試通過)。 |
| `web/src/components/EditorView.vue` | 頂欄:「scene.json ↑」匯入(檔案 → mergeScene → 套進 store,可 undo);**Embed 按鈕啟用**(複製 iframe 嵌入碼,URL 佔位待使用者替換託管位址);Render → 「Render poster」;clipboard 失敗 fallback console。 |
| `web/src/editor/sceneStore.ts` | 抽出 `mergeScene()`(外部 scene.json 解析 + 巢狀補預設),load / 匯入 / Embed 共用。 |
| `scripts/render_model.py` + `scripts/blender/render.py` | **poster 獨立產出**:`--scene-json` 時輸出 `poster.webp`(不出縮圖)、metadata 寫 `poster_render`——官方 `preview.webp` / `render` 統計不再被 scene 渲染覆蓋。 |
| `web/public/scenes/fishbowl-glass.scene.json`、`renders/fishbowl-poster.webp` | 新增。embed demo 素材(玻璃 fishbowl 場景 + 對應 poster)。 |

### 實測結果(headless Chrome)

- **嵌入頁直開**:fishbowl 玻璃(scene.json transmission)正確渲染、白底無 chrome、poster 先顯示後淡出——poster 與 live 場景幾乎無縫(同一份 scene.json 參數)
- **iframe 實嵌**:host 頁面 `<iframe src="…?mode=embed&…">` 內正常互動渲染——**「嵌進任意網站」的最短驗證通過**,無 console 錯誤
- poster 流程:`--scene-json` 渲染 8.0s(scene 的 32 samples/600px 生效)→ `poster.webp`;`preview.webp` 時間戳未動、metadata `render` 與 `poster_render` 分開
- 編輯器重構後煙霧測試:transmission 即時生效 ✅、Embed 按鈕 toast ✅、`npm run build` 通過

### 待辦 / 下一步

- [ ] 實際部署一次靜態託管(如 GitHub Pages / Cloudflare Pages)驗證跨網域嵌入
- [x] embed 重量瘦身:GLB meshopt + WebP、hdr 512 降檔(見上一條;Draco 改採 meshopt)
- [ ] 4A:public URL + 嵌入碼產生器(把手動放檔案自動化)

---

## 2026-08-26 — Phase 4B 配套:Undo/Redo + HDRI 旋轉 + web/public 資產版控

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `web/src/editor/sceneStore.ts` | (1) **Undo/Redo**:JSON 快照堆疊(cap 50),350ms debounce 把連續拖曳合成一步;undo 先 flush 未入棧的編輯,套用快照時以 `applying` 旗標避免重複入棧。原規劃 command pattern,改用快照——scene.json < 2KB,快照更簡單且天然涵蓋所有欄位。(2) **schema additive 欄位 `environment.rotation`**(HDRI 繞垂直軸,度);localStorage 載入改巢狀補預設,舊資料不缺新欄位。 |
| `web/src/components/EditorView.vue` | 頂欄 ↶/↷ 按鈕(依 history 狀態 disable)+ ⌘/Ctrl+Z、⇧⌘Z 快捷鍵;Light tab 加「HDRI 旋轉」滑桿(0–360°)。 |
| `web/src/components/SceneEnvironment.vue` | 新增 `rotation` prop → `scene.environmentRotation` / `backgroundRotation`(three r162+)。 |
| `scripts/blender/setup_lighting.py` | `build_lighting()` 新增 `hdri_rotation`(只轉 HDRI、不動燈,與評估用的 `azimuth_offset` 疊加於同一 Mapping 節點)。 |
| `scripts/blender/render.py` | `--scene-json` 讀 `environment.rotation` 傳給 build_lighting。 |
| `.gitignore` / `web/README.md` / `web/public/` | 資產版控定案:`hdri/`(IBL 必需,1.5MB)與 `renders/`(一致性頁)**進版控**;`models/` 加入 gitignore(大、可由 pipeline 重生),README 改寫為專案說明含複製指引。 |

**已知未定**:HDRI 旋轉在 three(`environmentRotation.y`)與 Blender(Mapping 節點 Z)兩端的正負號一致性待目視校驗——studio HDRI 各向性低、影響小,已在程式註解標記。

### 註釋:.hdr 檔是什麼、資產版控為什麼這樣分

- **`.hdr` = HDRI 環境貼圖**(High Dynamic Range Image):360° 全景圖,像素存「光的實際強度」而非 0~255 顏色——亮部(燈箱、窗)值可遠大於 1.0,因此可直接**當光源**用,不只是背景圖。本專案用 Poly Haven 的 `studio_small_08_1k.hdr`(CC0,1k)。
- **同一張檔案在兩端當同一組環境光**,這是 Step 3-5 色彩一致性的關鍵:
  - Blender 端:`setup_lighting.py` 掛 World 節點(強度 0.4),檔案在 `assets/`;
  - Web 端:`useHdri.ts` 載入 `web/public/hdri/` 的拷貝,掛 `scene.environment` 做 IBL——所有 PBR 材質自動獲得反射與環境照明。
- **為什麼非要它**:金屬 / 光滑表面的質感來自「反射環境」——radio 旋鈕、fishbowl 玻璃反射的都是這張 HDRI 裡的攝影棚燈箱;只有方向光時金屬會呈現死板塑膠感。編輯器 Light tab 的「HDRI 強度 / 旋轉」調的就是這張圖。少了檔案時 viewer 走降級路徑(純方向光,不會全黑,見 `42db7af`)。
- **版控取捨**:`hdri/`(1.5MB、功能必需、不會變)與 `renders/`(~370KB、一致性頁基準圖)進版控——clone 下來 viewer 即可用;`models/` 的 GLB 每顆 1.5~15MB、可由 pipeline 隨時重生,進 gitignore、README 留複製指引。`models/` 從未被 commit 過(`git log --all` 驗證),不存在誤推歷史。

### 實測結果(headless Chrome)

- 清 localStorage → Light tab 把 HDRI 旋轉拉到 180° → **Ctrl+Z 回 0 → ⇧Ctrl+Z 回 180°**,↶/↷ 按鈕 disable 狀態正確,無 page error
- 旋轉 180° 時模型反射位置可見改變(environmentRotation 生效)
- `npm run build`(vue-tsc)通過

### 待辦 / 下一步

- [ ] export_glb 端也吃 materials_override(gltf-transform,4B 後端)
- [ ] 背景 type=environment 時 Blender 端關 film_transparent
- [ ] 4A:上傳 → 佇列 → worker 的後端(pipeline stages 已 ready)

---

## 2026-08-26 — Phase 4B:scene.json → Blender 渲染閉環(commit `8eb3dff`)

> scene-schema 資料流的下半段:編輯器調的燈光 / 相機 / 材質(含 transmission 玻璃),
> 用同一份 scene.json 直接餵給 Cycles 渲染——即未來 Render API 的參數面,先以 CLI 打通。

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/blender/apply_scene.py` | 新增。`load_scene()`(驗 version)+ `apply_material_overrides()`:transmission→Principled `Transmission Weight`、ior→`IOR`、emissive→`Emission Color`+Strength;base_color_tint / roughness / metallic 依 glTF「factor × 貼圖」語意——輸入沒接貼圖直接設值,有接貼圖插 Multiply 節點(Math / Mix.RGBA)。sRGB hex → linear 轉換。統計(applied / missing)寫 metadata。 |
| `scripts/blender/render.py` | 新增 `--scene-json`:camera(azimuth/elevation/focal_mm/padding)、render(samples/resolution)、environment.intensity、lights[]、materials_override 全部由 scene.json 提供並優先於對應 CLI 參數。 |
| `scripts/blender/setup_lighting.py` | `build_lighting()` 新增 `lights` 參數(scene.json 的 lights[],id/azimuth/elevation/power),預設值抽成 `DEFAULT_LIGHTS`;size 依角色固定(key 2.0 / fill 3.0 / rim 2.0)。 |
| `scripts/render_model.py` | 傳遞 `--scene-json`;背景合成色改讀 scene.environment.background(type=color 用其色值,其餘維持白底)。 |
| `web/src/components/EditorView.vue` | Render 按鈕的 CLI 指令改為 `--scene-json` 形式。 |

**踩坑備註**:Blender `ShaderNodeMix` 的 A/B/Result 依 data_type 有多組同名 socket,`inputs["A"]` 會拿到 float 那組——RGBA 必須用固定索引(inputs[6]/[7]、outputs[2])。

### 實測結果(fishbowl,job `940b1dd831ac`)

- scene.json:`materials_override` 對 Tripo 材質設 transmission 1.0 / ior 1.45 / roughness 0.05
- `uv run scripts/render_model.py output/940b1dd831ac --scene-json .../scene.json` → **48.8s(Metal)**,metadata 記錄 `materials_overridden` 與 scene_json 路徑
- **Phase 2 記錄的「Tripo 玻璃烘成不透明」問題,首次渲出真玻璃**:可透視、折射、頂部光澤,shadow catcher 陰影正常——瀏覽器(three.js MeshPhysicalMaterial)與 Cycles 兩端同一份 scene.json 語意一致
- 玻璃版另存 `preview_scene.webp`,官方 `preview.webp` 保持原樣(scene override 渲染不覆蓋 pipeline 產物)

### 待辦 / 下一步

- [ ] editor「下載 scene.json」→ 放進 job 目錄的流程說明(或 4A 後端直接收 scene overrides)
- [ ] export_glb 端也吃 materials_override(gltf-transform 或 bpy 匯出前套用),Embed 用
- [ ] 背景 type=environment 時 Blender 端關 film_transparent、渲 HDRI 背景

---

## 2026-08-26 — Phase 4B 前置:Scene Editor 前端 MVP(三欄編輯器,commit `d420b85`)

> 依 4B UI mockup(三欄 Figma 式)先做**不依賴後端**的前端層;Render API / DB / Embed 屬 Phase 4 後續。

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `web/src/editor/sceneStore.ts` | 新增。Scene JSON v0(docs/scene-schema.md)的單一真相來源:模組層 reactive(MVP 先不引 Pinia)、debounce 300ms 寫 localStorage、`downloadSceneJson()` / `resetScene()`;`editorUi` 另放選取 / tab / 材質名等不進 scene.json 的 UI 狀態。 |
| `web/src/components/EditorView.vue` | 新增。三欄版面:頂欄(專案名 + Render / Export GLB / scene.json / Embed)、左欄 Scene 樹(model + 三燈 + HDRI + Camera,選取即切 Inspector tab)、中央 Viewport(狀態列 + Front/Side/Iso preset + Wireframe)、右欄 Inspector 四 tab(Material / Light / Camera / BG),滑桿全數對映 Scene Schema 欄位。 |
| `web/src/components/EditorViewport.vue` | 新增。編輯器 Viewport:燈光(瓦數 × 校正係數 8.5/400 換算 three.js 強度)、相機(az/el/focal/padding → 位置與 FOV)、背景(color / transparent / environment)、materials_override 全部 watch store 即幀生效;transmission/ior 以 lazy 升級 MeshPhysicalMaterial 實現(GLB 不動、可還原);`exportGlb()` 用 three GLTFExporter 在 client 端把 override 合成進 GLB 下載。 |
| `web/src/modelList.ts` | 新增。App 與 editor 共用的模型清單。 |
| `web/src/App.vue` | 加入「編輯器」模式(`?mode=editor`)。 |

### 實測結果(headless Chrome,含 ANGLE Metal 真 GPU)

- 三欄版面與 mockup 一致;radio 預設場景正常;fishbowl 切換後把 **Transmission 拉到 1.0 → 玻璃感即時生效**(4B 的 fishbowl 玻璃解法,scene.json `materials_override` 記錄、GLB 不動)
- scene.json localStorage 持久化與「已儲存」指示正常;Export GLB 實測輸出 `model_edited.glb`
- **修掉兩個實作坑**:
  1. scoped CSS 選不到子元件的 TresCanvas 容器 → canvas 高度暴走 15660px,以自己 scope 的 `.canvas-host` wrapper 解
  2. `MeshStandardMaterial.prototype.copy` 到 MeshPhysicalMaterial 時會把 `defines` 蓋掉(丟失 `PHYSICAL`)→ fragment shader 編譯失敗、mesh 消失(真 GPU 同樣重現),copy 後補回 defines 解
- Render 按鈕 MVP 行為:複製等價 CLI 指令(camera/render 參數面);Embed 停用待 4A public URL

### 待辦 / 下一步

- [ ] Undo / Redo(command pattern,4B 配套)
- [ ] HDRI 旋轉滑桿(Blender 端 `azimuth_offset` 已支援,editor 尚未曝露)
- [ ] Export 改走 gltf-transform(Draco 壓縮,4B 後端)
- [ ] scene.json → Render API(4A/4B 後端)

---

## 2026-08-26 — 修復:HDRI 載入失敗會讓 viewer 永遠卡在「載入模型中」(commit `42db7af`)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `web/src/components/useHdri.ts` | 新增。HDRI 的 URL / 強度常數與載入邏輯抽出:(1) **模組層快取 promise**——比較模式雙 pane 與模型切換共用同一張,1.5MB 的 `.hdr` 整個 app 生命週期只抓一次;(2) 載入失敗 `.catch()` 回傳 `null` 並留 console 警告。 |
| `web/src/components/ModelViewer.vue` | 移除內嵌 RGBELoader,改 import `useHdri`;`<SceneEnvironment>` 加 `v-if="hdriTexture"`——拿不到 HDRI 時略過 IBL、退回純方向光(不會全黑)。 |

**動機**:viewer 以 `Promise.all` 同時載入模型與 HDRI,HDRI 一旦載入失敗(檔案不在、網路錯誤),async setup reject → Suspense **永遠停在「載入模型中…」**且所有模型都開不了。failure mode 從「整頁阻斷」改為「可感知的降級」。

### 實測結果

- `npm run build`(vue-tsc)通過;headless Chrome 實測三模式正常、console 無錯誤
- 排查起點是使用者回報「都是模型載入中」——實際成因是舊分頁的 dev server 連線已斷(硬重新整理即解),但排查過程暴露了這個真實隱患,一併修掉

---

## 2026-08-26 — Phase 3 Step 3-5:Web 端一致性驗證 + 修正 render.py 取景 FOV bug(commit `de569ed`)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `web/src/components/SceneEnvironment.vue` | 新增。把與 Blender 同一張 HDRI(`web/public/hdri/studio_small_08_1k.hdr`)掛上 `scene.environment`(three.js 對等距長方貼圖自動轉 PMREM),`environmentIntensity 0.4` 對映 Blender World Strength;可選 `background` 純色(一致性頁白底)。 |
| `web/src/components/ModelViewer.vue` | (1) 全模式:HDRI IBL 取代 AmbientLight、TresCanvas 設 `ACESFilmicToneMapping`;(2) 新增 `studio` prop(攝影棚模式):白底、相機 30°/18°/FOV 39.6°(=50mm)/留白 1.4、三點打光角度同 `setup_lighting.py`(強度比例 = Blender 瓦數 400:130:250,整體係數定量校正後為 8.5/2.7/5.2)。`spherical()` 為 Blender Z-up → three.js Y-up 的座標轉換等價式。 |
| `web/src/components/ConsistencyViewer.vue` | 新增。一致性驗證頁:左 `preview.webp`(複製到 `web/public/renders/`)、右攝影棚模式 live viewer,三類素材下拉切換、重置視角按鈕。 |
| `web/src/App.vue` | 加入「一致性驗證」模式;支援 `?mode=compare / consistency` 深連結。 |
| `scripts/blender/render.py` | 🐛 解析度移到 `frame_camera()` **之前**設定(取景需要正確的輸出長寬比)。 |
| `scripts/blender/setup_camera.py` | 🐛 **取景 FOV bug 修正**:原本 `fov = min(data.angle_x, data.angle_y)`——但 `angle_y` 由 sensor 實體尺寸(36×24mm)計算、與渲染長寬比無關,方形輸出時誤用 27° 而非實際的 39.6°,等效留白 ~2.1 而非規劃的 1.4(商品圖物件偏小、像素利用率低)。改為 `data.angle` 配合輸出長寬比換算窄軸 FOV(橫直向通用)。 |
| 文件 | 新增 `docs/render-consistency.md`:viewer ↔ Blender 參數對映表、座標轉換公式、已知差異(AgX vs ACES、Area vs Directional、接觸陰影)、校正旋鈕清單。 |

### 實測結果

- `npm run build`(vue-tsc)通過;headless Chrome(puppeteer-core)實截三模式,console 無錯誤
- **一致性頁抓到取景 bug**:並排立刻看出 live viewer(照規格 1.4 留白)物件比 preview.webp 大——追查發現是 Blender 端 FOV 算錯,viewer 反而是對的。修正後三個 job 重渲 preview/thumbnail(radio 物件寬度佔比 0.598 → **0.805**,商品圖像素利用率明顯提升;重渲 ~44s/張,Metal)
- **定量亮度校正**:以並排截圖量測物件區域平均亮度,燈光係數迭代三輪(2.0/0.65/1.25 → 8.5/2.7/5.2),radio 兩端 mean **177.7 vs 178.3** 一致(median 173 vs 185,右側中間調略暗屬 Directional vs Area 光源差)
- radio / fishbowl 目視:basecolor 色相、明度、大小、角度四項對齊;AgX vs ACES 高光滾降差異可見、可接受
- 殘餘差異(已記錄於 render-consistency.md):接觸陰影(viewer 無 shadow catcher)、光源軟硬

---

## 2026-08-26 — Phase 3 Step 3-4:高模 → 低模貼圖烘焙(bake_textures.py)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/blender/bake_textures.py` | 新增。同場景匯入高模(帶 provider 貼圖)與 Web 低模 → 低模重新 unwrap(復用 Step 3-3 的 `reunwrap`)→ Cycles selected-to-active 烘焙 **normal / AO / diffuse(pass_filter=COLOR,不含光影)/ roughness** 四張(1024px,32 samples,cage_extrusion 0.02)→ 貼圖接回 Principled → 匯出 `model_baked.glb`。貼圖另存 `textures/baked_*.png`,統計寫 metadata `bake` 欄位。Metal GPU(復用 render 的 enable_gpu)。 |
| `web/src/App.vue` | viewer 加入 `radio_baked.glb` 供 A/B 比較。 |

已知限制(記錄於腳本 docstring):

- **metallic 無原生 bake type**,先固定 0(之後需要時以 EMIT 技巧補)——金屬件在 baked 版會失去金屬感
- **AO 只存檔不接線**(glTF occlusion 佈線需特殊節點群組,Web 端效益低)

### 實測結果(vintage-radio)

- 四張全烤 + 匯出共 **7.7s**(Metal GPU;normal/AO/diffuse/roughness 各約 1~2s)
- 渲染比對:與 provider 貼圖版幾乎無差異——無接縫、無黑斑(cage 0.02 適當),頂部格柵 normal 細節保留
- `model_baked.glb` 4.4 MB vs 原 `model.glb` 1.6 MB(四張未壓縮 1024 PNG;之後可轉 JPEG/壓縮再省)
- 意義:**貼圖產線與 provider 解耦**——之後不論貼圖來自 delighting、AI 生成或手動修圖,都能烤回統一的低模 UV

### 待辦 / 下一步

- [ ] viewer 比較模式 A/B:`model.glb` vs `radio_baked.glb`
- [ ] baked 貼圖的壓縮策略(JPEG basecolor / 較低解析度 roughness)
- [ ] Step 3-5:Web 端材質與色彩一致性驗證

---

## 2026-08-26 — Phase 3 Step 3-3:UV 處理自動化(品質檢測 + 重新 unwrap)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/blender/cleanup_model.py` | (1) 新增 `uv_quality()`:以 bmesh 計算每面「UV 面積 / 3D 面積」的加權變異係數(texel density 均勻度)與 UV 總覆蓋率,decimate 後永遠量測、寫入 metadata `cleanup.uv`,`density_cv > 1.0` 標記警告;(2) 新增 `--reunwrap` 旗標:decimate 後 `smart_project`(66°)+ `pack_islands` 重建乾淨 UV。 |

**設計決策**:文件建議 decimate 後直接重新 unwrap,但這會讓既有貼圖立刻失效(舊貼圖對不上新 UV),必須搭配 Step 3-4 的 bake 才成立。因此 `--reunwrap` 預設**關閉**——一般 pipeline 保留 decimate 自動維護的原 UV(貼圖照常可用),bake 流程才開啟。

### 實測結果(vintage-radio)

| 模式 | texel density CV(越低越均勻) | UV 覆蓋率 |
|---|---|---|
| 原 UV(decimate 保留) | 0.395 | 0.686 |
| `--reunwrap` 後 | **0.056** | 0.669 |

- 原 UV 品質尚可(未達警告門檻),貼圖直接沿用沒問題
- 重新 unwrap 後 texel density 幾乎完全均勻,驗證了給 bake 用的 UV 產線可行
- UV 覆蓋率 >1 可偵測重疊/複用(精確的重疊檢測成本高,以覆蓋率作 proxy)

### 待辦 / 下一步

- [ ] Step 3-4:`bake_textures.py`(高模 → 低模新 UV 的 normal / AO / diffuse bake)
- [ ] bake 後 A/B 比較(viewer 已有比較模式可用)

---

## 2026-08-26 — Phase 3 Step 3-2:AI 貼圖 PBR 品質評估(旋轉打光)

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/blender/setup_lighting.py` | `build_lighting()` 新增 `azimuth_offset`:整組光源(三盞 Area Light + HDRI,HDRI 經 Mapping 節點轉 Z 軸)一起旋轉。 |
| `scripts/blender/render.py` | 新增 `--light-rotation` 參數,傳給 build_lighting。 |
| `scripts/eval_textures.py` | 新增(venv 端)。固定相機、光照轉 0°/120°/240° 各渲一張(64 samples / 800px),輸出 `eval/light_<deg>.webp`。 |

### 實測結果(vintage-radio + fishbowl,共 6 張)

- **兩者的陰影與表面高光都正確隨光旋轉**——Tripo 的 ORM/normal 是真 PBR,不是畫上去的光影
- vintage-radio:金屬旋鈕、喇叭網高光跟著光走;basecolor 僅輕微斑駁明暗(近似做舊質感,可接受)
- fishbowl:球面即時鏡面反射正確,**但玻璃「窗」的白色反光條紋烤死在 basecolor**(三個角度完全不動),加上無 transmission,反光類是目前品質短板
- 結論寫入 `docs/evaluation.md` 附錄 A:第一版貼圖採 **Tripo API PBR 輸出**;反光/透明類 fallback → delighting 或 Blender bake(Step 3-4)+ 後製 transmission

### 待辦 / 下一步

- [ ] Step 3-3:UV 處理自動化(檢測拉伸/重疊/texel density)
- [ ] Step 3-4:Blender bake(高模 → 低模貼圖烘焙)

---

## 2026-08-26 — Phase 2 完整驗證(coral-mound)+ Phase 3 Step 3-1:標準化貼圖結構

### Phase 2 完整 pipeline 驗證(job `b0b8fdff66a5`)

以 `test-assets/organic/coral-mound/front.png` 跑**含 generate 的完整 pipeline**,一條指令全程無 GUI:

| 階段 | 數據 |
|---|---|
| generate(Tripo) | 107.5s、16.2 MB(502,558 tris),`source.png` 正確拷貝 ✅ |
| cleanup | 30,000 tris、2.1 MB,合併重複頂點 32,836(organic 類明顯偏多)、內部面 290 |
| material | 0 需修復 |
| render(Metal) | 40.4s,商品圖風格與前兩類一致 |
| **總計** | **155.1s**(圖片 → Web 模型 + 商品圖) |

三類測試素材(hard-surface / reflective / organic)全數通過,Phase 2 驗收清單達成,已加入 viewer(`coral{,_raw}.glb`)。

### Phase 3 Step 3-1:標準化 PBR 貼圖輸出結構

| 檔案 | 內容 |
|---|---|
| `scripts/blender/export_textures.py` | 新增。依貼圖節點連到 Principled 的輸入分類(Base Color→basecolor、Normal→normal、Metallic/Roughness→orm),從 GLB 存出 PNG 到 `textures/`。 |
| `scripts/extract_textures.py` | 新增(venv 端)。呼叫上者後以 Pillow 把 ORM 拆成 `ao/roughness/metallic.png`(glTF 慣例 R=AO、G=Roughness、B=Metallic),寫 metadata `textures` 欄位。 |
| `scripts/validate_textures.py` | 新增。檢查:必要貼圖齊全、解析度為 2 的次方、normal map 平均色接近 (128,128,255)。結果寫 metadata `textures.validation`。 |
| `scripts/pipeline.py` | material 與 render 之間插入 `textures` 階段(抽取 + 驗證,驗證失敗 fail fast)。 |

實測(vintage-radio 與 coral-mound):各抽出 5 檔標準結構(basecolor/normal/roughness/metallic/ao,2048×2048),驗證全數 OK,約 3s/job。

### 待辦 / 下一步

- [ ] Step 3-2:評估 AI texture 品質(轉動光照看高光是否「跟著光走」,已有攝影棚渲染可用)
- [ ] Step 3-3:UV 處理自動化

---

## 2026-08-25 — Phase 2 Step 2-4 / 2-5 / 2-6:程式化攝影棚渲染 + 單一指令 pipeline

### 程式碼更新

| 檔案 | 內容 |
|---|---|
| `scripts/blender/setup_lighting.py` | 新增。程式化三點打光(Key 75°/45° 400W、Fill −30°/20° 130W、Rim 200°/40° 250W,Area Light)+ HDRI 環境光(`assets/studio_small_08_1k.hdr`,強度 0.4;檔案不在時退均勻灰)。 |
| `scripts/blender/setup_camera.py` | 新增。自動取景:固定球座標(方位角 30°、仰角 18°、50mm),距離依 bounding box 與 FOV 計算(留白係數 1.4),保證完整入鏡。 |
| `scripts/blender/render.py` | 新增。Cycles 渲染:Metal GPU(失敗退 CPU)、128 samples + denoising、透明底片 + shadow catcher 地板(白底商品圖帶自然接觸陰影)、輸出帶 alpha 的 PNG,統計寫 metadata `render` 欄位。 |
| `scripts/render_model.py` | 新增(venv 端)。呼叫 render.py 後以 Pillow 合成白底,轉出 `preview.webp`(1600px)與 `thumbnail.webp`(400px),刪中間 PNG。 |
| `scripts/pipeline.py` | 新增。單一指令串接 generate → cleanup → material → render,各階段狀態/耗時寫 metadata `stages`,fail fast;`--skip-generate --job-dir` 可重跑後段省 API 額度。 |
| `scripts/generate_model.py` | 重構:抽出可 import 的 `generate()`;補拷貝 `source.<ext>` 進 job dir(規格要求,先前缺漏)。 |
| `assets/studio_small_08_1k.hdr` | 新增。Poly Haven studio HDRI(CC0)。 |
| `pyproject.toml` | 新增相依 `pillow`(WebP 轉檔)。 |

與文件規劃的差異:

- **不建手動 `studio.blend`**,改為全程式化場景(可版本控制、免 GUI);之後若要手調再補
- 縮圖不用 Eevee 另渲,直接由 Cycles 1600px 縮放(品質更好、省一次渲染)
- 不另寫 `export_glb.py`:cleanup / setup_material 已各自負責匯出,無「場景最終狀態」需要再匯的情境

### 實測結果

| Job | 渲染耗時(Metal GPU) | preview.webp | thumbnail.webp |
|---|---|---|---|
| vintage-radio(160724017c66) | 134.9s | 1600px | 400px |
| fishbowl(940b1dd831ac) | 40.9s | 79 KB | 8 KB |

- 兩張商品圖風格一致:白底、柔和接觸陰影、同構圖角度,肉眼確認達商品縮圖水準
- `pipeline.py --skip-generate` 全程 **48.4s**(cleanup 5.3 + material 1.4 + render 41.7),stages 正確記錄
- 完整輸出結構:`model_raw/high/model.glb + preview.webp + thumbnail.webp + metadata.json`(新 job 另有 `source.<ext>`)

### 待辦 / 下一步

- [ ] 用新圖片跑一次完整 pipeline(含 generate)驗證 source 拷貝與全流程
- [ ] coral-mound(organic)素材驗證
- [ ] Phase 2 驗收清單逐項確認 → 進 Phase 3(PBR 貼圖生成)

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
