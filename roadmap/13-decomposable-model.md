# Step 13 — 要「爆開」效果,模型必須先能拆

## 目標

確保模型結構在 **Blender 階段**就被設計成可以在 Three.js 中逐件操控,
並在瀏覽器端用 InstancedMesh 等技巧有效率地實作「散開 → 移動 → 重組」。

## 為什麼

影片裡的 sculpture 會:

```
完整
  ↓
散開
  ↓
移動
  ↓
重新組合
```

這**不能**只是一整塊 mesh。
如果 Blender export 時全部被 join,網頁端什麼都做不了。
所以這個需求要在 Step 02 / 03 / 04 就提前講清楚,這一步是回頭確認 + 瀏覽器端實作。

## 前置條件

- Step 06 的 GLB 階層已確認可動元件是獨立 node(若不是,回 Blender 修)

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
- each coral branch / plate is its own object with origin at its attachment point
- repeated variants share the same mesh data (linked duplicates)
- name pattern: Coral_<Variant>_<Index>, e.g. Coral_BranchA_017
- store nothing in modifiers that would be lost on export (apply them)
```

檢查 GLB:
```
Load export/reef.glb and list every node whose name starts with "Coral_".
Group them by shared geometry (same vertex count + same bounding box).
Report: number of unique geometries vs. number of instances.
```

### 2. 瀏覽器端:InstancedMesh 轉換

載入 GLB 後,把共用 geometry 的節點合併成 `InstancedMesh`:

```ts
// ReefModel.ts
function buildInstances(root: THREE.Group) {
  const groups = new Map<string, THREE.Mesh[]>();
  root.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh || !m.name.startsWith('Coral_')) return;
    const key = m.geometry.uuid;           // linked duplicates 在 glTF 會共用 geometry
    (groups.get(key) ?? groups.set(key, []).get(key)!).push(m);
  });

  const instanced: THREE.InstancedMesh[] = [];
  for (const [, meshes] of groups) {
    if (meshes.length < 4) continue;       // 太少就不值得
    const im = new THREE.InstancedMesh(meshes[0].geometry, meshes[0].material, meshes.length);
    meshes.forEach((m, i) => {
      m.updateWorldMatrix(true, false);
      im.setMatrixAt(i, m.matrixWorld);
      m.parent?.remove(m);
    });
    im.userData.rest = meshes.map((m) => m.matrixWorld.clone());
    root.add(im);
    instanced.push(im);
  }
  return instanced;
}
```

### 3. 每個 instance 的 local spring motion

```ts
// 每個 instance 一組 rest / target / current
interface InstanceState {
  rest: THREE.Matrix4;
  explodeDir: THREE.Vector3;   // 從模型中心指向該 instance
  explodeDist: number;         // 依距離中心遠近決定,加一點隨機
  current: number;             // 目前 explode 進度(有彈簧)
}

update(explodeTarget: number, dt: number) {
  for (let i = 0; i < n; i++) {
    const s = states[i];
    // 彈簧
    s.current += (explodeTarget - s.current) * Math.min(1, dt * 6);
    _m.copy(s.rest);
    _m.setPosition(_p.setFromMatrixPosition(s.rest).addScaledVector(s.explodeDir, s.explodeDist * s.current));
    im.setMatrixAt(i, _m);
  }
  im.instanceMatrix.needsUpdate = true;
}
```

### 4. 影片 repo 提到的其他技巧

| 技巧 | 用途 |
|------|------|
| shared geometry | 所有同型元件共用一份 geometry,省記憶體與 draw call |
| instancing | 幾百個元件一個 draw call |
| local spring motion | 每個 instance 獨立的彈簧,散開 / 回彈有生命感 |
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

點擊 InstancedMesh 用 raycaster 的 `instanceId` 找到被點的那個。

## 完成條件 (Definition of Done)

- [ ] GLB 中可動元件都是獨立 node,重複元件共用 geometry
- [ ] 瀏覽器端已轉成 InstancedMesh,draw call 明顯下降(用 `renderer.info.render.calls` 看)
- [ ] `setExplode(t)` 可以平滑散開 / 重組
- [ ] 每個 instance 有獨立彈簧
- [ ] (可選)點擊單一元件有回饋

## 常見問題

- **glTF 載入後 geometry 沒共用** → Blender export 時沒用 linked duplicates,或 modifier 讓每個變不同;回 Blender 修 `02_detail.py`。
- **散開方向怪** → origin 不在 attachment point;回 Blender 設 origin。
- **InstancedMesh 不吃原本材質的 emissive 動畫** → 用 `onBeforeCompile` 加 per-instance attribute。

## 下一步

→ [14-mobile-fallback.md](./14-mobile-fallback.md)
