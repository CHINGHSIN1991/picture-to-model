# Step 04 細部建模完成 — 2026-10-16

## 交付

- `blender/scenes/02_detail.blend`：可編輯場景，封裝色票貼圖。
- `blender/scripts/02_detail.py`：從空場景重建的入口。
- `blender/scripts/detail_geometry.py`：可重現的零件、色票與表面處理函式。
- `blender/textures/reef_palette.png`：64×64 sRGB 色票。
- `blender/renders/final/`：六視角、總覽及三張潛水員近照。

指令：`blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/02_detail.py`。

## 造型與材質

保留核准灰模的唯一主峰與階層，峰高 1.65 m，最高珊瑚約 1.17 m。
岩面加入細分切面與局部起伏、坡腳倒角及沙色平台；分枝珊瑚以體素融合形成連續分枝，管狀珊瑚有厚度、內壁與深色內腔，盤珊瑚有波浪邊。
海草改為連續帶狀曲面；魚有尾鰭、背鰭、眼睛和小丑魚色帶。
潛水員的潛水衣經融合形成連續肢體，另有貼合背帶、面鏡、黃色氣瓶、彎曲呼吸管、獨立蛙鞋與加強肋。
角色為靜態玩具感造型，手部採簡化手套；不宣稱具有動畫變形或逐指控制。
所有可見網格共用一個 Principled BSDF，roughness 0.55、metallic 0；每個面透過 PaletteUV 取色，貼圖已 packed。

## 面數報告

| 群組 | 網格物件 | 場景 triangles | Unique triangles |
|---|---:|---:|---:|
| 沙地 | 1 | 768 | 768 |
| 主山體與坡腳岩 | 7 | 2,272 | 2,272 |
| 散石 | 12 | 2,544 | 424 |
| 珊瑚 | 35 | 32,388 | 7,098 |
| 海草 | 16 | 3,648 | 456 |
| 潛水員 | 5 | 5,340 | 5,180 |
| 魚群 | 15 | 2,460 | 492 |
| 合計 | 91 | 49,420 | 16,690 |

場景 <100,000、unique <40,000 的硬上限均通過。每種魚 164 triangles（上限 400）。
重複珊瑚、海草、魚和左右蛙鞋仍共用各自 mesh data。91 個網格、26 個 unique meshes。

## 已執行的驗證

- 最終來源在新的 Blender 5.2.0 LTS 程序從空場景成功建構並輸出所有影像。
- 另開獨立程序載入 `.blend`，asset inspector hard gate 通過，issues 為空。
- 全部網格具材質與 UV；無無效頂點、退化面、零長度邊、孤立頂點或 wire edges。
- 192 條開放／非流形邊全部屬於沙地平面外圈；其他零件為閉合表面。
- 名稱與父子階層和核准灰模完全一致；主峰最高頂點唯一、配角低於峰頂。
- 已開啟最終 hero、六視角總覽和潛水員前／側／背近照，檢查輪廓、材質、肢體連續性、裝備與蛙鞋接合。
- 近照檢出的背帶間隙、呼吸管銳角已修回 source 並重建。
- 重複物件的旋轉／縮放及 Diver 的整體尺度是刻意保留的 placement transforms，並非漏套用 modifier。

## Render

Eevee、1024×768、64 samples、兩個 CPU threads、三盞 area softbox、AgX Medium High Contrast。
最終一次整個來源建構與九張渲染約 5.5 秒（本機 Blender log）；未使用 Cycles denoising 或合成降噪。
`contact_sheet.png` 上排 hero / front / left，下排 right / back / top。
角色近照：`diver_front.png`、`diver_back.png`、`diver_side.png`。
此階段完成模型與 Blender 視覺檢查；正式 GLB 匯出、重新匯入與 Three.js 驗證屬後續 Step 06–07。

## 證據

`build_report.json` 為分組面數，`metrics.json` 為獨立 asset inspector 結果，`render_manifest.json` 為場景設定、封裝色票與階層核對。
`preview_metrics.json` 只代表第一版預覽的歷史量測；最終以 `metrics.json` 為準。
