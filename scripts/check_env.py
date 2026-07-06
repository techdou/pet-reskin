#!/usr/bin/env python3
"""check_env.py — Preflight checks for pet-reskin."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


def check(target: Path | None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("python>=3.8", sys.version_info >= (3, 8), sys.version.split()[0])
    add("pillow", importlib.util.find_spec("PIL") is not None, "pip install Pillow")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    add("GEMINI_API_KEY", bool(key), "set GEMINI_API_KEY or GOOGLE_API_KEY")
    add("GEMINI_IMAGE_MODEL", True, os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image"))

    if target is not None:
        add("target exists", target.exists(), str(target))
        add("target pet.config.js", (target / "pet.config.js").exists(), str(target / "pet.config.js"))
        add("target assets/pet", (target / "assets" / "pet").exists(), str(target / "assets" / "pet"))
    ok = all(item["ok"] for item in checks)
    return {"ok": ok, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pet-reskin environment checks")
    parser.add_argument("--target", type=Path, help="canvas-pet project root")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()
    report = check(args.target)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            mark = "OK" if item["ok"] else "FAIL"
            print(f"[{mark}] {item['name']}: {item['detail']}")
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
