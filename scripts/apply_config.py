#!/usr/bin/env python3
"""
apply_config.py — Install generated sprites into a canvas-pet project safely.

Default behavior is strict: all required core frames must be present before copying files or
rewriting pet.config.js. Optional frames such as `cloud` are only updated when present in the
manifest; otherwise existing optional entries in pet.config.js are preserved.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_REQUIRED_FRAMES = [
    "idle", "idleWink", "walkFront1", "walkFront2", "walkLeft", "walkRight", "walkBack", "sleep"
]
KNOWN_OPTIONAL_FRAMES = ["cloud"]


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON: {path}: {exc}") from exc


def required_frames_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    required = manifest.get("requiredFrames")
    if isinstance(required, list) and required:
        return [str(item) for item in required]
    return list(BASE_REQUIRED_FRAMES)


def optional_frames_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    optional = manifest.get("optionalFrames")
    if isinstance(optional, list):
        return [str(item) for item in optional]
    return list(KNOWN_OPTIONAL_FRAMES)


def validate_manifest(manifest: Dict[str, Any], allow_partial: bool) -> List[str]:
    errors: List[str] = []
    frames = manifest.get("frames")
    files = manifest.get("files")
    if not isinstance(frames, dict):
        errors.append("manifest.frames must be an object")
        frames = {}
    if not isinstance(files, list):
        errors.append("manifest.files must be a list")
    required = required_frames_from_manifest(manifest)
    missing = [frame for frame in required if frame not in frames]
    if missing and not allow_partial:
        errors.append("missing required frames: " + ", ".join(missing))
    return errors


def extract_frames_body(text: str) -> str:
    r"""提取 `frames: { ... }` 的花括号内部内容（不含外层括号）。

    用平衡括号扫描代替正则 `[\s\S]*?`，正确处理 frames 值里含 `}` 的字面量、
    嵌套对象、以及文件路径中的花括号。
    """
    start_match = re.search(r"frames\s*:\s*\{", text)
    if not start_match:
        raise RuntimeError("could not find frames block in pet.config.js")
    brace_start = start_match.end() - 1  # 指向 `{`
    depth = 0
    in_str: Optional[str] = None
    for i in range(brace_start, len(text)):
        ch = text[i]
        if in_str:
            if ch == "\\":
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"'):
                in_str = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[brace_start + 1:i]
    raise RuntimeError("unbalanced braces in frames block")


def parse_existing_frames(text: str) -> Dict[str, str]:
    body = extract_frames_body(text)
    frames: Dict[str, str] = {}
    # 只匹配简单字符串值 `key: 'value'` 或 `key: "value"`，忽略嵌套对象。
    for key, _, value in re.findall(r"\b([A-Za-z_]\w*)\s*:\s*(['\"])(.*?)\2", body):
        frames[key] = value
    return frames


def build_frames_block(
    existing_frames: Dict[str, str],
    manifest_frames: Dict[str, str],
    required_frames: List[str],
    optional_frames: List[str],
    indent: str = "  ",
) -> str:
    merged = dict(existing_frames)
    merged.update(manifest_frames)

    ordered_keys: List[str] = []
    for frame in required_frames:
        if frame in merged:
            ordered_keys.append(frame)
    for frame in optional_frames:
        if frame in merged and frame not in ordered_keys:
            ordered_keys.append(frame)
    for frame in merged:
        if frame not in ordered_keys:
            ordered_keys.append(frame)

    lines = ["frames: {"]
    for frame in ordered_keys:
        lines.append(f"{indent}  {frame}: {json.dumps(merged[frame], ensure_ascii=False)},")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def replace_once(text: str, pattern: str, replacement: str, label: str, flags: int = re.DOTALL) -> Tuple[str, bool]:
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"could not uniquely replace {label}; matches={count}")
    return new_text, True


def find_balanced(text: str, open_ch: str, close_ch: str, kw_pattern: str, label: str) -> Tuple[int, int]:
    r"""定位 `kw_pattern: open_ch ... close_ch`，返回 (关键字起始索引, 闭合符后一位)。

    用平衡扫描代替 `[\s\S]*?close_ch`，避免金句含 `]`、文件路径含 `}` 时误匹配。
    同时跳过字符串字面量内部的括号，避免引号内的 `]`/`}` 干扰计数。
    """
    start_match = re.search(kw_pattern + r"\s*:\s*" + re.escape(open_ch), text)
    if not start_match:
        raise RuntimeError(f"could not find {label} block")
    kw_start = start_match.start()
    bracket_start = start_match.end() - 1
    depth = 0
    i = bracket_start
    in_str: Optional[str] = None
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"'):
                in_str = ch
            elif ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return kw_start, i + 1
        i += 1
    raise RuntimeError(f"unbalanced {open_ch}{close_ch} in {label}")


def update_config_text(text: str, manifest: Dict[str, Any], plan: Dict[str, Any]) -> Tuple[str, List[str]]:
    warnings: List[str] = []
    required_frames = required_frames_from_manifest(manifest)
    optional_frames = optional_frames_from_manifest(manifest)
    existing_frames = parse_existing_frames(text)
    frames_block = build_frames_block(existing_frames, manifest["frames"], required_frames, optional_frames)

    # 用平衡括号扫描定位 frames 块的精确范围（kw_start 到 close 后一位），切片替换。
    # 同时吞掉块后紧跟的逗号/空白，由 build_frames_block 统一控制结尾标点。
    fb_start, fb_end = find_balanced(text, "{", "}", r"frames", "frames")
    while fb_end < len(text) and text[fb_end] in (",", " ", "\t", "\n", "\r"):
        fb_end += 1
    text = text[:fb_start] + frames_block + "\n" + text[fb_end:]

    quotes = manifest.get("quotes") if manifest.get("quotes") else plan.get("quotes")
    if quotes:
        if not isinstance(quotes, list):
            raise RuntimeError("quotes must be a list")
        qblock = "quotes: " + json.dumps(quotes, ensure_ascii=False)
        qb_start, qb_end = find_balanced(text, "[", "]", r"quotes", "quotes")
        text = text[:qb_start] + qblock + text[qb_end:]
    else:
        warnings.append("quotes not provided; existing quotes preserved")

    base_size = manifest.get("baseSize") if manifest.get("baseSize") is not None else plan.get("baseSize")
    if base_size is not None:
        bblock = f"baseSize: {int(base_size)}"
        text, _ = replace_once(text, r"baseSize\s*:\s*\d+", bblock, "baseSize", flags=0)
    else:
        warnings.append("baseSize not provided; existing baseSize preserved")
    return text, warnings


def copy_sprites(manifest: Dict[str, Any], sprites_dir: Path, assets_pet: Path, dry_run: bool) -> List[str]:
    copied: List[str] = []
    for fname in manifest.get("files", []):
        source = sprites_dir / fname
        if not source.exists():
            raise RuntimeError(f"sprite listed in manifest is missing: {source}")
        if not dry_run:
            shutil.copy2(source, assets_pet / fname)
        copied.append(fname)
    return copied


def run(manifest_path: Path, sprites_dir: Path, target: Path, allow_partial: bool, dry_run: bool, no_backup: bool) -> int:
    manifest = load_json(manifest_path)
    errors = validate_manifest(manifest, allow_partial=allow_partial)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    config_path = target / "pet.config.js"
    assets_pet = target / "assets" / "pet"
    if not target.exists():
        print(f"ERROR: target does not exist: {target}", file=sys.stderr)
        return 1
    if not config_path.exists():
        print(f"ERROR: target is missing pet.config.js: {config_path}", file=sys.stderr)
        return 1
    if not dry_run:
        assets_pet.mkdir(parents=True, exist_ok=True)

    plan_path = sprites_dir / "plan.json"
    plan = load_json(plan_path) if plan_path.exists() else {}

    try:
        copied = copy_sprites(manifest, sprites_dir, assets_pet, dry_run=dry_run)
        original = config_path.read_text(encoding="utf-8")
        updated, warnings = update_config_text(original, manifest, plan)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = {
        "ok": True,
        "dryRun": dry_run,
        "target": str(target),
        "copied": copied,
        "config": str(config_path),
        "warnings": warnings,
    }

    if dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if not no_backup:
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        shutil.copy2(config_path, backup_path)
        summary["backup"] = str(backup_path)
    config_path.write_text(updated, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Install generated sprites into a canvas-pet project")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--sprites", required=True, type=Path, help="Directory containing generated PNGs and plan.json")
    parser.add_argument("--target", required=True, type=Path, help="canvas-pet project root")
    parser.add_argument("--allow-partial", action="store_true", help="Allow installing a partial manifest")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print summary without writing files")
    parser.add_argument("--no-backup", action="store_true", help="Do not create pet.config.js.bak")
    args = parser.parse_args()
    raise SystemExit(run(args.manifest, args.sprites, args.target, args.allow_partial, args.dry_run, args.no_backup))


if __name__ == "__main__":
    main()
