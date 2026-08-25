"""Phase 2 Step 2-3: 檢查與修復 GLB 的 PBR 材質。

跑在 Blender 內(經 scripts/run_blender.py 呼叫):

    uv run scripts/run_blender.py setup_material -- --job-dir output/<job_id>
    uv run scripts/run_blender.py setup_material -- --input in.glb [--output out.glb]

--job-dir 模式會就地修復 model_high.glb 與 model.glb 兩個檔案。

修復內容:
- Image Texture 的 color space:連到 Base Color / Emission 的用 sRGB,
  其餘(Normal / Roughness / Metallic / AO)一律 Non-Color。
- 移除沒有連到 Material Output 的孤兒節點(AI 模型常見多餘的
  tex image 節點,會觸發 glTF 匯出警告)。
- 完全沒有材質的 mesh 補一個中性灰 Principled BSDF,避免渲染全黑。
統計數字寫進 --job-dir 的 metadata.json(material 欄位)。
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _util import export_glb, import_glb, reset_scene, script_args

# 連到這些 Principled 輸入的貼圖要用 sRGB,其餘 Non-Color
SRGB_INPUTS = {"Base Color", "Emission Color", "Emission"}
FALLBACK_GRAY = (0.541, 0.541, 0.541, 1.0)  # #8A8A8A


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-dir", type=Path, help="output/<job_id>,就地修復 model_high.glb 與 model.glb")
    ap.add_argument("--input", type=Path, help="單一輸入 GLB")
    ap.add_argument("--output", type=Path, help="輸出路徑(預設覆寫 --input)")
    args = ap.parse_args(script_args())

    if args.job_dir:
        args.targets = [
            (args.job_dir / "model_high.glb", args.job_dir / "model_high.glb"),
            (args.job_dir / "model.glb", args.job_dir / "model.glb"),
        ]
    elif args.input:
        args.targets = [(args.input, args.output or args.input)]
    else:
        ap.error("需要 --job-dir 或 --input")
    for src, _ in args.targets:
        if not src.exists():
            ap.error(f"找不到輸入檔: {src}")
    return args


def _output_node(tree: bpy.types.NodeTree) -> bpy.types.Node | None:
    outputs = [n for n in tree.nodes if n.type == "OUTPUT_MATERIAL"]
    active = [n for n in outputs if n.is_active_output]
    return (active or outputs or [None])[0]


def _reachable_backward(tree: bpy.types.NodeTree, root: bpy.types.Node) -> set[bpy.types.Node]:
    """從 Material Output 反向走訪,回傳有貢獻到輸出的節點集合。"""
    incoming: dict[bpy.types.Node, list[bpy.types.Node]] = {}
    for link in tree.links:
        incoming.setdefault(link.to_node, []).append(link.from_node)
    seen, stack = {root}, [root]
    while stack:
        for src in incoming.get(stack.pop(), []):
            if src not in seen:
                seen.add(src)
                stack.append(src)
    return seen


def _feeds_srgb_input(tree: bpy.types.NodeTree, tex: bpy.types.Node) -> bool:
    """貼圖節點是否(經任意中繼節點)連到 Principled 的 sRGB 類輸入。"""
    outgoing: dict[bpy.types.Node, list[tuple[bpy.types.Node, str]]] = {}
    for link in tree.links:
        outgoing.setdefault(link.from_node, []).append((link.to_node, link.to_socket.name))
    seen, stack = {tex}, [tex]
    while stack:
        for dst, socket in outgoing.get(stack.pop(), []):
            if dst.type == "BSDF_PRINCIPLED":
                if socket in SRGB_INPUTS:
                    return True
                continue  # 到 Principled 就停,不再往 Output 走
            if dst not in seen:
                seen.add(dst)
                stack.append(dst)
    return False


def fix_material(mat: bpy.types.Material, stats: dict) -> None:
    tree = mat.node_tree
    if tree is None:  # Blender 6.0 起 use_nodes 將移除,直接以 node_tree 判斷
        stats["principled_missing"] += 1
        print(f"[material]   警告: {mat.name} 沒有 node tree,略過")
        return
    out = _output_node(tree)
    if out is None or not any(n.type == "BSDF_PRINCIPLED" for n in tree.nodes):
        # 不強行重建既有 shader,只記錄讓人工判斷
        stats["principled_missing"] += 1
        print(f"[material]   警告: {mat.name} 缺 Principled BSDF / Material Output,略過")
        return

    # 1. 移除沒有貢獻到輸出的孤兒節點(含多餘的 tex image)
    keep = _reachable_backward(tree, out)
    orphans = [n for n in tree.nodes if n not in keep and n.type != "FRAME"]
    for n in orphans:
        print(f"[material]   移除孤兒節點: {mat.name} / {n.name} ({n.type})")
        tree.nodes.remove(n)
    stats["orphan_nodes_removed"] += len(orphans)

    # 2. 修 color space
    for n in tree.nodes:
        if n.type != "TEX_IMAGE" or n.image is None:
            continue
        want = "sRGB" if _feeds_srgb_input(tree, n) else "Non-Color"
        have = n.image.colorspace_settings.name
        if have != want:
            print(f"[material]   color space: {mat.name} / {n.image.name}: {have} → {want}")
            n.image.colorspace_settings.name = want
            stats["colorspace_fixed"] += 1


def make_fallback_material() -> bpy.types.Material:
    mat = bpy.data.materials.new("fallback_gray")
    if mat.node_tree is None:  # Blender ≤5.x 新材質預設沒有 node tree
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = FALLBACK_GRAY
    bsdf.inputs["Roughness"].default_value = 0.5
    return mat


def process_file(src: Path, dst: Path) -> dict:
    reset_scene()
    meshes = import_glb(str(src))
    if not meshes:
        sys.exit(f"GLB 內沒有 mesh: {src}")

    stats = {
        "materials": 0,
        "colorspace_fixed": 0,
        "orphan_nodes_removed": 0,
        "fallback_materials_created": 0,
        "principled_missing": 0,
    }
    fallback = None
    for obj in meshes:
        if not any(slot.material for slot in obj.material_slots):
            fallback = fallback or make_fallback_material()
            if obj.material_slots:
                obj.material_slots[0].material = fallback
            else:
                obj.data.materials.append(fallback)
            stats["fallback_materials_created"] += 1
            print(f"[material]   {obj.name} 無材質,補中性灰 fallback")

    seen: set[str] = set()
    for obj in meshes:
        for slot in obj.material_slots:
            if slot.material and slot.material.name not in seen:
                seen.add(slot.material.name)
                stats["materials"] += 1
                fix_material(slot.material, stats)

    export_glb(str(dst))
    return stats


def main() -> None:
    args = parse_args()
    t0 = time.time()

    per_file: dict[str, dict] = {}
    for src, dst in args.targets:
        print(f"[material] 處理 {src}")
        per_file[src.name] = process_file(src, dst)

    result = {"files": per_file, "elapsed_sec": round(time.time() - t0, 1)}
    if args.job_dir:
        meta_path = args.job_dir / "metadata.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        meta["material"] = result
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[material] 完成 ({result['elapsed_sec']}s): {json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
