# Web 端渲染一致性設定(Phase 3 Step 3-5)

> 回到主文件:[ROADMAP.md](../ROADMAP.md) / [phase-3-pbr.md](phase-3-pbr.md)
> 目的:記錄 Three.js viewer 的固定渲染配置,以及它與 Blender Cycles 端(`render.py`)的參數對映,讓「Blender 商品圖」與「網頁互動展示」目視一致。
> 驗證工具:viewer 的「一致性驗證」模式(`?mode=consistency`)——左 `preview.webp`、右 live viewer 同角度並排。

---

## Viewer 固定配置(所有模式共用)

| 項目 | 值 | 對映 Blender 端 |
|---|---|---|
| 環境光照(IBL) | `scene.environment` = `web/public/hdri/studio_small_08_1k.hdr`(RGBELoader,等距長方投影,three.js 內部自動轉 PMREM) | `setup_lighting.py` 的 `DEFAULT_HDRI`(同一檔案) |
| 環境強度 | `scene.environmentIntensity = 0.4` | World Background `Strength = 0.4` |
| Tone mapping | `renderer.toneMapping = ACESFilmicToneMapping`、exposure 1.0 | Blender view transform 為 **AgX**——兩者必然「接近但不完全相同」(AgX 高光壓縮更強),接受此差異 |
| Color space | three.js r152+ 預設 `outputColorSpace = SRGBColorSpace`,GLTFLoader 自動把 basecolor 標 sRGB,不需手動設定 | Cycles 輸出經 sRGB view transform |

實作位置:`web/src/components/SceneEnvironment.vue`(掛 environment / background)+ `ModelViewer.vue`(TresCanvas `tone-mapping`)。

## 攝影棚模式(`studio` prop,一致性驗證頁使用)

模型在 viewer 正規化為最長邊 **1.6** 單位(Blender cleanup 端為 1.0,比例等價換算)。

| 項目 | 值 | 對映 Blender 端 |
|---|---|---|
| 背景 | `scene.background = #ffffff` | 透明底片 + Pillow 合成白底 |
| 相機 | 方位角 30° / 仰角 18°、FOV 39.6°(= 50mm / 36mm 感光片)、距離 = (1.6/2)/tan(FOV/2) × 1.4 | `setup_camera.frame_camera(azimuth=30, elevation=18, margin=1.4, lens_mm=50)` |
| 打光 | 三盞 DirectionalLight:Key 75°/45° 強度 **8.5**、Fill −30°/20° **2.7**、Rim 200°/40° **5.2**(比例 = Blender 瓦數 400:130:250;整體係數以 radio 並排截圖的物件平均亮度迭代校正,兩端 mean 178 vs 178 一致) | `build_lighting()` 三盞 Area Light |

### 座標轉換(Blender Z-up → three.js Y-up)

Blender `spherical()`(方位角 0° = 正前方 −Y):`(d·cosEl·sinAz, −d·cosEl·cosAz, d·sinEl)`
經 glTF 轉換 `(x, y, z) → (x, z, −y)` 後,three.js 端等價式:

```ts
(d·cosEl·sinAz, d·sinEl, d·cosEl·cosAz)   // 方位角 0° = +Z(面向鏡頭)
```

兩端共用同一組(方位角, 仰角)參數即可對齊,`ModelViewer.vue` 的 `spherical()` 即此式。

## 已知差異(接受,不追零差)

1. **Tone mapping**:AgX(Blender)vs ACESFilmic(three.js)——高光滾降曲線不同,金屬高光處 Blender 略灰、three.js 略亮。
2. **光源形狀**:Blender 為 Area Light(大面積軟光),three.js 用 DirectionalLight 近似——陰影邊緣與漸層較硬。
3. **接觸陰影**:Blender 有 shadow catcher 地板,viewer 攝影棚模式目前無地板陰影(必要時可補 cientos `<ContactShadows>`)。
4. **降噪與採樣**:Cycles 128 samples + OpenImageDenoise vs 即時光柵化。

## 校正旋鈕(目視迭代時調這些)

- `ModelViewer.vue`:`HDRI_INTENSITY`(0.4)、`studioLights` 三盞強度(現值 8.5 / 2.7 / 5.2)
- 必要時:TresCanvas `tone-mapping-exposure`(目前 1.0,未顯式設定)
- Blender 端不動——以 `preview.webp` 為基準單向校 viewer
- 已做過一次定量校正(2026-08-26):以 radio 並排截圖量測物件區域平均亮度,燈光整體係數從 2.0/0.65/1.25 迭代三輪到 8.5/2.7/5.2,兩端 mean 達 177.7 vs 178.3(median 173 vs 185,右側中間調仍略暗——DirectionalLight 無 Area Light 的包覆感,由 HDRI 部分補償)

## 驗證流程

1. `cd web && npm run dev` → 開 `http://localhost:5173/?mode=consistency`
2. 下拉切換三類素材(radio / fishbowl / coral),`preview.webp` 需先複製到 `web/public/renders/`
3. 重點看:整體亮度、basecolor 色相、金屬反射位置;拖曳右側檢查非渲染角度的材質行為
4. 調整校正旋鈕 → 瀏覽器熱更新即時比對 → 收斂後把最終值更新回本文件
