#!/usr/bin/env python3
"""check_env.py — Preflight checks for pet-reskin."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _probe_api(key: str, model_id: str) -> tuple[bool, str]:
    """轻量探测 API：用 models 查询端点验证 key 是否有效。

    这不调用图像生成（避免费用），只验证 key 能否通过鉴权。
    返回 (ok, detail)。
    """
    try:
        req = urllib.request.Request(
            f"{API_BASE}?key={key}&pageSize=1",
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 401, 403):
            return False, f"key rejected (HTTP {exc.code})"
        # 404/其他通常是模型/端点问题，key 本身可能有效，不阻断但要提示
        return True, f"API reachable, non-auth warning HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"network error: {exc.reason}"
    except Exception as exc:
        return False, f"probe failed: {exc}"


def check(target: Path | None, probe: bool = False) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    info: List[Dict[str, Any]] = []  # 提示性信息，不影响 ok 判定

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    def add_info(name: str, detail: str) -> None:
        info.append({"name": name, "detail": detail})

    add("python>=3.8", sys.version_info >= (3, 8), sys.version.split()[0])
    add("pillow", importlib.util.find_spec("PIL") is not None, "pip install Pillow")
    add("numpy", importlib.util.find_spec("numpy") is not None, "pip install numpy")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    add("GEMINI_API_KEY", bool(key), "set GEMINI_API_KEY or GOOGLE_API_KEY")

    # GEMINI_IMAGE_MODEL 是提示性信息（可选覆盖），不参与 ok 判定
    add_info("GEMINI_IMAGE_MODEL", os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image (default)"))

    if target is not None:
        add("target exists", target.exists(), str(target))
        add("target pet.config.js", (target / "pet.config.js").exists(), str(target / "pet.config.js"))
        add("target assets/pet", (target / "assets" / "pet").exists(), str(target / "assets" / "pet"))

    # 可选：探测 key 是否被 API 接受，提前暴露 401/403，避免生成中途失败。
    if probe and key:
        model_id = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image")
        ok, detail = _probe_api(key, model_id)
        add("API key valid", ok, detail)

    ok = all(item["ok"] for item in checks)
    return {"ok": ok, "checks": checks, "info": info}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pet-reskin environment checks")
    parser.add_argument("--target", type=Path, help="canvas-pet project root")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--probe", action="store_true", help="Probe API key validity (network call)")
    args = parser.parse_args()
    report = check(args.target, probe=args.probe)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            mark = "OK" if item["ok"] else "FAIL"
            print(f"[{mark}] {item['name']}: {item['detail']}")
        for item in report.get("info", []):
            print(f"[INFO] {item['name']}: {item['detail']}")
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
