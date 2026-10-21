# PROJECT_SPEC — 本專案的專案值

`roadmap/` 是通用流程,裡面不該出現「只有這個專案才成立」的值。
所有專案值集中在這份文件(以及它指到的 `blender/MODEL_PLAN.md`、`mockups/SECTIONS.md`);
換一個專案只改這三份,roadmap 不動。

roadmap 文件中的 `<asset>` 等佔位符一律查這裡。

## 基本

| key | 值 | 用在 |
|---|---|---|
| `<asset>` | `reef` | `export/reef.glb`、`web/public/models/reef.glb` |
| 主題 | 潛水員 + 錐狀珊瑚礁,low-poly 玩具感 | Step 01 prompt |
| reference | `references/final-concept.png` | Step 02 起所有比對 |
| model plan | [blender/MODEL_PLAN.md](blender/MODEL_PLAN.md) | Step 02–06 |
| sections | [mockups/SECTIONS.md](mockups/SECTIONS.md)(6 段,Step 09) | Step 10–12 |
| 網頁 stack | Vue 3 + Vite + TypeScript + Three.js + GSAP | Step 07–17 |

## 零件群組(part groups)

命名規則 `<Category>_<Variant>_<Index>`,詳細階層見 MODEL_PLAN。
`match` 是 Three.js 端比對 node 名稱的 pattern,也是 Step 13 `config/partAnimations.ts` 的來源。

| group | match | instancing | origin 規則 | 備註 |
|---|---|---|---|---|
| `rocks` | `/^Rock_(Peak\|Tier)_/` | 否(各自獨立 mesh) | 底面中心 | 主峰 + 三層平台 |
| `boulders` | `/^Rock_Boulder_/` | 是 | 底面中心 | 散落小石塊 |
| `corals` | `/^Coral_/` | 是 | 與岩塊的接觸點 | 五類珊瑚 |
| `kelp` | `/^Kelp_/` | 是 | 根部 | |
| `fish` | `/^Fish_[A-C]_/` | 是 | 身體中心 | `Fish_Root` 是容器 empty,不屬於 group(Step 10 修正) |
| `diver` | `/^Diver$/`(empty,含子物件) | 否 | 胸口 | 子物件 `Diver_Fin_L/R` 可獨立動 |

## 動畫方式

### Pointer(Step 11)

| 對象 | mode | 參數 |
|---|---|---|
| 整體(`Reef_Root`) | `tilt` | `maxRotationX 0.08`、`maxRotationY 0.15`、`damping 0.08`、`stiffness 1` |
| `fish` | `repel`(可選) | `radius 0.6`、`strength 0.3`:魚離游標遠一點 |

Step 11 已實作 `tilt` / `none`，設定在 `web/src/three/config/pointer.ts`。
`damping` 是 60 Hz 每幀補間比例，`stiffness` 是反應速度倍率；用時間校正的指數阻尼，無超越最大角度的回彈。
偏移加在 `Model_Root` 包裝節點上，讓整個 `Reef_Root` 隨 section 一起傾斜，保留 GLB 原始 transform。
視窗離開／失焦時平滑回正；減少動態效果與純觸控裝置停用。魚群 `repel` 尚未實作。

### 逐件動畫(Step 12 / 13)

mode 目錄與 `t`(departure:0 = rest,1 = 離開狀態)的定義見 [roadmap/13](roadmap/13-decomposable-model.md)。

| group | mode | 參數 | 敘事用途 |
|---|---|---|---|
| `rocks` | `stack` | `dropHeight 1.5`、`order height`、`stagger 0.1` | 由下往上逐層堆起(`t: 1 → 0`) |
| `corals` + `kelp` | `grow` | `order random`、`stagger 0.03`、`overshoot 0.15` | 依序長出(`t: 1 → 0`) |
| `diver` | `path` | `offsets [[-1.0, 3.0, 0.5], [-0.5, 1.2, 0.3], [0, 0, 0]]` | 從畫面頂沿曲線下潛到定位(`t: 1 → 0`) |
| `fish` | `orbit` | `center [0, 0.8, 0]`、`axis [0, 1, 0]`、`angle 2π` | 進場環繞(`t: 1 → 0`) |

哪個 section 用哪個 group 的哪個 `t`,寫在 `mockups/SECTIONS.md`(Step 09)。
`explode` mode 在 Step 09 確認沒有任何 section 需要,已移除;`boulders` 全程 `t = 0`,與沙地一起當錨。

Step 12–13 實作補充（`web/src/three/config/partAnimations.ts`）：

- `spring` 使用時間校正的指數阻尼：rocks 5、corals / kelp / fish 6、diver 4；每個零件分別追蹤進度。
- rocks 的底部原點皆在沙面，`order: height` 以零件 bounding box 上緣排序，確保低岩先到、主峰最後到。
- `stagger` 按進場進度排序；總延遲上限 0.8，避免 35 株珊瑚 × 0.03 讓動畫區間歸零。random order 以名稱固定 seed。
- rocks / diver / fish 設 `hideAtDeparture: true`：最後 15% 的離場進度縮小至不可見。尤其魚群轉完 2π 會回到原位，需此設定才能符合前幾段「尚未進場」的畫面。
- `PartAnimator` 額外提供 `explode` 供換 mode 驗證；正式 sections 沒有使用。Idle 與選配點擊回饋尚未實作。
- 重複件同 parent / geometry / material 且至少四件時合批；原 named node 留作不可見 transform proxy，instance 使用同一個 local matrix，保留原點與階層。

### Idle(時間驅動,不經 scroll,不經 PartAnimator)

| 對象 | 做法 |
|---|---|
| `kelp` | vertex shader 擺動 |
| `fish` | 游動路徑(CatmullRom),每隻相位不同 |
| `diver` | 上下浮動 ±0.03 m |
| 氣泡 | sprite 上升(Three.js 端生成,GLB 不帶) |

### 點擊單一零件(Step 13,可選)

| 對象 | 回饋 |
|---|---|
| `corals` instance | 彈跳 + 短暫變亮(`onBeforeCompile` per-instance uniform) |

## Sections(Step 09 產出後填)

網站是**圖轉 3D 平台的產品頁**,珊瑚礁是示範 asset。Step 09 選定 `mockups/homepage-01.png`(編輯排版),
共 **6 個 section**:Hero、上傳、建模、調光、互動、CTA;四個流程段各用一個零件 mode 演示(stack / grow / path / orbit)。
每段的模型位置、累計旋轉(0° → −360°,繞一圈)、縮放、相機仰角與零件 `t` 寫在 [mockups/SECTIONS.md](mockups/SECTIONS.md);
Step 10 的元件名稱、Step 12 的 `config/sections.ts` 都從那裡來。

Step 12 已接上六個 ScrollTrigger：每段以自己的 plain state 插值，區間不重疊；四個流程段各增加一個 viewport 的停留距離。
CSS sticky 保持文案就位，這段距離只播放 `partsOnEnter → parts`；段落間改變整體位置、角度、縮放、相機與珊瑚 emissive。
減少動態效果時移除停留距離，以最接近視窗中央的段落直接切換完整狀態。`?state=N` 保留固定預覽，不綁 scroll。
