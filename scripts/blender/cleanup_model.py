"""Phase 2 Step 2-2: AI 原始 GLB → 修整後高模 + Web 輕量版。

跑在 Blender 內(經 scripts/run_blender.py 呼叫):

    uv run scripts/run_blender.py cleanup_model -- --job-dir output/<job_id>
    uv run scripts/run_blender.py cleanup_model -- \
        --input in.glb --output-high high.glb --output-web web.glb --target-tris 30000
    # 多策略變體:另外輸出 web__collapse.glb / web__planar.glb / … + variants.json
    uv run scripts/run_blender.py cleanup_model -- \
        --input in.glb --output-high high.glb --output-web web.glb \
        --variants collapse,planar,unsubdiv

流程:匯入 → 合併 mesh → 正規化(置中 + 單位大小)→ 修整(重複頂點 /
法線 / 內部面)→ 匯出高模 → Decimate(--strategy)→ 匯出 Web 版
→(選用)各減面策略變體 + variants.json manifest。
統計數字寫進 --job-dir 的 metadata.json(cleanup 欄位)。
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _util import export_glb, import_glb, reset_scene, script_args, select_only, triangle_count

# 內部面選中比例超過此值視為 select_interior_faces 誤判(非水密網格),跳過刪除
MAX_INTERIOR_RATIO = 0.5

STRATEGIES = ("collapse", "planar", "unsubdiv")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-dir", type=Path, help="output/<job_id>,自動推導各檔案路徑")
    ap.add_argument("--input", type=Path, help="輸入 GLB(預設 <job-dir>/model_raw.glb)")
    ap.add_argument("--output-high", type=Path, help="高模輸出(預設 <job-dir>/model_high.glb)")
    ap.add_argument("--output-web", type=Path, help="Web 版輸出(預設 <job-dir>/model.glb)")
    ap.add_argument("--target-tris", type=int, default=30000, help="Web 版目標三角形數")
    ap.add_argument("--strategy", choices=STRATEGIES, default="collapse",
                    help="Web 版減面策略(預設 collapse)")
    ap.add_argument("--planar-angle", type=float, default=5.0,
                    help="planar 策略的平面角度容差(度)")
    ap.add_argument("--unsubdiv-iterations", type=int, default=2,
                    help="unsubdiv 策略的反細分次數(2 = 還原一層 subdivision)")
    ap.add_argument("--variants", type=str, default="",
                    help="逗號分隔的策略清單(如 collapse,planar,unsubdiv),"
                         "每個策略從修整後高模各自減面,輸出 <web 檔名>__<策略>.glb")
    ap.add_argument("--variant-tris", type=str, default="",
                    help="逗號分隔的目標面數清單(如 10000,30000,60000),"
                         "collapse 變體每個目標各出一檔 <web 檔名>__collapse-<N>k.glb")
    ap.add_argument("--variants-manifest", type=Path,
                    help="變體 manifest JSON 路徑(預設 <web 輸出目錄>/variants.json),"
                         "以 web 檔名為 key 合併更新,供 viewer 的減面策略模式讀取")
    ap.add_argument("--keep-interior", action="store_true", help="不刪除內部面(除錯用)")
    ap.add_argument("--reunwrap", action="store_true",
                    help="decimate 後重新 unwrap(smart_project + pack_islands)。"
                         "會使既有貼圖失效,僅供後續 bake 流程使用")
    args = ap.parse_args(script_args())

    if args.job_dir:
        args.input = args.input or args.job_dir / "model_raw.glb"
        args.output_high = args.output_high or args.job_dir / "model_high.glb"
        args.output_web = args.output_web or args.job_dir / "model.glb"
    if not (args.input and args.output_high and args.output_web):
        ap.error("需要 --job-dir,或同時給 --input / --output-high / --output-web")
    if not args.input.exists():
        ap.error(f"找不到輸入檔: {args.input}")

    args.variants = [s.strip() for s in args.variants.split(",") if s.strip()]
    unknown = [s for s in args.variants if s not in STRATEGIES]
    if unknown:
        ap.error(f"未知的減面策略: {', '.join(unknown)}(可用: {', '.join(STRATEGIES)})")
    try:
        args.variant_tris = [int(s) for s in args.variant_tris.split(",") if s.strip()]
    except ValueError:
        ap.error(f"--variant-tris 需為逗號分隔的整數: {args.variant_tris}")
    if args.variants and not args.variants_manifest:
        args.variants_manifest = args.output_web.parent / "variants.json"
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


def apply_decimate(obj: bpy.types.Object, strategy: str, args: argparse.Namespace,
                   target_tris: int | None = None) -> dict:
    """套用一種減面策略,回傳 {strategy, params, tris_before, tris_after}。

    collapse:邊塌縮到目標三角形數(target_tris 可覆寫),保 UV,面數可控。
    planar:合併夾角小於容差的共面區域,適合 hard-surface,面數不可直接控。
    unsubdiv:反細分,只對規則 quad 網格有效(如 remesh 過的模型)。
    """
    before = triangle_count(obj)
    mod = None
    if strategy == "collapse":
        target = target_tris or args.target_tris
        ratio = min(1.0, target / max(before, 1))
        params = {"target_tris": target, "ratio": round(ratio, 4)}
        if ratio < 1.0:
            mod = obj.modifiers.new("decimate", "DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = ratio
    elif strategy == "planar":
        params = {"angle_limit_deg": args.planar_angle}
        mod = obj.modifiers.new("decimate", "DECIMATE")
        mod.decimate_type = "DISSOLVE"
        mod.angle_limit = math.radians(args.planar_angle)
    elif strategy == "unsubdiv":
        params = {"iterations": args.unsubdiv_iterations}
        mod = obj.modifiers.new("decimate", "DECIMATE")
        mod.decimate_type = "UNSUBDIV"
        mod.iterations = args.unsubdiv_iterations
    else:
        raise ValueError(f"未知策略: {strategy}")
    if mod is not None:
        select_only([obj])
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return {
        "strategy": strategy,
        "params": params,
        "tris_before": before,
        "tris_after": triangle_count(obj),
    }


def fmt_tris(n: int) -> str:
    return f"{n // 1000}k" if n % 1000 == 0 else str(n)


def variant_jobs(args: argparse.Namespace) -> list[dict]:
    """展開變體工作清單:collapse 依 --variant-tris 每個目標一檔,其餘策略各一檔。

    slug 進檔名(<web 檔名>__<slug>.glb),label 給 viewer 的切換按鈕顯示。
    """
    jobs: list[dict] = []
    for strategy in args.variants:
        if strategy == "collapse":
            targets = args.variant_tris or [args.target_tris]
            multi = len(targets) > 1
            for t in targets:
                jobs.append({"strategy": strategy, "target_tris": t,
                             "slug": f"collapse-{fmt_tris(t)}" if multi else "collapse",
                             "label": f"collapse {fmt_tris(t)}"})
        elif strategy == "planar":
            jobs.append({"strategy": strategy, "target_tris": None, "slug": "planar",
                         "label": f"planar {args.planar_angle:g}°"})
        else:
            jobs.append({"strategy": strategy, "target_tris": None, "slug": "unsubdiv",
                         "label": f"unsubdiv ×{args.unsubdiv_iterations}"})
    return jobs


def export_variants(obj: bpy.types.Object, base_mesh: bpy.types.Mesh,
                    args: argparse.Namespace) -> list[dict]:
    """每個變體從修整後高模(base_mesh)各自減面並匯出獨立 GLB。"""
    variants: list[dict] = []
    for job in variant_jobs(args):
        obj.data = base_mesh.copy()
        v = apply_decimate(obj, job["strategy"], args, target_tris=job["target_tris"])
        v["label"] = job["label"]
        path = args.output_web.with_name(f"{args.output_web.stem}__{job['slug']}.glb")
        export_glb(str(path))
        v["file"] = path.name
        v["bytes"] = path.stat().st_size
        variants.append(v)
        print(f"[cleanup] 變體 {job['label']}: {v['tris_before']} → {v['tris_after']} tris → {path}")
    return variants


def update_variants_manifest(args: argparse.Namespace, variants: list[dict]) -> None:
    """以 web 檔名為 key 合併寫入 manifest,viewer 的減面策略模式讀這份。"""
    path = args.variants_manifest
    manifest = json.loads(path.read_text()) if path.exists() else {}
    manifest[args.output_web.stem] = {
        "source": args.input.name,
        "target_tris": args.target_tris,
        "variants": variants,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"[cleanup] manifest 已更新 → {path}")


def reunwrap(obj: bpy.types.Object) -> None:
    """重新 unwrap(給 bake 用的乾淨 UV):smart_project 66° + pack_islands。"""
    select_only([obj])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.003)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")


# texel density 的變異係數(std/mean)超過此值視為 UV 品質異常
UV_DENSITY_CV_WARN = 1.0


def uv_quality(obj: bpy.types.Object) -> dict | None:
    """UV 品質量測:每面「UV 面積 / 3D 面積」的均勻度(texel density)。

    回傳 density_cv(變異係數,0=完全均勻)與 uv_coverage(UV 總面積,
    1.0 = 佔滿 0~1 空間;>1 表示有重疊或重複利用)。無 UV 回傳 None。
    """
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        bm.free()
        return None

    ratios: list[tuple[float, float]] = []  # (UV/3D 面積比, 3D 面積權重)
    uv_total = 0.0
    for face in bm.faces:
        area3d = face.calc_area()
        uvs = [loop[uv_layer].uv for loop in face.loops]
        area_uv = 0.5 * abs(sum(
            uvs[i].x * uvs[(i + 1) % len(uvs)].y - uvs[(i + 1) % len(uvs)].x * uvs[i].y
            for i in range(len(uvs))
        ))
        uv_total += area_uv
        if area3d > 1e-12:
            ratios.append((area_uv / area3d, area3d))
    bm.free()
    if not ratios:
        return None

    weight_sum = sum(w for _, w in ratios)
    mean = sum(r * w for r, w in ratios) / weight_sum
    if mean <= 0:
        return {"density_cv": None, "uv_coverage": round(uv_total, 4), "warning": True}
    var = sum(w * (r - mean) ** 2 for r, w in ratios) / weight_sum
    cv = (var ** 0.5) / mean
    return {
        "density_cv": round(cv, 3),
        "uv_coverage": round(uv_total, 4),
        "warning": cv > UV_DENSITY_CV_WARN,
    }


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

    # 變體需要從「修整後、未減面」的網格各自出發,先留一份快照
    base_mesh = obj.data.copy() if args.variants else None

    dec = apply_decimate(obj, args.strategy, args)
    tris_web = dec["tris_after"]
    # collapse 有明確 ratio;planar / unsubdiv 以實際減後面數比回報
    ratio = dec["params"].get("ratio", round(tris_web / max(dec["tris_before"], 1), 4))
    if args.reunwrap:
        reunwrap(obj)
        print("[cleanup] 已重新 unwrap(既有貼圖將對不上新 UV,需後續 bake)")
    uv_stats = uv_quality(obj)
    if uv_stats and uv_stats["warning"]:
        print(f"[cleanup] 警告: UV 品質異常 (density_cv={uv_stats['density_cv']})")
    args.output_web.parent.mkdir(parents=True, exist_ok=True)
    export_glb(str(args.output_web))
    print(f"[cleanup] Web 版 {tris_web} tris (ratio={ratio:.4f}) → {args.output_web}")

    variants = export_variants(obj, base_mesh, args) if base_mesh else []
    if variants:
        update_variants_manifest(args, variants)

    stats = {
        "blender_version": bpy.app.version_string,
        "tris_raw": tris_raw,
        "tris_high": tris_high,
        "tris_web": tris_web,
        "target_tris": args.target_tris,
        "strategy": args.strategy,
        "decimate_ratio": round(ratio, 4),
        "variants": variants,
        **repair_stats,
        "reunwrapped": args.reunwrap,
        "uv": uv_stats,
        "high_glb_bytes": args.output_high.stat().st_size,
        "web_glb_bytes": args.output_web.stat().st_size,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    write_metadata(args.job_dir, stats)
    print(f"[cleanup] 完成 ({stats['elapsed_sec']}s): {json.dumps(stats, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
