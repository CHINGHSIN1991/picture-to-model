# Step 03 總結 — Graybox 灰模

對應 roadmap:[roadmap/03-graybox.md](../roadmap/03-graybox.md)
狀態:完成(第一版 2026-10-15,commit `e6c3428`;單峰重建 2026-10-16,commit `3072e43`)

## 這一步做了什麼

1. 依 MODEL_PLAN 的階層、命名、origin 規則,用 bmesh 從空場景建出全部零件的**簡單 primitive 佔位**:主山體、6 塊坡腳岩、12 顆散石、7 類珊瑚、海草、潛水員(5 個子物件)、15 隻魚。
2. 以 Workbench 單色 + studio light + cavity + outline render 六視角,輸出 contact sheet 與 hierarchy 報告。
3. **第一版被退回**:側邊珊瑚與獨立高岩柱形成多個次峰,主峰不明顯。使用者要求清空重做為單峰。
4. 第二版把主山體改成一個**連續、閉合、只有一個頂點**的階梯狀山體;坡腳岩壓低到 0.25–0.55 m;大型珊瑚移到兩側低坡;重新 render 並做單峰檢查與前後對照。

## 產出

| 檔案 | 內容 |
|---|---|
| `blender/scripts/01_graybox.py` | 可重現腳本,參數集中檔頭 |
| `blender/scenes/01_graybox.blend` | 灰模場景 |
| `blender/renders/graybox/{hero,front,left,right,back,top}.png` | 六視角,1024×768 |
| `blender/renders/graybox/contact_sheet.png` | 上排 hero / front / left,下排 right / back / top |
| `blender/renders/graybox/before_after.png` | 同相機舊版(左)/ 新版(右) |
| `blender/renders/graybox/hierarchy.txt` | 物件樹、每物件面數與尺寸 |
| `blender/renders/graybox/metrics.json` | Blender Agent Studio asset inspector 結果 |
| `blender/renders/graybox/single_peak_checks.json` | 單峰檢查數值 |
| `blender/renders/graybox/iteration_review.json` | 第一版 → 第二版的判定紀錄 |
| `blender/renders/graybox/final_report.md` | 人類可讀總結 |

## 結果數字

| 項目 | 值 |
|---|---|
| mesh objects / unique meshes | 91 / 26 |
| 場景 triangles / unique triangles | 7,786 / 2,098 |
| 主峰高 | 1.65 m,summit vertex 恰好 1 個 |
| 最高珊瑚 | 1.158 m(低於峰頂 0.49 m) |
| 主山體 | 1 個 connected component、0 非流形邊、0 開放邊 |
| 全場景開放邊 | 48 條,全部是沙地圓盤外圈 |
| inspector | hard gate 通過;唯一 warning 是 3,900 面沒有材質(灰模預期) |

## 技術說明

### 主山體的建法(`build_mountain`)

- `MOUNTAIN_PROFILE` 是一串 `(高度比例, 半徑比例)`,高度相近而半徑差很多的兩個點形成一層「平台 + 懸崖」。
- 12 個方向角各有獨立的隨機不規則度,但每一圈的半徑強制 `min(r, 上一圈同方向半徑 − 0.04)`,保證**向上單調收窄**,不會出現懸空的裙邊。
- 相鄰兩圈用四邊形切成三角形,`(level + i) % 2` 交替對角線方向,避免規則網格感。
- 最上面一圈所有頂點連到唯一的 `summit` 頂點,所以「只有一個山峰」是結構上保證的,不是靠調參。
- 地形用獨立的 `random.Random(SEED + 101)`,改山體不會打亂珊瑚與魚的隨機擺放。

### 其他零件

- 岩石:icosphere 頂點徑向抖動 → 非等比縮放 → `bisect_plane` 切掉底部與頂部 → `holes_fill` 補面。切面天然就是 low-poly 感。
- 珊瑚 / 海草 / 魚:圓錐、圓柱、橢球、box 組合,每個 mesh 原點在底部中心或根部。
- 擺放:`ground_z(x, y)` 從上往下 ray_cast 到所有岩石與沙地,取最高命中點;只對岩石物件投射,不會被已放的珊瑚擋住。
- 重複零件用同一個 mesh data 建多個 object(linked duplicate),hierarchy 報告列出 unique meshes = 26。
- 潛水員:5 個子物件 parent 到 `Diver` empty,再依子物件 bound box 總長度把 empty 等比縮到 `DIVER_LENGTH`。

### Render

Workbench、`SINGLE` 灰色、studio light、cavity both、object outline、Standard view transform。目的是看輪廓與比例,不看材質。

### 迭代判定(`iteration_review.json`)

記錄 contract(critical / preserve / authorized_changes / excluded)、候選版本失敗的證據、原因、修法、最終 ledger 與 `decision: retain_repair`。前後對照圖用同一個相機與 Workbench 設定。

## Takeaway

- **灰模階段就要把「輪廓結構」做成程式保證,而不是調出來的**。第一版靠多個岩柱拼山,看起來總有次峰;第二版改成單一 summit vertex + 單調收窄,之後 Step 04、05 都沒再動山體。
- **參數集中在檔頭的好處在第二版兌現**:`MOUNTAIN_PROFILE`、`ROCKS`、`CORALS` 座標表改完即可重跑,不需要開 Blender。
- **分離隨機流**(地形 vs 擺放)讓「只改山」成為可能,否則每次改地形珊瑚全部換位置,比對無從比起。
- **被退回是正常流程**。灰模階段修比例成本極低,這次只花一天;同樣的問題若到 Step 04 才發現,要連材質與細節一起重做。
- 把「退回的原因、修法、證據」寫成 `iteration_review.json`,之後 Step 05 沿用同一格式,review 紀錄就能機器比對。
