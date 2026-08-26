"""Phase 2 Step 2-5: 攝影棚渲染(Cycles + shadow catcher)。

跑在 Blender 內(建議經 scripts/render_model.py 呼叫,會自動轉 WebP):

    uv run scripts/run_blender.py render -- --job-dir output/<job_id>
    uv run scripts/run_blender.py render -- --input model.glb --output out.png

流程:匯入高模 → 程式化打光(setup_lighting)→ 自動取景(setup_camera)
→ shadow catcher 地板 + 透明底片 → Cycles(Metal GPU,失敗退 CPU)
→ 輸出帶 alpha 的 PNG。統計寫進 metadata.json(render 欄位)。
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _util import import_glb, reset_scene, script_args
from setup_camera import frame_camera, world_bounds
from setup_lighting import build_lighting


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-dir", type=Path, help="output/<job_id>,輸入預設 model_high.glb")
    ap.add_argument("--input", type=Path, help="輸入 GLB(預設 <job-dir>/model_high.glb)")
    ap.add_argument("--output", type=Path, help="輸出 PNG(預設 <job-dir>/preview.png)")
    ap.add_argument("--resolution", type=int, default=1600)
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--azimuth", type=float, default=30.0)
    ap.add_argument("--elevation", type=float, default=18.0)
    ap.add_argument("--light-rotation", type=float, default=0.0,
                    help="整組光源(含 HDRI)繞 Z 軸旋轉角度,PBR 品質評估用")
    args = ap.parse_args(script_args())

    if args.job_dir:
        args.input = args.input or args.job_dir / "model_high.glb"
        args.output = args.output or args.job_dir / "preview.png"
    if not (args.input and args.output):
        ap.error("需要 --job-dir,或同時給 --input / --output")
    if not args.input.exists():
        ap.error(f"找不到輸入檔: {args.input}")
    return args


def enable_gpu() -> str:
    """啟用 Metal GPU 渲染,失敗退回 CPU。回傳實際裝置。"""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        bpy.context.scene.cycles.device = "GPU"
        return "METAL"
    except Exception as exc:  # noqa: BLE001 - 任何失敗都退 CPU
        print(f"[render] Metal GPU 啟用失敗({exc}),改用 CPU")
        bpy.context.scene.cycles.device = "CPU"
        return "CPU"


def add_shadow_catcher(floor_z: float) -> None:
    """透明底片下仍能接住模型陰影的地板。"""
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0.0, 0.0, floor_z))
    floor = bpy.context.active_object
    floor.name = "ShadowCatcher"
    floor.is_shadow_catcher = True


def main() -> None:
    args = parse_args()
    t0 = time.time()

    reset_scene()
    meshes = import_glb(str(args.input))
    if not meshes:
        sys.exit(f"GLB 內沒有 mesh: {args.input}")

    lo, _hi = world_bounds(meshes)
    add_shadow_catcher(floor_z=lo.z)
    light_stats = build_lighting(azimuth_offset=args.light_rotation)
    frame_camera(meshes, azimuth=args.azimuth, elevation=args.elevation)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    device = enable_gpu()
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True  # 透明背景,WebP 階段再合成白底
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.output)

    bpy.ops.render.render(write_still=True)

    stats = {
        "engine": "CYCLES",
        "device": device,
        "samples": args.samples,
        "resolution": args.resolution,
        "azimuth": args.azimuth,
        "elevation": args.elevation,
        **light_stats,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    if args.job_dir:
        meta_path = args.job_dir / "metadata.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        meta["render"] = stats
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[render] 完成 ({stats['elapsed_sec']}s, {device}): {args.output}")


if __name__ == "__main__":
    main()
