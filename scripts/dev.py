"""Start the local API, durable worker and Vite; terminate them together on Ctrl+C."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import nullcontext, suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_services(api_port: int, web_port: int, data_dir: str | None) -> int:
    if not shutil.which("npm"):
        print("npm is required. Install Node.js, then run npm ci --prefix web.", file=sys.stderr)
        return 1
    if not (ROOT / "web/node_modules").is_dir():
        print("Run npm ci --prefix web first.", file=sys.stderr)
        return 1

    environment = os.environ.copy()
    environment["PTM_API_TARGET"] = f"http://127.0.0.1:{api_port}"
    environment["PTM_WEB_ORIGIN"] = f"http://127.0.0.1:{web_port}"
    if data_dir:
        environment["PTM_DATA_DIR"] = data_dir
        environment["PTM_LOCAL_OWNER"] = "e2e-owner"
    commands = [
        (
            "API",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
            ROOT,
        ),
        ("worker", [sys.executable, "-m", "backend.app.worker"], ROOT),
        # --strictPort: a silent fallback port would break the API's Origin allowlist.
        ("web", ["npm", "run", "dev", "--", "--port", str(web_port), "--strictPort"], ROOT / "web"),
    ]
    processes: list[tuple[str, subprocess.Popen]] = []
    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    result = 0
    try:
        for name, command, cwd in commands:
            processes.append(
                (name, subprocess.Popen(command, cwd=cwd, env=environment, start_new_session=True))
            )
        print(
            f"\nPicture to Model → http://127.0.0.1:{web_port}  (Ctrl+C stops all services)\n",
            flush=True,
        )
        while not stopping:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"{name} exited ({code}); stopping other services.", file=sys.stderr)
                    result = code or 1
                    stopping = True
                    break
            time.sleep(0.2)
    finally:
        for _, process in processes:
            # npm may exit before its Vite child; clean up the entire group either way.
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
        for _, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=5173)
    parser.add_argument(
        "--temporary-data",
        action="store_true",
        help="Use isolated data and remove it on exit (for E2E tests).",
    )
    args = parser.parse_args()
    if not (1 <= args.api_port <= 65535 and 1 <= args.web_port <= 65535):
        parser.error("Ports must be between 1 and 65535.")
    if args.api_port == args.web_port:
        parser.error("API and web ports must differ.")
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    context = (
        tempfile.TemporaryDirectory(prefix="e2e-", dir=output)
        if args.temporary_data
        else nullcontext(None)
    )
    with context as data_dir:
        return run_services(args.api_port, args.web_port, data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
