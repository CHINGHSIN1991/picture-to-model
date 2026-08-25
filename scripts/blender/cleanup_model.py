"""Phase 2 Step 2-2: AI 原始 GLB → 修整後高模 + Web 輕量版。

跑在 Blender 內(經 scripts/run_blender.py 呼叫):

    uv run scripts/run_blender.py cleanup_model -- --job-dir output/<job_id>
    uv run scripts/run_blender.py cleanup_model -- \
        --input in.glb --output-high high.glb --output-web web.glb --target-tris 30000

流程:匯入 → 合併 mesh → 正規化(置中 + 單位大小)→ 修整(重複頂點 /
法線 / 內部面)→ 匯出高模 → Decimate → 匯出 Web 版。
統計數字寫進 --job-dir 的 metadata.json(cleanup 欄位)。
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _util import export_glb, import_glb, reset_scene, script_args, select_only, triangle_count

# 內部面選中比例超過此值視為 select_interior_faces 誤判(非水密網格),跳過刪除
MAX_INTERIOR_RATIO = 0.5


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-dir", type=Path, help="output/<job_id>,自動推導各檔案路徑")
    ap.add_argument("--input", type=Path, help="輸入 GLB(預設 <job-dir>/model_raw.glb)")
    ap.add_argument("--output-high", type=Path, help="高模輸出(預設 <job-dir>/model_high.glb)")
    ap.add_argument("--output-web", type=Path, help="Web 版輸出(預設 <job-dir>/model.glb)")
    ap.add_argument("--target-tris", type=int, default=30000, help="Web 版目標三角形數")
    ap.add_argument("--keep-interior", action="store_true", help="不刪除內部面(除錯用)")
    args = ap.parse_args(script_args())

    if args.job_dir:
        args.input = args.input or args.job_dir / "model_raw.glb"
        args.output_high = args.output_high or args.job_dir / "model_high.glb"
        args.output_web = args.output_web or args.job_dir / "model.glb"
    if not (args.input and args.output_high and args.output_web):
        ap.error("需要 --job-dir,或同時給 --input / --output-high / --output-web")
    if not args.input.exists():
        ap.error(f"找不到輸入檔: {args.input}")
    return args


def merge_meshes(meshes: list[bpy.types.Object]) -> bpy.types.Object:
    """合併為單一 mesh,脫離 parent(保留世界座標),清掉非 mesh 物件。"""
    select_only(meshes)
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    for o in [o for o in bpy.context.scene.objects if o is not obj]:
        bpy.data.objects.remove(o, do_unlink=True)
    return obj


def normalize(obj: bpy.types.Object) -> None:
    """置中於原點、最長邊縮放到 1 單位,套用 transform。"""
    select_only([obj])
    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_VOLUME", center="BOUNDS")
    obj.location = (0.0, 0.0, 0.0)
    max_dim = max(obj.dimensions)
    if max_dim > 0:
        obj.scale = tuple(s / max_dim for s in obj.scale)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def repair_mesh(obj: bpy.types.Object, keep_interior: bool) -> dict:
    """合併重複頂點、重算法線、刪除內部面。回傳統計。"""
    verts_before = len(obj.data.vertices)
    select_only([obj])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    interior_removed = 0
    if not keep_interior:
        faces_before = len(obj.data.polygons)
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_mode(type="FACE")
        bpy.ops.mesh.select_interior_faces()
        # 非水密網格(如 TRELLIS 輸出)會讓 select_interior_faces 把大半
        # 表面誤判成內部面。選中比例過高視為誤判,跳過刪除保住模型。
        bpy.ops.object.mode_set(mode="OBJECT")
        selected = sum(1 for p in obj.data.polygons if p.select)
        if 0 < selected <= faces_before * MAX_INTERIOR_RATIO:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.delete(type="FACE")
            bpy.ops.object.mode_set(mode="OBJECT")
            interior_removed = faces_before - len(obj.data.polygons)
        elif selected:
            print(
                f"[cleanup] 警告: 內部面選中 {selected}/{faces_before} "
                f"(> {MAX_INTERIOR_RATIO:.0%}),疑似非水密網格誤判,跳過刪除"
            )
    else:
        bpy.ops.object.mode_set(mode="OBJECT")
    return {
        "merged_vertices": verts_before - len(obj.data.vertices),
        "interior_faces_removed": interior_removed,
    }


def decimate(obj: bpy.types.Object, target_tris: int) -> float:
    """Collapse decimate 到目標三角形數,回傳實際 ratio。"""
    current = triangle_count(obj)
    ratio = min(1.0, target_tris / max(current, 1))
    if ratio >= 1.0:
        return 1.0
    select_only([obj])
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return ratio


def write_metadata(job_dir: Path | None, stats: dict) -> None:
    if not job_dir:
        return
    meta_path = job_dir / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta["cleanup"] = stats
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    t0 = time.time()

    reset_scene()
    meshes = import_glb(str(args.input))
    if not meshes:
        sys.exit(f"GLB 內沒有 mesh: {args.input}")
    print(f"[cleanup] 匯入 {len(meshes)} 個 mesh")

    obj = merge_meshes(meshes)
    tris_raw = triangle_count(obj)
    normalize(obj)
    repair_stats = repair_mesh(obj, keep_interior=args.keep_interior)
    tris_high = triangle_count(obj)

    args.output_high.parent.mkdir(parents=True, exist_ok=True)
    export_glb(str(args.output_high))
    print(f"[cleanup] 高模 {tris_high} tris → {args.output_high}")

    ratio = decimate(obj, args.target_tris)
    tris_web = triangle_count(obj)
    args.output_web.parent.mkdir(parents=True, exist_ok=True)
    export_glb(str(args.output_web))
    print(f"[cleanup] Web 版 {tris_web} tris (ratio={ratio:.4f}) → {args.output_web}")

    stats = {
        "blender_version": bpy.app.version_string,
        "tris_raw": tris_raw,
        "tris_high": tris_high,
        "tris_web": tris_web,
        "target_tris": args.target_tris,
        "decimate_ratio": round(ratio, 4),
        **repair_stats,
        "high_glb_bytes": args.output_high.stat().st_size,
        "web_glb_bytes": args.output_web.stat().st_size,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    write_metadata(args.job_dir, stats)
    print(f"[cleanup] 完成 ({stats['elapsed_sec']}s): {json.dumps(stats, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
