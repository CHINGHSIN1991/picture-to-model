"""Phase 2 Step 2-6: 單一指令 pipeline — 圖片 → Web 模型 + poster。

    uv run scripts/pipeline.py test-assets/hard-surface/vintage-radio/front.png
    uv run scripts/pipeline.py --job-dir output/<job_id> --skip-generate   # 重跑後段,省 API 額度
    uv run scripts/pipeline.py <image> --skip-preprocess --skip-optimize   # 對照 / 除錯

七段流程:preprocess(去背 / 置中 / 佔比 / 解析度 fail fast)→ generate(Tripo)
→ cleanup(修整 + decimate)→ material(PBR 檢查)→ textures(拆 ORM + 驗證)
→ optimize(gltf-transform meshopt|draco + WebP → web/model.glb)→ render(Cycles poster + WebP)。
每步輸入輸出都是檔案、可單獨重跑;各階段狀態與耗時記進 metadata.json 的 stages。
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

from extract_textures import extract_textures
from generate_model import generate
from optimize_glb import COMPRESSORS, optimize_job
from preprocess_image import MIN_RESOLUTION, TARGET_RATIO, preprocess
from render_model import render_job
from run_blender import run as run_blender
from validate_textures import validate

# 與 scripts/blender/cleanup_model.py 的 STRATEGIES 同步(該檔 import bpy,無法在 venv 匯入)
STRATEGIES = ("collapse", "planar", "unsubdiv")


def update_stages(job_dir: Path, stage: dict) -> None:
    meta_path = job_dir / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    stages = [s for s in meta.get("stages", []) if s["name"] != stage["name"]]
    meta["stages"] = stages + [stage]
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))


def run_stage(job_dir: Path, name: str, fn) -> None:
    """執行一個階段,記錄狀態與耗時;失敗即中止(fail fast)。"""
    print(f"\n=== [{name}] 開始 ===")
    t0 = time.time()
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - 記錄後中止
        update_stages(job_dir, {"name": name, "status": "failed", "error": str(exc),
                                "elapsed_sec": round(time.time() - t0, 1)})
        sys.exit(f"[pipeline] 階段 {name} 失敗: {exc}")
    update_stages(job_dir, {"name": name, "status": "ok",
                            "elapsed_sec": round(time.time() - t0, 1)})


def blender_stage(script: str, job_dir: Path, extra_args: list[str] | None = None,
                  timeout: int | None = None):
    def _run():
        kwargs = {"timeout": timeout} if timeout else {}
        rc = run_blender(script, ["--job-dir", str(job_dir), *(extra_args or [])], **kwargs)
        if rc != 0:
            raise RuntimeError(f"{script} exit code {rc}")
    return _run


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path, nargs="?", help="輸入圖片(--skip-generate 時免)")
    ap.add_argument("--job-dir", type=Path, help="既有 job(搭配 --skip-generate)")
    ap.add_argument("--skip-generate", action="store_true", help="用既有 model_raw.glb 重跑後段")
    ap.add_argument("--no-pbr", action="store_true")
    ap.add_argument("--skip-preprocess", action="store_true", help="跳過品質前處理(對照 / 除錯用)")
    ap.add_argument("--min-resolution", type=int, default=MIN_RESOLUTION, help="輸入解析度下限,低於即 fail fast")
    ap.add_argument("--target-ratio", type=float, default=TARGET_RATIO, help="主體佔比目標(0.70~0.80)")
    ap.add_argument("--no-remove-bg", action="store_true", help="前處理不去背")
    ap.add_argument("--skip-optimize", action="store_true", help="跳過 GLB 壓縮")
    ap.add_argument("--compress", choices=COMPRESSORS, default="meshopt",
                    help="optimize 幾何壓縮器(meshopt 預設;draco 需 viewer 掛 DRACOLoader)")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--resolution", type=int, default=1600)
    ap.add_argument("--strategy", choices=STRATEGIES,
                    help="cleanup 的減面策略(預設 collapse)")
    ap.add_argument("--variants", type=str,
                    help="cleanup 額外輸出的減面策略變體,逗號分隔(如 collapse,planar)")
    ap.add_argument("--variant-tris", type=str,
                    help="collapse 變體的目標面數清單,逗號分隔(如 10000,30000,60000)")
    ap.add_argument("--blender-timeout", type=int,
                    help="Blender 階段逾時秒數(預設 1800;多變體 cleanup 可能需要調高)")
    args = ap.parse_args()

    # cleanup_model 內也會驗證,但那時付費的 generate 階段已經跑完;typo 在這裡先擋下
    if args.variants:
        unknown = [s for s in args.variants.split(",") if s.strip() and s.strip() not in STRATEGIES]
        if unknown:
            ap.error(f"未知的減面策略: {', '.join(unknown)}(可用: {', '.join(STRATEGIES)})")
    if args.variant_tris:
        try:
            tris = [int(s) for s in args.variant_tris.split(",") if s.strip()]
        except ValueError:
            ap.error(f"--variant-tris 需為逗號分隔的整數: {args.variant_tris}")
        if any(t <= 0 for t in tris):
            ap.error("--variant-tris 需為正整數")

    t0 = time.time()
    if args.skip_generate:
        if not args.job_dir:
            ap.error("--skip-generate 需要 --job-dir")
        job_dir = args.job_dir
        if not (job_dir / "model_raw.glb").exists():
            sys.exit(f"找不到 {job_dir}/model_raw.glb")
    else:
        if not args.image or not args.image.exists():
            ap.error("需要有效的輸入圖片(或 --skip-generate + --job-dir)")
        job_dir = args.job_dir or Path("output") / uuid.uuid4().hex[:12]
        job_dir.mkdir(parents=True, exist_ok=True)
        gen_input = {"image": args.image}

        def preprocess_stage() -> None:
            meta = preprocess(args.image, job_dir, min_resolution=args.min_resolution,
                              target_ratio=args.target_ratio, remove_bg=not args.no_remove_bg)
            gen_input["image"] = job_dir / meta["output"]

        if args.skip_preprocess:
            update_stages(job_dir, {"name": "preprocess", "status": "skipped", "elapsed_sec": 0})
        else:
            run_stage(job_dir, "preprocess", preprocess_stage)
        run_stage(job_dir, "generate", lambda: generate(gen_input["image"], pbr=not args.no_pbr, job_dir=job_dir))

    def textures_stage() -> None:
        extract_textures(job_dir)
        result = validate(job_dir)
        if not result["ok"]:
            raise RuntimeError("; ".join(result["errors"]))

    cleanup_args: list[str] = []
    if args.strategy:
        cleanup_args += ["--strategy", args.strategy]
    if args.variants:
        cleanup_args += ["--variants", args.variants]
    if args.variant_tris:
        cleanup_args += ["--variant-tris", args.variant_tris]
    run_stage(job_dir, "cleanup", blender_stage("cleanup_model", job_dir, cleanup_args,
                                                timeout=args.blender_timeout))
    run_stage(job_dir, "material", blender_stage("setup_material", job_dir,
                                                 timeout=args.blender_timeout))
    run_stage(job_dir, "textures", textures_stage)
    if args.skip_optimize:
        update_stages(job_dir, {"name": "optimize", "status": "skipped", "elapsed_sec": 0})
    else:
        run_stage(job_dir, "optimize", lambda: optimize_job(job_dir, compress=args.compress))
    run_stage(job_dir, "render",
              lambda: render_job(job_dir, samples=args.samples, resolution=args.resolution))

    total = round(time.time() - t0, 1)
    print(f"\n[pipeline] 全部完成 ({total}s) → {job_dir}/")
    for f in sorted(job_dir.iterdir()):
        print(f"  {f.name}  {f.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
