"""Phase 2 Step 2-6: 單一指令 pipeline — 圖片 → Web 模型 + 商品圖。

    uv run scripts/pipeline.py test-assets/hard-surface/vintage-radio/front.png
    uv run scripts/pipeline.py --job-dir output/<job_id> --skip-generate   # 重跑後段,省 API 額度

流程:generate(Tripo)→ cleanup(修整 + decimate)→ material(PBR 檢查)
→ render(Cycles 商品圖 + WebP)。
每步輸入輸出都是檔案、可單獨重跑;各階段狀態與耗時記進 metadata.json 的 stages。
"""

import argparse
import json
import sys
import time
from pathlib import Path

from generate_model import generate
from render_model import render_job
from run_blender import run as run_blender


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


def blender_stage(script: str, job_dir: Path):
    def _run():
        rc = run_blender(script, ["--job-dir", str(job_dir)])
        if rc != 0:
            raise RuntimeError(f"{script} exit code {rc}")
    return _run


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path, nargs="?", help="輸入圖片(--skip-generate 時免)")
    ap.add_argument("--job-dir", type=Path, help="既有 job(搭配 --skip-generate)")
    ap.add_argument("--skip-generate", action="store_true", help="用既有 model_raw.glb 重跑後段")
    ap.add_argument("--no-pbr", action="store_true")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--resolution", type=int, default=1600)
    args = ap.parse_args()

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
        job_dir = generate(args.image, pbr=not args.no_pbr)
        update_stages(job_dir, {"name": "generate", "status": "ok",
                                "elapsed_sec": round(time.time() - t0, 1)})

    run_stage(job_dir, "cleanup", blender_stage("cleanup_model", job_dir))
    run_stage(job_dir, "material", blender_stage("setup_material", job_dir))
    run_stage(job_dir, "render",
              lambda: render_job(job_dir, samples=args.samples, resolution=args.resolution))

    total = round(time.time() - t0, 1)
    print(f"\n[pipeline] 全部完成 ({total}s) → {job_dir}/")
    for f in sorted(job_dir.iterdir()):
        print(f"  {f.name}  {f.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
