# Step 04 — Graybox OK 後,做完整模型

## 目標

把核准的 graybox 細化成最終模型:次要造型、表面細節、材質、bevel、乾淨的 topology 與 normals。
**同時維持 web 友善的面數,並保留可動元件的分離。**

## 為什麼

灰模確認了「形」,這一步補「質」。
因為目標是即時 Three.js 網站,**視覺衝擊力 > 幾何複雜度**。
很多細節用材質(normal map、roughness、emissive)做,比加面數划算。

影片中 Codex 大約用了 12 分 40 秒自動完成一次 Blender asset 建立,
主要靠 scripting,而不是手動操作 Blender UI。
(這只是作者那次案例的時間,不代表固定速度。)

## 前置條件

- Step 03 完成,graybox 比例已核准
- `blender/scripts/01_graybox.py` 可重現

## 操作步驟

### 1. 要求 Codex 細化

```
Refine the approved graybox into the final model.

Start from blender/scripts/01_graybox.py and produce blender/scripts/02_detail.py.
The new script must still be fully reproducible from an empty scene.

Use references/final-concept.png as the visual target.

Add:
- secondary forms
- surface details
- polished materials
- appropriate bevels
- optimized topology
- proper normals
- realistic but web-friendly shading

Important:
This asset is intended for a real-time Three.js website,
so prioritize visual impact over unnecessary geometric complexity.

Keep interactive or animated pieces as separate objects where useful.

Stay within the polygon budget defined in blender/MODEL_PLAN.md.
Report the triangle count per object group when done.

Save:
- blender/scenes/02_detail.blend
- blender/scripts/02_detail.py
```

### 2. 材質的 web 友善原則

Three.js 的 `MeshStandardMaterial` / `MeshPhysicalMaterial` 能吃的 glTF 材質參數:

| 可以 export 到 glTF | 不會 export(網頁端要重做) |
|--------------------|--------------------------|
| Base Color | 複雜 node tree(procedural noise 等) |
| Metallic / Roughness | Shader-to-RGB |
| Normal map | Volume / SSS(部分) |
| Emissive | Blender 專屬的 light path trick |
| Alpha | Displacement(需 bake) |
| Transmission / Clearcoat(部分) | Hair / Particles |

所以要求:

```
For every material:
- use Principled BSDF only
- if a procedural texture is needed, bake it to an image texture (max 2048x2048)
- keep emissive as a plain color or baked emissive map
- do not rely on Blender-only shader nodes
```

### 3. 確認物件結構沒有被合併

```
Confirm that the object hierarchy still matches blender/MODEL_PLAN.md.
List any objects that were joined or merged during detailing and undo any merge
that affects a component marked as animatable.
```

### 4. 重複元件先規劃 instancing

如果有大量重複元件(珊瑚分枝、魚):

```
For repeated components (coral branches, fish):
- model each unique variant once
- place copies as linked duplicates (Alt+D) sharing the same mesh data
- give each copy a clear name like Coral_Branch_A_001
This allows InstancedMesh in Three.js later.
```

## 完成條件 (Definition of Done)

- [ ] `blender/scenes/02_detail.blend` 與 `blender/scripts/02_detail.py` 存在
- [ ] `blender --background --python blender/scripts/02_detail.py` 可以從零重現
- [ ] 三角面數在預算內(有報告)
- [ ] 所有材質是 Principled BSDF,procedural 已 bake
- [ ] 可動元件仍是獨立物件
- [ ] 重複元件共用 mesh data

## 常見問題

- **面數爆了** → 要求 decimate 或把 subdivision 降一級,細節改用 normal map。
- **AI 用了 Blender 專屬 node** → 要求 bake 成 image texture。
- **script 跑很久** → 可以把 bake 步驟拆成獨立 script,只在材質改動時重跑。

## 下一步

→ [05-render-and-inspect.md](./05-render-and-inspect.md)
