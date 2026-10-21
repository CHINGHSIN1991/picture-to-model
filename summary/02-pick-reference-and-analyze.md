# Step 02 總結 — 選定 reference 與建模分析

對應 roadmap:[roadmap/02-pick-reference-and-analyze.md](../roadmap/02-pick-reference-and-analyze.md)
狀態:完成(2026-10-09;2026-10-15 補上 PROJECT_SPEC 分離專案值;2026-10-16 / 10-19 依 Step 03、05 回寫兩段)

## 代表結果

這一步沒有新的圖,產出是兩份規格文件。代表資料是 MODEL_PLAN 的物件階層,以及 PROJECT_SPEC 把它對應到 Web 端的群組表。

物件階層(節錄自 [blender/MODEL_PLAN.md](../blender/MODEL_PLAN.md)):

```
Scene_Root
├─ Sand
├─ Reef_Root                      (empty,原點在礁石底部中心)
│  ├─ Rock_Peak_001               主山體,獨立 mesh
│  ├─ Rock_Tier_001 … 006         坡腳岩
│  ├─ Rock_Boulder_A/B_001 …      散石,2 variant,instancing
│  ├─ Coral_BranchA_001 … 002     大型紅樹枝珊瑚
│  ├─ Coral_TubeA_001 … ~008      管狀叢 variant A
│  ├─ Coral_Plate_001 … 004       盤狀珊瑚
│  └─ Kelp_A_001 … ~008
├─ Diver                          (empty,原點在胸口)
│  ├─ Diver_Body / Diver_Tank / Diver_Mask
│  └─ Diver_Fin_L / Diver_Fin_R
└─ Fish_Root
   └─ Fish_A/B/C_001 …            3 variant,instancing
```

零件群組表(節錄自 [PROJECT_SPEC.md](../PROJECT_SPEC.md)):

| group | match | instancing | origin | 逐件動畫 mode |
|---|---|---|---|---|
| `rocks` | `/^Rock_(Peak\|Tier)_/` | 否 | 底面中心 | `stack` |
| `boulders` | `/^Rock_Boulder_/` | 是 | 底面中心 | `explode`(未定) |
| `corals` | `/^Coral_/` | 是 | 接觸點 | `grow` |
| `kelp` | `/^Kelp_/` | 是 | 根部 | `grow` |
| `fish` | `/^Fish_/` | 是 | 身體中心 | `orbit` |
| `diver` | `/^Diver$/` | 否 | 胸口 | `path` |

這張表同時是 Blender 腳本的命名規範、Three.js 的 node 比對規則,以及 Step 13 動畫 config 的來源。

後續修正：上表保留 Step 02 當時的規劃。Step 09 確認 boulders 全程停在原位，取消其 explode；
Step 10 把魚群 pattern 改為 `^Fish_[A-C]_`，避免納入 `Fish_Root` 容器。
目前採用值見 [PROJECT_SPEC.md](../PROJECT_SPEC.md)，實作結果見 [Step 13](13-decomposable-model.md)。

## 這一步做了什麼

1. 把 `concept-01.png` **複製**為 `references/final-concept.png`,成為之後所有 render 比對的唯一標準。
2. 寫出 [blender/MODEL_PLAN.md](../blender/MODEL_PLAN.md):主要造型、geometry vs material、物件階層、origin 規則、尺度、動畫計畫、polygon 預算、graybox 範圍。
3. 把「只有這個專案才成立的值」從 roadmap 抽出來,集中到 [PROJECT_SPEC.md](../PROJECT_SPEC.md):asset 名稱、零件群組與 match pattern、每個群組的動畫 mode 與參數、idle 動畫、sections 佔位。roadmap 改用 `<asset>` 等佔位符。
4. 把 Step 13 的逐件動畫從「散開 / 重組」一種效果,改成 mode 目錄(explode / stack / grow / path / orbit / custom),由 spec 指定。

## 產出

| 檔案 | 內容 |
|---|---|
| `references/final-concept.png` | 唯一 reference |
| `blender/MODEL_PLAN.md` | 建模分析全文 |
| `PROJECT_SPEC.md` | 專案值:群組、match、instancing、origin、動畫 mode 與參數 |
| roadmap 多個檔案 | 把專案值改成佔位符(commit `54af139`) |

## 技術說明

### 物件階層與命名

```
Scene_Root
├─ Sand
├─ Reef_Root                 (empty,原點 = 礁石底部中心 = 世界原點)
│  ├─ Rock_Peak_001          主山體,獨立 mesh
│  ├─ Rock_Tier_001…006      坡腳岩,各自獨立 mesh
│  ├─ Rock_Boulder_A/B_*     散石,2 variant,linked duplicate
│  ├─ Coral_<Variant>_*      7 類珊瑚,linked duplicate
│  └─ Kelp_A/B_*             海草,linked duplicate
├─ Diver                     (empty,原點在胸口)
│  └─ Diver_Body / Tank / Mask / Fin_L / Fin_R
└─ Fish_Root
   └─ Fish_A/B/C_*           3 variant,linked duplicate
```

命名規則 `<Category>_<Variant>_<Index>` 直接對應 PROJECT_SPEC 的 regex(例如 `/^Coral_/`),Three.js 端用名稱分群,不靠額外 metadata。

### Origin 規則與動畫 mode 的耦合

| 群組 | mode | origin | 原因 |
|---|---|---|---|
| rocks | `stack` | 底面中心 | 由下往上堆,縮放 / 位移從底部算 |
| corals、kelp | `grow` | 接觸點 / 根部 | 長出時從根部縮放,不會浮起 |
| diver | `path` | 胸口 | 沿曲線移動時以身體中心定位 |
| fish | `orbit` | 身體中心 | 環繞時旋轉自身 |

這張表是 Step 03 之後所有腳本 `new_object(..., location=...)` 參數的依據。

### 材質策略

所有顏色集中在一張 64×64 色票 PNG,每個 mesh 的 UV 指到對應色塊。好處:

- 整個場景只有 1 個 material → 1 個 shader,InstancedMesh 不受材質切分限制。
- GLB 內只帶一張極小貼圖,預算 < 1.5 MB。
- 換色只改 PNG 或色票表,geometry 不動。

### Polygon 預算

| 項目 | 計畫值 | roadmap 建議 |
|---|---|---|
| 場景總面數(含 instance) | < 100k | < 150k |
| unique geometry | < 40k | — |
| 各群組 | 計畫合計 ≈ 54k 場景 / ≈ 26k unique | — |

刻意比 roadmap 保守,留預算給 mobile。

## Takeaway

- **「通用流程」與「專案值」分開放,是這個 repo 能變成平台的前提**。換一個主題只改 `PROJECT_SPEC.md`、`MODEL_PLAN.md`、`SECTIONS.md`,roadmap 一個字不動。
- **動畫方式是資料不是程式**。把 explode 改成 mode 目錄後,Step 13 的 `PartAnimator` 可以不含任何特定效果;spec 說 `grow` 就 grow。
- **origin 規則要在分析階段定死**,因為它同時決定建模腳本的 mesh 原點與 Web 端的動畫行為。事後改 origin 等於重建 mesh。
- 單一色票材質是整個專案最大的簡化決策:它讓 Step 04 的「材質」工作縮成「每個面指定一個 material_index」。
- MODEL_PLAN 不是一次寫完的文件:Step 03 的單峰需求、Step 05 的接合修正都回寫進來,它是目前模型的「規格書」,不只是分析紀錄。
