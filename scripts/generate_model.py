"""Phase 1 Step 1-2: 圖片 → Tripo API → output/<job_id>/model_raw.glb

用法:
    uv run scripts/generate_model.py test-assets/organic/coral-mound/front.png
    uv run scripts/generate_model.py <image> --no-pbr        # 只要幾何不要 PBR 貼圖
    uv run scripts/generate_model.py --check-balance          # 只驗證金鑰與餘額(零成本)
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

load_dotenv()
BASE = "https://api.tripo3d.ai/v2/openapi"
POLL_INTERVAL = 5      # 秒
POLL_TIMEOUT = 600     # 秒

TERMINAL_FAIL = {"failed", "cancelled", "banned", "expired"}


def _headers() -> dict:
    key = os.getenv("TRIPO_API_KEY")
    if not key:
        sys.exit("錯誤:.env 缺少 TRIPO_API_KEY")
    return {"Authorization": f"Bearer {key}"}


def _request(method: str, url: str, **kw) -> dict:
    r = requests.request(method, url, headers=_headers(), timeout=kw.pop("timeout", 60), **kw)
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:500]}
    if r.status_code != 200 or body.get("code", 0) != 0:
        sys.exit(f"API 錯誤 {method} {url}\nHTTP {r.status_code}: {json.dumps(body, ensure_ascii=False, indent=2)}")
    return body["data"]


def check_balance() -> None:
    data = _request("GET", f"{BASE}/user/balance")
    print(f"金鑰有效。餘額: {json.dumps(data, ensure_ascii=False)}")


def upload_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        data = _request(
            "POST", f"{BASE}/upload/sts",
            files={"file": (image_path.name, f)},
            timeout=120,
        )
    token = data.get("image_token") or data.get("file_token") or data.get("token")
    if not token:
        sys.exit(f"上傳成功但找不到 token,response: {data}")
    return token


def create_task(image_path: Path, token: str, pbr: bool) -> str:
    suffix = image_path.suffix.lstrip(".").lower().replace("jpg", "jpeg")
    payload = {
        "type": "image_to_model",
        "file": {"type": suffix, "file_token": token},
        "texture": True,
        "pbr": pbr,
    }
    data = _request("POST", f"{BASE}/task", json=payload)
    return data["task_id"]


def poll_task(task_id: str) -> dict:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        data = _request("GET", f"{BASE}/task/{task_id}")
        status = data.get("status")
        print(f"  status={status} progress={data.get('progress')}%", flush=True)
        if status == "success":
            return data
        if status in TERMINAL_FAIL:
            sys.exit(f"任務 {task_id} 結束於 {status}: {json.dumps(data, ensure_ascii=False)}")
        time.sleep(POLL_INTERVAL)
    sys.exit(f"任務 {task_id} 超過 {POLL_TIMEOUT}s 未完成")


def pick_model_url(output: dict) -> tuple[str, str]:
    """回傳 (欄位名, url),優先 PBR 模型"""
    for key in ("pbr_model", "model", "base_model", "model_url"):
        url = output.get(key)
        if isinstance(url, dict):
            url = url.get("url")
        if url:
            return key, url
    sys.exit(f"任務成功但 output 中找不到模型 URL: {json.dumps(output, ensure_ascii=False, indent=2)}")


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    dest.write_bytes(r.content)


def generate(image: Path, pbr: bool = True, job_dir: Path | None = None) -> Path:
    """圖片 → Tripo → output/<job_id>/(model_raw.glb + source + metadata)。回傳 job dir。

    job_dir:pipeline 先建好的 job 目錄(preprocess stage 已寫入 input/ 與 metadata);
    未指定則自建 output/<uuid>/。既有 metadata.json 會合併而非覆蓋。
    """
    out_dir = job_dir if job_dir is not None else Path("output") / uuid.uuid4().hex[:12]
    job_id = out_dir.name
    t0 = time.time()

    print(f"[{job_id}] 上傳 {image} ...")
    token = upload_image(image)
    print(f"[{job_id}] 建立任務 ...")
    task_id = create_task(image, token, pbr=pbr)
    print(f"[{job_id}] task_id={task_id},輪詢中 ...")
    result = poll_task(task_id)

    output = result.get("output", {})
    field, model_url = pick_model_url(output)
    dest = out_dir / "model_raw.glb"
    print(f"[{job_id}] 下載 {field} → {dest}")
    download(model_url, dest)
    shutil.copy(image, out_dir / f"source{image.suffix.lower()}")

    meta = {
        "job_id": job_id,
        "source_image": str(image),
        "source_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "provider": "tripo",
        "task_id": task_id,
        "model_field": field,
        "output_keys": list(output.keys()),
        "elapsed_sec": round(time.time() - t0, 1),
        "glb_bytes": dest.stat().st_size,
    }
    meta_path = out_dir / "metadata.json"
    existing = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    existing.update(meta)
    meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    print(f"[{job_id}] 完成 ({meta['elapsed_sec']}s, {meta['glb_bytes']/1e6:.1f} MB) → {out_dir}/")
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path, nargs="?")
    ap.add_argument("--no-pbr", action="store_true", help="不要求 PBR 貼圖")
    ap.add_argument("--check-balance", action="store_true", help="只驗證金鑰與餘額")
    args = ap.parse_args()

    if args.check_balance:
        check_balance()
        return
    if not args.image:
        ap.error("需要圖片路徑(或用 --check-balance)")
    if not args.image.exists():
        sys.exit(f"找不到圖片: {args.image}")

    generate(args.image, pbr=not args.no_pbr)


if __name__ == "__main__":
    main()
