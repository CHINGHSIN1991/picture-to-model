# Model Plan — Coral Reef Diorama

Reference:`references/final-concept.png`(唯一 reference,之後所有 render 都跟它比)。
目標:一個 low-poly、玩具感的珊瑚礁 diorama,潛水員懸浮其上,魚群環繞。
用途:Three.js 網站 hero,需支援旋轉、scroll 敘事、逐件爆開 / 重組(Step 11–13)。

## Major forms

| 代號 | 說明 | 在圖中的位置 |
|---|---|---|
| **A. Reef(主體)** | 鈷藍色多面體岩塊堆成的三層階梯狀小丘,整體剪影是寬底三角 / 錐形。中央最高峰,左右各一座矮丘,周圍散落小石塊 | 畫面下半 2/3 |
| **B. Sand** | 淺米色沙地平面,邊緣自然淡出 | 底部 |
| **C. Corals(配角,數量多)** | 五類:樹枝狀(紅 / 粉)、腦珊瑚(粉)、管狀叢(橘 / 紫 / 粉 / 藍)、盤狀 / 杯狀(橘)、小型叢(黃 / 紫) | 貼附在岩塊各層平台上 |
| **D. Kelp(配角,數量多)** | 綠色與黃綠色 S 型海草 | 岩塊間與邊緣 |
| **E. Diver(配角,單一)** | 深藍潛水衣、黃色氣瓶、藍色蛙鞋與面鏡的低模人形,手臂外張、懸浮姿態 | 礁石上方偏左 |
| **F. Fish(配角,數量多)** | 三種小魚:黃色圓身、橘白小丑魚、藍色小魚 | 環繞礁石中層高度 |
| ~~G. 氣泡、光束、焦散、懸浮微粒~~ | **不做 geometry**,Three.js 端用 sprite / shader / 背景處理 | — |

## Geometry vs. Material

| 元素 | 做法 | 理由 |
|---|---|---|
| 岩塊(Rock) | geometry:每塊是 ico-sphere / cube 隨機位移頂點後 decimate,**flat shading** | 多面體切面本身就是輪廓特色,flat shading 不加任何貼圖就有圖中的面狀感 |
| 沙地(Sand) | geometry:一片 subdivided 平面,微起伏 | 只是地板;細石、焦散不做 |
| 樹枝狀珊瑚(BranchA / BranchB) | 低模 geometry,**2 個 variant**,linked duplicates | 需可拆解、可 instancing;分枝用 skin modifier 或手動圓柱拼接後 apply |
| 腦珊瑚(Brain) | 低模 geometry:球體壓扁 + 輕微隨機位移 | 溝紋**不刻**;若 Step 04 覺得太平,加一張 512px normal map |
| 管狀珊瑚叢(TubeA / TubeB) | 低模 geometry:5–8 根圓柱(8 邊)一叢,**2 個 variant** | 數量多,instancing |
| 盤狀珊瑚(Plate) | 低模 geometry:倒圓錐 + 波浪邊緣,**1 個 variant** | 數量少但形狀獨特 |
| 小型珊瑚叢(Bush) | 低模 geometry:數顆小球堆疊,**1 個 variant** | 填補空隙用 |
| 海草(KelpA / KelpB) | 低模 geometry:帶狀 S 型 mesh,**2 個 variant**;擺動**不在 Blender 做** | 擺動在 Three.js 用 vertex shader 做,geometry 保持靜態 |
| 潛水員(Diver) | 低模 geometry,身體 / 氣瓶 / 面鏡 / 蛙鞋分開建但 parent 在一起 | 單一物件,但保留子物件方便 Step 12 做蛙鞋踢水 |
| 魚(FishA / FishB / FishC) | 低模 geometry,**3 個 variant**,各 ≤ 400 tri | instancing;游動路徑在 Three.js 做 |
| **所有顏色** | **單一 palette 貼圖**(64×64 PNG 色塊),每個 mesh 的 UV 全部指到對應色塊 | 整個場景 1 個 material → 1 個 shader、instancing 不受材質切分限制、GLB 最小。Roughness 統一 0.55,Metallic 0,無 emissive |
| 氣泡、光束、焦散、微粒 | **不做** | Three.js 端:sprite、god-ray shader、背景漸層 |

### 色票(palette 貼圖的色塊)

| 名稱 | 概略 hex | 用在 |
|---|---|---|
| rock_blue | #3A5BA0 | 所有岩塊 |
| rock_blue_dark | #2E4A86 | 岩塊陰影面(可選,flat shading 其實已足夠) |
| sand | #E8D9A8 | 沙地 |
| coral_red | #E8546B | BranchA、部分 Tube |
| coral_pink | #F27BA3 | Brain、BranchB |
| coral_orange | #F28C3B | Plate、部分 Tube |
| coral_purple | #7A5BD6 | 部分 Tube、Bush |
| coral_blue | #4A6CF0 | 部分 Tube |
| coral_yellow | #F2C94C | Bush、部分 Tube、FishA |
| kelp_green | #3FA65B | KelpA |
| kelp_yellow | #B8C83A | KelpB |
| diver_suit | #1F2E5C | 潛水衣 |
| diver_tank | #F2C94C | 氣瓶 |
| diver_fin | #3A7BF0 | 蛙鞋、面鏡框 |
| fish_orange | #F27B3B | FishB 身體 |
| fish_white | #F5F5F5 | FishB 條紋 |
| fish_blue | #3A5BF0 | FishC |

## Object hierarchy (for Three.js)

命名規則依 Step 13:`<Category>_<Variant>_<Index>`,index 三位數。
所有 index 物件都是 **linked duplicate**(共用 mesh data),Three.js 端才能轉 InstancedMesh。

```
Scene_Root
├─ Sand                           (1 mesh)
├─ Reef_Root                      (empty,原點在礁石底部中心)
│  ├─ Rock_Peak_001               中央主峰(最高,獨立 mesh,不 instancing)
│  ├─ Rock_Tier_001 … 006         三層平台的大岩塊(各自獨立 mesh,形狀不重複)
│  ├─ Rock_Boulder_A_001 … ~012   散落小石塊(2 variant,instancing)
│  ├─ Rock_Boulder_B_001 …
│  ├─ Coral_BranchA_001 … 002     大型紅樹枝珊瑚(左、右)
│  ├─ Coral_BranchB_001 … ~004    小型粉樹枝珊瑚
│  ├─ Coral_Brain_001             腦珊瑚(1 個)
│  ├─ Coral_TubeA_001 … ~006      管狀叢 variant A
│  ├─ Coral_TubeB_001 … ~006      管狀叢 variant B
│  ├─ Coral_Plate_001 … 004       盤狀珊瑚
│  ├─ Coral_Bush_001 … ~006       小型叢
│  ├─ Kelp_A_001 … ~008
│  └─ Kelp_B_001 … ~008
├─ Diver                          (empty,原點在胸口)
│  ├─ Diver_Body
│  ├─ Diver_Tank
│  ├─ Diver_Mask
│  ├─ Diver_Fin_L
│  └─ Diver_Fin_R
└─ Fish_Root                      (empty,原點同 Reef_Root)
   ├─ Fish_A_001 … ~006           黃色
   ├─ Fish_B_001 … ~005           小丑魚
   └─ Fish_C_001 … ~004           藍色
```

### Origin 規則(Step 13 爆開方向依賴這個)

| 類別 | origin 位置 |
|---|---|
| Rock_* | 底面中心 |
| Coral_* | 與岩塊的接觸點(底部中心) |
| Kelp_* | 根部 |
| Fish_* | 身體中心 |
| Diver | 胸口 |
| Reef_Root / Fish_Root | 礁石底部中心 = 世界原點 |

### 尺度(Blender 單位 = 公尺)

| 物件 | 尺寸 |
|---|---|
| 整座礁石(Reef_Root 含珊瑚) | 寬 3.0 m × 深 2.2 m × 高 1.6 m(主峰頂) |
| Sand | 直徑 4.5 m |
| Coral_BranchA | 高 ≈ 0.6 m |
| Coral_Brain | 直徑 ≈ 0.35 m |
| Kelp | 高 0.3–0.5 m |
| Diver | 身長 ≈ 0.6 m(約礁石高度 1/3,符合 reference 比例) |
| Fish | 長 0.08–0.12 m |
| Diver 懸浮位置 | 礁石主峰上方約 0.4 m,偏左 0.3 m |

## Animation plan

| 互動(Step) | 會動的物件 | 需要的結構 |
|---|---|---|
| **Pointer 跟隨(11)** | Reef_Root 整體輕微 tilt;Fish_* 離游標遠一點 | Reef_Root 為單一 empty;魚為獨立 instance |
| **Scroll 敘事(12)** | ① Rock_Tier 由下往上逐層堆起 ② Coral_* / Kelp_* 依序 scale-in 長出 ③ Diver 沿曲線從畫面頂下潛到定位 ④ Fish_* 進場環繞 | 岩塊分層獨立;珊瑚 origin 在接觸點(scale-in 才不會浮起);Diver 為 empty 可整體移動 |
| **爆開 / 重組(13)** | 全部 Coral_*、Kelp_*、Rock_Boulder_*、Fish_* 以 Reef_Root 為中心向外散開再回彈;Rock_Peak / Rock_Tier 留在原地當錨 | linked duplicates 共用 geometry → InstancedMesh;origin 正確;無 modifier 殘留 |
| **持續 idle** | Kelp 擺動(vertex shader)、Fish 游動(路徑)、Diver 上下浮動、氣泡 sprite 上升 | 不需 Blender 動畫;GLB 不帶 animation |
| **點擊單一珊瑚(13 可選)** | 被點的 instance 彈跳 + 短暫變亮 | raycaster instanceId |

Blender 端**不做任何 keyframe 動畫**,GLB 只帶靜態 mesh 與階層。

## Polygon budget

總目標:**< 100k triangles(場景總面數,含 instance)**;unique geometry **< 40k**。
比 roadmap 建議的 150k 保守,因為 low-poly 風格本來就不需要,省下的預算留給 mobile。

| 群組 | Variant 數 | 每 variant tri | Instance 數 | Unique tri | 場景 tri |
|---|---|---|---|---|---|
| Rock_Peak + Rock_Tier | 7(各不同) | ~1,500 | 7 | 10,500 | 10,500 |
| Rock_Boulder | 2 | ~200 | ~12 | 400 | 2,400 |
| Sand | 1 | ~800 | 1 | 800 | 800 |
| Coral_BranchA | 1 | ~3,000 | 2 | 3,000 | 6,000 |
| Coral_BranchB | 1 | ~1,500 | ~4 | 1,500 | 6,000 |
| Coral_Brain | 1 | ~2,000 | 1 | 2,000 | 2,000 |
| Coral_TubeA / B | 2 | ~600 | ~12 | 1,200 | 7,200 |
| Coral_Plate | 1 | ~800 | 4 | 800 | 3,200 |
| Coral_Bush | 1 | ~500 | ~6 | 500 | 3,000 |
| Kelp_A / B | 2 | ~200 | ~16 | 400 | 3,200 |
| Diver(含子物件) | 1 | ~4,000 | 1 | 4,000 | 4,000 |
| Fish_A / B / C | 3 | ~350 | ~15 | 1,050 | 5,250 |
| **合計** | | | | **≈ 26k** | **≈ 54k** |

其他預算(對應 Step 06):

| 項目 | 目標 |
|---|---|
| GLB 大小 | < 1.5 MB(無 texture 除了 64×64 palette) |
| Material | 1(palette) |
| Texture | 1(palette PNG 64×64);Step 04 若加 Brain normal map 則 2 |
| Draw calls(instancing 後) | < 25 |

## Graybox 階段(Step 03)要做到的範圍

- 只建 Rock_Peak、Rock_Tier、Sand、Diver(一個 capsule 代替)、2 顆 Coral_BranchA 的概略體積、Coral_Brain 球體;
  管狀叢、海草、魚**先用簡單 primitive 佔位**(圓柱、平面、橢球),只為了確認分布與比例。
- 命名與階層已依本文件建立,原點位置正確。
- 無材質、無 subdivision、無 palette;用統一灰色 + 三點光 render 六個角度。
- 腳本 `blender/scripts/01_graybox.py`,參數(礁石尺寸、各類數量、random seed)集中在檔頭。
