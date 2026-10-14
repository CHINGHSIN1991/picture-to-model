# Step 13 — 逐件動畫:模型必須先能拆,動畫方式由 spec 指定

## 目標

1. 確保模型結構在 **Blender 階段**就被設計成可以在 Three.js 中逐件操控。
2. 在瀏覽器端實作一個**通用的 `PartAnimator`**:每個零件群組(part group)的動畫方式
   (`explode` / `stack` / `grow` / `path` / `orbit` / `custom`)由 `PROJECT_SPEC.md` 指定,
   程式碼不寫死任何一種。

## 為什麼

影片裡的 sculpture 是「完整 → 散開 → 移動 → 重組」,但那只是**其中一種**逐件動畫。
本專案的零件要「岩塊由下往上堆起、珊瑚長出來、潛水員下潛」;換一個專案可能又完全不同。
所以 roadmap 只規定兩件事:

- **模型要可拆**:每個要動的零件是獨立 node、有正確 origin、重複件共用 geometry。
- **動畫方式是資料,不是程式碼**:同一個 `PartAnimator` 讀不同 config 就產生不同動畫。
  未來平台讓使用者改 config 就能換動畫,不用改程式。

不管哪種方式,都**不能**只是一整塊 mesh。
如果 Blender export 時全部被 join,網頁端什麼都做不了。
所以這個需求要在 Step 02 / 03 / 04 就提前講清楚,這一步是回頭確認 + 瀏覽器端實作。

## 前置條件

- Step 06 的 GLB 階層已確認可動元件是獨立 node(若不是,回 Blender 修)
- `PROJECT_SPEC.md` 的「零件群組」與「逐件動畫」兩個表已填

## 動畫方式目錄(mode catalog)

每個 mode 都用同一個參數 **`t` = departure(離開 rest 的程度)**:

- `t = 0`:零件在 GLB 裡的原位(rest)
- `t = 1`:該 mode 定義的「離開狀態」

所有 mode 共用這個語意,所以「什麼都沒發生」的 section 一律是全 0,不用知道任何 mode 細節。
要做「堆起 / 長出」這類**進場**效果,section 序列就寫 `1 → 0`;要做「散開」就寫 `0 → 1`。

| mode | `t = 1` 時的狀態 | 需要的 origin | 參數 | 典型用途 |
|------|------------------|---------------|------|----------|
| `explode` | 沿「中心 → 零件」方向向外偏移 | 任意 | `center`、`distance`、`jitter` | 散開 / 重組 |
| `stack` | 沉到 rest 下方 `dropHeight` | 底面中心 | `dropHeight`、`order`、`stagger` | 由下往上逐層堆起 |
| `grow` | scale 0(從 origin 縮到沒有) | 接觸點 / 根部 | `order`、`stagger`、`overshoot` | 依序長出 |
| `path` | 位於曲線起點 | 任意 | `offsets[]`(相對 rest,最後一點必為 `[0,0,0]`) | 單一物件沿曲線進場 |
| `orbit` | 繞 `axis` 公轉 `angle` | 任意 | `center`、`axis`、`angle` | 魚群環繞進場 |
| `custom` | 由函式決定 | — | `fn(out, state, t)` | 上述都不合時 |

`stagger` + `order` 讓同一群組的 instance 不同時動:`order` 決定誰先(`index` / `height` / `distance` / `random`),
`stagger` 是相鄰兩個的 progress 間隔。
每個 instance 另有獨立彈簧(見下),所以散開 / 回彈 / 長出都有生命感。

時間驅動的 idle(海草擺動、魚游動、浮動)**不屬於**這裡,那是 vertex shader / 路徑動畫,見 PROJECT_SPEC 的 Idle 表。

## 操作步驟

### 1. Blender 階段的要求(應該已經在 Step 03/04 提過,這裡再確認)

```
Structure the asset so its repeated components
can be manipulated individually in Three.js.

Do not merge all pieces into one mesh.

If there are many repeated pieces,
design them so the browser implementation
can use InstancedMesh where practical.

Specifically:
- each animatable part is its own object; its origin is where PROJECT_SPEC.md says
  (attachment point for "grow", bottom center for "stack", etc.)
- repeated variants share the same mesh data (linked duplicates)
- name pattern: <Category>_<Variant>_<Index>, e.g. Coral_BranchA_017
- store nothing in modifiers that would be lost on export (apply them)
```

檢查 GLB(把 prefix 換成 PROJECT_SPEC 的群組):
```
Load export/<asset>.glb and list every node matching each part-group pattern in PROJECT_SPEC.md.
Group them by shared geometry (same vertex count + same bounding box).
Report per group: number of unique geometries vs. number of instances,
and whether each node's origin matches the rule in PROJECT_SPEC.md.
```

### 2. Config:把 PROJECT_SPEC 的表翻成程式可讀的資料

```ts
// config/partAnimations.ts
export type PartMode = 'explode' | 'stack' | 'grow' | 'path' | 'orbit' | 'custom';

export interface PartGroupConfig {
  name: string;                 // SectionState.parts 的 key
  match: RegExp;                // 哪些 node 屬於這群,例如 /^Coral_/
  mode: PartMode;
  spring: number;               // 每個 instance 的彈簧速度,建議 6
  stagger?: number;             // 相鄰 instance 的 progress 間隔,建議 0.02~0.1
  order?: 'index' | 'height' | 'distance' | 'random';
  params?: Record<string, unknown>;
  instancing?: boolean;         // true:同 geometry 轉 InstancedMesh
}

// 內容照 PROJECT_SPEC.md 填;以下只是本專案的例子
export const partGroups: PartGroupConfig[] = [
  { name: 'rocks',  match: /^Rock_(Peak|Tier)_/, mode: 'stack', spring: 5, stagger: 0.1, order: 'height',
    params: { dropHeight: 1.5 } },
  { name: 'corals', match: /^(Coral|Kelp)_/,     mode: 'grow',  spring: 6, stagger: 0.03, order: 'random',
    params: { overshoot: 0.15 }, instancing: true },
  { name: 'diver',  match: /^Diver$/,            mode: 'path',  spring: 4,
    params: { offsets: [[-1.0, 3.0, 0.5], [-0.5, 1.2, 0.3], [0, 0, 0]] } },
  { name: 'fish',   match: /^Fish_/,             mode: 'orbit', spring: 6, stagger: 0.02, order: 'index',
    params: { center: [0, 0.8, 0], axis: [0, 1, 0], angle: Math.PI * 2 }, instancing: true },
];
```

### 3. 瀏覽器端:InstancedMesh 轉換(prefix 來自 config,不寫死)

載入 GLB 後,把 `instancing: true` 群組中共用 geometry 的節點合併成 `InstancedMesh`:

```ts
// Model.ts
function buildInstances(root: THREE.Group, group: PartGroupConfig) {
  const byGeom = new Map<string, THREE.Mesh[]>();
  root.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh || !group.match.test(m.name)) return;
    const key = m.geometry.uuid;           // linked duplicates 在 glTF 會共用 geometry
    (byGeom.get(key) ?? byGeom.set(key, []).get(key)!).push(m);
  });

  const instanced: THREE.InstancedMesh[] = [];
  for (const [, meshes] of byGeom) {
    if (meshes.length < 4) continue;       // 太少就不值得
    const im = new THREE.InstancedMesh(meshes[0].geometry, meshes[0].material, meshes.length);
    meshes.forEach((m, i) => {
      m.updateWorldMatrix(true, false);
      im.setMatrixAt(i, m.matrixWorld);
      m.parent?.remove(m);
    });
    im.name = `${group.name}__${meshes[0].name}`;
    root.add(im);
    instanced.push(im);
  }
  return instanced;
}
```

### 4. 通用 PartAnimator

一個 class 管所有群組。每個零件(獨立 node 或 instance)一組狀態;
`mode` 只是一張「`t` → matrix」的函式表,新增 mode 就是多加一個函式。

```ts
// PartAnimator.ts
interface PartState {
  target: THREE.Object3D | { im: THREE.InstancedMesh; index: number };
  restPos: THREE.Vector3; restQuat: THREE.Quaternion; restScale: THREE.Vector3;  // 載入時記下
  seed: number;        // 0~1,固定隨機(jitter / random order 用)
  delay: number;       // 由 stagger + order 算出,0~(1 - span)
  current: number;     // 目前 departure(有彈簧)
}

type ModeFn = (out: Transform, s: PartState, t: number, p: any, ctx: { center: THREE.Vector3 }) => void;

const modes: Record<PartMode, ModeFn> = {
  explode(out, s, t, p, ctx) {
    const dir = s.restPos.clone().sub(ctx.center).normalize();
    out.pos.copy(s.restPos).addScaledVector(dir, p.distance * (1 + p.jitter * (s.seed - 0.5)) * t);
  },
  stack(out, s, t, p) {
    out.pos.copy(s.restPos); out.pos.y -= p.dropHeight * t;
  },
  grow(out, s, t, p) {
    const k = (1 - t) * (1 + (p.overshoot ?? 0) * Math.sin(Math.PI * (1 - t)));   // 微彈跳
    out.scale.copy(s.restScale).multiplyScalar(k);
  },
  path(out, s, t, p) {
    const curve = new THREE.CatmullRomCurve3(p.offsets.map((o: number[]) => new THREE.Vector3(...o)));
    out.pos.copy(s.restPos).add(curve.getPoint(1 - t));   // offsets 最後一點是 [0,0,0] → t=0 回到 rest
  },
  orbit(out, s, t, p, ctx) {
    const axis = new THREE.Vector3(...p.axis).normalize();
    const c = p.center ? new THREE.Vector3(...p.center) : ctx.center;
    out.pos.copy(s.restPos).sub(c).applyAxisAngle(axis, p.angle * t).add(c);
    out.quat.copy(s.restQuat).premultiply(new THREE.Quaternion().setFromAxisAngle(axis, p.angle * t));
  },
  custom(out, s, t, p) { p.fn(out, s, t); },
};

export class PartAnimator {
  private groups: { cfg: PartGroupConfig; states: PartState[]; span: number }[] = [];
  private progress: Record<string, number> = {};   // group name → departure target

  constructor(root: THREE.Group, configs: PartGroupConfig[]) { /* 收集 node / instance,記 rest,算 delay */ }

  /** Step 12 的 render loop 每 frame 呼叫一次 */
  setProgress(parts: Record<string, number>) { Object.assign(this.progress, parts); }

  update(dt: number) {
    for (const g of this.groups) {
      const t = this.progress[g.cfg.name] ?? 0;
      for (const s of g.states) {
        const local = THREE.MathUtils.clamp((t - s.delay) / (1 - g.span), 0, 1);   // stagger
        s.current += (local - s.current) * Math.min(1, dt * g.cfg.spring);        // 彈簧
        const out = { pos: s.restPos.clone(), quat: s.restQuat.clone(), scale: s.restScale.clone() };
        modes[g.cfg.mode](out, s, s.current, g.cfg.params ?? {}, this.ctx);
        apply(s.target, out);   // Object3D → position/quaternion/scale;instance → setMatrixAt + needsUpdate
      }
    }
  }
}
```

重點:

- **一個 group 一個 key**,Step 12 的 `SectionState.parts` 就是 `{ rocks: 0, corals: 0, diver: 0, fish: 0 }`。
- **`t = 0` 永遠是 rest**。載入後呼叫 `setProgress(sections[0].parts)`,若 Hero 本來就要完整,全 0 即可。
- **進場動畫(非 scroll)**也走同一條路:載入時把某群組 `t` 從 1 tween 到 0,不必另寫一套。
- `apply` 對 `InstancedMesh` 要在迴圈結束後設一次 `instanceMatrix.needsUpdate = true`。

### 5. 影片 repo 提到的其他技巧

| 技巧 | 用途 |
|------|------|
| shared geometry | 所有同型元件共用一份 geometry,省記憶體與 draw call |
| instancing | 幾百個元件一個 draw call |
| local spring motion | 每個 instance 獨立的彈簧,任何 mode 都有生命感 |
| click vs drag | 區分點擊(觸發單一元件動畫)與拖曳(旋轉整體),用移動距離 + 時間判斷 |
| shader light pulse | 自訂 `onBeforeCompile` 在 instance 上加 uniform 驅動的發光脈衝 |

click vs drag 判斷:

```ts
let down: { x: number; y: number; t: number } | null = null;
window.addEventListener('pointerdown', (e) => (down = { x: e.clientX, y: e.clientY, t: performance.now() }));
window.addEventListener('pointerup', (e) => {
  if (!down) return;
  const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
  const held = performance.now() - down.t;
  if (moved < 6 && held < 300) onClick(e); else onDragEnd(e);
  down = null;
});
```

點擊 InstancedMesh 用 raycaster 的 `instanceId` 找到被點的那個;
被點的 instance 要做什麼(彈跳、變亮)同樣寫在 PROJECT_SPEC,不寫死。

## 完成條件 (Definition of Done)

- [ ] GLB 中可動元件都是獨立 node,origin 符合 PROJECT_SPEC,重複元件共用 geometry
- [ ] `config/partAnimations.ts` 與 PROJECT_SPEC 的「逐件動畫」表一致
- [ ] 瀏覽器端已把 `instancing: true` 的群組轉成 InstancedMesh,draw call 明顯下降(`renderer.info.render.calls`)
- [ ] `PartAnimator` 對每個 group 都能平滑地 `t: 0 ↔ 1`,且**只改 config 就能換 mode**(例如把 `grow` 改成 `explode` 看一眼)
- [ ] 每個 instance 有獨立彈簧與 stagger
- [ ] (可選)點擊單一元件有回饋

## 常見問題

- **glTF 載入後 geometry 沒共用** → Blender export 時沒用 linked duplicates,或 modifier 讓每個變不同;回 Blender 修 `02_detail.py`。
- **`grow` 從錯的點長出 / `stack` 沉下去的位置怪** → origin 不符合該 mode 的要求;回 Blender 設 origin。
- **`explode` 散開方向怪** → `center` 設錯,或零件 origin 離 geometry 太遠。
- **InstancedMesh 不吃原本材質的 emissive 動畫** → 用 `onBeforeCompile` 加 per-instance attribute。
- **某群組要兩種動畫(例如先長出、之後又要散開)** → 同一批 node 可以屬於兩個 group(兩個 config 項,不同 `name`),PartAnimator 依序套用;或用 `custom`。

## 下一步

→ [14-mobile-fallback.md](./14-mobile-fallback.md)
