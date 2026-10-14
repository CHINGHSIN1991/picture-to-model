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
| sections | `mockups/SECTIONS.md`(Step 09 產出後才有) | Step 10–12 |
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
| `fish` | `/^Fish_/` | 是 | 身體中心 | |
| `diver` | `/^Diver$/`(empty,含子物件) | 否 | 胸口 | 子物件 `Diver_Fin_L/R` 可獨立動 |

## 動畫方式

### Pointer(Step 11)

| 對象 | mode | 參數 |
|---|---|---|
| 整體(`Reef_Root`) | `tilt` | `maxRotationX 0.08`、`maxRotationY 0.15`、`damping 0.08` |
| `fish` | `repel`(可選) | `radius 0.6`、`strength 0.3`:魚離游標遠一點 |

### 逐件動畫(Step 12 / 13)

mode 目錄與 `t`(departure:0 = rest,1 = 離開狀態)的定義見 [roadmap/13](roadmap/13-decomposable-model.md)。

| group | mode | 參數 | 敘事用途 |
|---|---|---|---|
| `rocks` | `stack` | `dropHeight 1.5`、`order height`、`stagger 0.1` | 由下往上逐層堆起(`t: 1 → 0`) |
| `corals` + `kelp` | `grow` | `order random`、`stagger 0.03`、`overshoot 0.15` | 依序長出(`t: 1 → 0`) |
| `diver` | `path` | `offsets [[-1.0, 3.0, 0.5], [-0.5, 1.2, 0.3], [0, 0, 0]]` | 從畫面頂沿曲線下潛到定位(`t: 1 → 0`) |
| `fish` | `orbit` | `center [0, 0.8, 0]`、`axis [0, 1, 0]`、`angle 2π` | 進場環繞(`t: 1 → 0`) |
| `boulders` + `corals` + `kelp` + `fish` | `explode` | `distance 0.8`、`jitter 0.3`;`rocks` 不散開,留在原地當錨 | **未定**:只有在 `SECTIONS.md` 某個 section 真的需要「散開 / 重組」時才啟用,否則刪掉這列 |

哪個 section 用哪個 group 的哪個 `t`,寫在 `mockups/SECTIONS.md`(Step 09)。

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

section **數量不固定**,由 mockup 決定;每個 section 的 3D 狀態寫在 `mockups/SECTIONS.md`,
欄位含「零件狀態」(每個 group 的 `t`)。Step 10 的元件名稱、Step 12 的 `config/sections.ts` 都從那裡來。
