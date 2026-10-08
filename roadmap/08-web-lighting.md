# Step 08 — 在 Browser 裡重新調光

## 目標

讓 Three.js 裡的模型**視覺上**接近 `references/final-concept.png`。
重點在光線、曝光、材質參數,**不動幾何**。

## 為什麼

**Blender render 漂亮 ≠ WebGL 一定漂亮。**

- Blender 的燈光、world、volume 都不會進 GLB。
- Eevee / Cycles 和 Three.js 的 PBR 實作不同,同樣參數結果不同。
- 網頁端是即時渲染,要用更便宜的技巧(environment map、rim light、emissive)做出類似感覺。

## 前置條件

- Step 07 完成,viewer 可以看到模型

## 操作步驟

### 1. 通用調光 prompt

```
Adjust the Three.js lighting and materials
to visually match references/final-concept.png.

Do not modify the geometry unless necessary.

Focus on:
- exposure
- directional/key lighting
- rim lighting
- emissive elements
- roughness
- metalness
- contrast against the background

Put all lighting setup in web/src/three/createLighting.ts
so it can be tuned independently.
```

### 2. 場景專屬 prompt(珊瑚範例)

```
Create an underwater lighting environment.

Use:
- soft blue ambient light
- directional light from the upper-right
- subtle caustic-like movement
- slight volumetric-looking depth effect
- emissive highlights on selected coral

Keep performance suitable for real-time rendering.
```

### 3. 可調參數清單

建議讓 Codex 把這些做成一個 config 物件,方便之後平台做「光源控制」UI:

```ts
export const lightingConfig = {
  exposure: 1.1,
  ambient: { color: 0x1a3a5c, intensity: 0.6 },
  key:     { color: 0xffffff, intensity: 2.5, position: [4, 6, 3] },
  rim:     { color: 0x4fc3f7, intensity: 1.8, position: [-4, 3, -4] },
  fill:    { color: 0x0d2a45, intensity: 0.4, position: [-2, 1, 4] },
  fog:     { color: 0x02101c, near: 6, far: 18 },
  envMapIntensity: 0.8,
};
```

### 4. 便宜但有效的技巧

| 效果 | 做法 | 成本 |
|------|------|------|
| 水下深度感 | `scene.fog = new THREE.Fog(...)` | 幾乎免費 |
| 焦散 / 水光 | 一張 caustic texture 用 `DirectionalLight` 的 map 或 shader 做 UV scroll | 低 |
| 發光珊瑚 | material.emissive + `UnrealBloomPass`(可選) | bloom 中等,手機要關 |
| 整體反射 | `PMREMGenerator` + 小張 HDR(512px) | 低 |
| Rim light | 一盞反向 `DirectionalLight` 冷色 | 免費 |

### 5. 即時調參

加一個暫時的 debug UI(lil-gui)方便調:

```bash
bun add -d lil-gui
```

```
Add a temporary lil-gui panel bound to lightingConfig so I can tune
exposure, light intensities, colors, and fog in the browser.
Print the final config to console on demand so I can paste it back.
```

### 6. 截圖比對

調完後,在 viewer 裡用和 concept 相同構圖截圖,存成 `web/screenshots/lighting-v1.png`,
和 reference 並排看。

## 平台化提醒

這一步產出的 `lightingConfig` 與 material 參數,
就是未來平台「材質控制 / 光源控制 / 相機控制」的資料結構。
現在就把它設計成可序列化(plain JSON),不要散在程式碼裡。

## 完成條件 (Definition of Done)

- [ ] `web/src/three/createLighting.ts` 存在,參數集中在 config
- [ ] 截圖與 reference 的氛圍接近
- [ ] 桌機 60fps(開 stats.js 看)
- [ ] 暫時的 lil-gui 可以關掉(用 `?debug` query 切換)

## 常見問題

- **怎麼調都偏灰** → 檢查 `toneMapping`、`outputColorSpace`、texture 的 `colorSpace`。
- **emissive 看不到** → emissive 強度在 GLB 可能被 clamp 到 1,在 Three.js 端 `material.emissiveIntensity` 拉高。
- **bloom 吃效能** → 降 bloom 解析度,或改用 emissive 本身 + fog 製造光暈感。

## 下一步

→ [09-website-mockup.md](./09-website-mockup.md)
