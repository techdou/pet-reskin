#!/usr/bin/env python3
"""
apply_config.py — Install generated sprites into a pet project (thin dispatcher).

This is now a thin wrapper over installers/ package. It auto-detects the target
type (canvas_pet with pet.config.js, or multi_skin with pet.js skins array) and
dispatches to the appropriate installer.

Backward compatibility: the CLI interface is unchanged. Old canvas-pet projects
still work exactly as before; new multi-skin projects are now also supported.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# 让 scripts/ 目录下的子包（installers/、providers/、background_removal.py）可 import
sys.path.insert(0, str(Path(__file__).parent))

from installers import install, detect_target_type  # noqa: E402

# 向后兼容：老测试直接调用 apply_config.validate_manifest / update_config_text 等。
# 这些函数现在在 canvas_pet.py 里（私有带下划线），这里 re-export 保持 import 路径不变。
from installers.canvas_pet import (  # noqa: E402, F401
    install_canvas_pet,
    _validate_manifest as _validate_manifest_impl,
    _update_config_text as _update_config_text_impl,
    _parse_existing_frames as _parse_existing_frames_impl,
    _extract_frames_body as _extract_frames_body_impl,
    _find_balanced as _find_balanced_impl,
    _copy_sprites as _copy_sprites_impl,
)


def validate_manifest(manifest, allow_partial=False):
    return _validate_manifest_impl(manifest, allow_partial=allow_partial)


def update_config_text(text, manifest, plan):
    return _update_config_text_impl(text, manifest, plan)


def parse_existing_frames(text):
    return _parse_existing_frames_impl(text)


def extract_frames_body(text):
    return _extract_frames_body_impl(text)


def find_balanced(text, open_ch, close_ch, kw_pattern, label):
    return _find_balanced_impl(text, open_ch, close_ch, kw_pattern, label)


def copy_sprites(manifest, sprites_dir, assets_pet, dry_run=False):
    return _copy_sprites_impl(manifest, sprites_dir, assets_pet, dry_run=dry_run)


# run() 函数老测试也直接用（run(manifest, sprites, target, allow_partial, dry_run, no_backup)）
# 保持原签名向后兼容


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON: {path}: {exc}") from exc


def run(manifest_path: Path, sprites_dir: Path, target: Path, allow_partial: bool, dry_run: bool, no_backup: bool, target_type: str | None = None) -> int:
    manifest = load_json(manifest_path)

    plan_path = sprites_dir / "plan.json"
    plan = load_json(plan_path) if plan_path.exists() else {}

    # 探测或使用显式指定的 target 类型
    if target_type is None:
        target_type = detect_target_type(target)
        if target_type == "unknown":
            print(
                f"ERROR: 无法识别 target 类型: {target}\n"
                f"期望找到 pet.config.js（canvas-pet）或含 skins 数组的 pet.js（multi-skin）。",
                file=sys.stderr,
            )
            return 1

    try:
        summary = install(
            manifest=manifest,
            sprites_dir=sprites_dir,
            target=target,
            target_type=target_type,
            plan=plan,
            allow_partial=allow_partial,
            dry_run=dry_run,
            no_backup=no_backup,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not summary.get("ok"):
        for error in summary.get("errors", []):
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Install generated sprites into a pet project (auto-detects canvas-pet or multi-skin)")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--sprites", required=True, type=Path, help="Directory containing generated PNGs and plan.json")
    parser.add_argument("--target", required=True, type=Path, help="pet project root (canvas-pet or multi-skin)")
    parser.add_argument("--allow-partial", action="store_true", help="Allow installing a partial manifest")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print summary without writing files")
    parser.add_argument("--no-backup", action="store_true", help="Do not create config.js.bak")
    parser.add_argument("--target-type", choices=["canvas_pet", "multi_skin"], help="Force target type (auto-detected by default)")
    args = parser.parse_args()
    raise SystemExit(run(args.manifest, args.sprites, args.target, args.allow_partial, args.dry_run, args.no_backup, args.target_type))


if __name__ == "__main__":
    main()
