# 評估紀錄(Evaluation)

> 對應 [ROADMAP.md](../ROADMAP.md) 各階段的評估與決策紀錄。
> Phase 0 的正式選型評估未逐項執行(直接以 Tripo 進入 PoC 驗證,運作良好);
> 本文件自 Phase 3 起補齊各項評估。

---

## 附錄 A:AI 貼圖 PBR 品質評估(Phase 3 Step 3-2,2026-08-26)

### 方法

固定相機、整組光源(三點打光 + HDRI)繞 Z 軸旋轉 0° / 120° / 240° 各渲一張
(`uv run scripts/eval_textures.py output/<job_id>`,Cycles 64 samples / 800px):

- 高光與陰影**跟著光走** → 貼圖是乾淨的 PBR
- 亮部**黏在表面不動** → basecolor 烤死了光影(baked 殘留)

評估對象:Tripo API 內建 PBR 輸出(basecolor + ORM + normal,2048px)。
渲染圖存於 `output/<job_id>/eval/light_<deg>.webp`。

### 觀察

| 項目 | vintage-radio(hard-surface) | fishbowl(reflective) |
|---|---|---|
| 陰影方向 | ✅ 正確隨光旋轉 | ✅ 正確隨光旋轉 |
| 表面高光 | ✅ 機身光澤、金屬旋鈕與喇叭網的高光跟著光走,roughness 分布合理 | ✅ 球面頂部與邊緣的即時鏡面反射隨光移動,表面光澤感正確 |
| 金屬感 | ✅ 旋鈕/金屬件在不同角度呈現正確反射 | -(無金屬件) |
| baked 殘留 | ⚠️ 輕微:basecolor 有少量斑駁明暗(接近做舊質感,可接受) | ❌ 明顯:玻璃「窗」上的白色反光條紋與內容物亮部烤死在 basecolor,三個光照角度完全不動 |
| 其他 | - | ❌ 無透明:GLB 無 `alphaMode` / `KHR_materials_transmission`,玻璃是不透明表面(Phase 2 已記錄) |

### 結論

1. **第一版貼圖來源採用 Tripo API 內建 PBR 輸出**:
   hard-surface 與 organic 類的 roughness / metallic / normal 真實響應光照,達商品展示水準。
2. **品質不足時的 fallback**(依序):
   - 反光 / 透明類商品的 baked 反光:於 Phase 3 後續評估 **delighting(去光影)** 或 **Blender bake(Step 3-4)重出 basecolor**;
   - 玻璃透明感:需後製 **transmission 材質**(偵測玻璃區域、替換 shader),或在產品層面接受「烤圖玻璃」的呈現。
3. 反光類輸入照片建議在拍攝端減少環境反射(柔光箱、偏光鏡),從源頭降低 baked 殘留。
