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

    # image2-api skill 可用性（provider=image2api 时需要）
    image2api_root = None
    for candidate in [
        Path.home() / ".agents" / "skills" / "image2-api",
        Path.home() / ".zcode" / "skills" / "image2-api",
    ]:
        if (candidate / "scripts" / "image2lib" / "__init__.py").exists():
            image2api_root = candidate
            break
    if image2api_root:
        add_info("image2-api skill", f"found at {image2api_root} (provider=image2api 可用)")
    elif os.environ.get("IMAGE2_API_ROOT"):
        root = Path(os.environ["IMAGE2_API_ROOT"])
        if (root / "scripts" / "image2lib" / "__init__.py").exists():
            add_info("image2-api skill", f"found via IMAGE2_API_ROOT at {root}")
        else:
            add_info("image2-api skill", "IMAGE2_API_ROOT set but image2lib not found there")
    else:
        add_info("image2-api skill", "not found (provider=image2api 不可用，将走 gemini 默认)")

    if target is not None:
        add("target exists", target.exists(), str(target))
        # 探测 target 类型：canvas-pet（pet.config.js）或 multi-skin（pet.js skins 数组）
        config_js = target / "pet.config.js"
        pet_js = target / "pet.js"
        has_config_js = config_js.exists()
        has_pet_js_skins = False
        if pet_js.exists():
            try:
                text = pet_js.read_text(encoding="utf-8")
                has_pet_js_skins = "skins" in text and ("PET_CONFIG" in text or "skins:" in text)
            except Exception:
                pass

        if has_config_js:
            add("target type", True, "canvas_pet (pet.config.js)")
            add("target pet.config.js", True, str(config_js))
            add("target assets/pet", (target / "assets" / "pet").exists(), str(target / "assets" / "pet"))
        elif has_pet_js_skins:
            add("target type", True, "multi_skin (pet.js skins array)")
            add("target pet.js", True, str(pet_js))
        else:
            add("target type", False, "unknown — 既无 pet.config.js 也无含 skins 的 pet.js")

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
