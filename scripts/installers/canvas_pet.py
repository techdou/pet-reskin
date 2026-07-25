"""canvas-pet installer：单皮肤架构（pet.config.js + assets/pet/）。

全部逻辑从原 apply_config.py 平移而来，行为完全一致。apply_config.py 现在
改成薄封装，调用本模块的 install_canvas_pet。
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_REQUIRED_FRAMES = [
    "idle", "idleWink", "walkFront1", "walkFront2", "walkLeft", "walkRight", "walkBack", "sleep"
]
KNOWN_OPTIONAL_FRAMES = ["cloud"]


def _required_frames_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    required = manifest.get("requiredFrames")
    if isinstance(required, list) and required:
        return [str(item) for item in required]
    return list(BASE_REQUIRED_FRAMES)


def _optional_frames_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    optional = manifest.get("optionalFrames")
    if isinstance(optional, list):
        return [str(item) for item in optional]
    return list(KNOWN_OPTIONAL_FRAMES)


def _validate_manifest(manifest: Dict[str, Any], allow_partial: bool) -> List[str]:
    errors: List[str] = []
    frames = manifest.get("frames")
    files = manifest.get("files")
    if not isinstance(frames, dict):
        errors.append("manifest.frames must be an object")
        frames = {}
    if not isinstance(files, list):
        errors.append("manifest.files must be a list")
    required = _required_frames_from_manifest(manifest)
    missing = [frame for frame in required if frame not in frames]
    if missing and not allow_partial:
        errors.append("missing required frames: " + ", ".join(missing))
    return errors


def _extract_frames_body(text: str) -> str:
    start_match = re.search(r"frames\s*:\s*\{", text)
    if not start_match:
        raise RuntimeError("could not find frames block in pet.config.js")
    brace_start = start_match.end() - 1
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


def _parse_existing_frames(text: str) -> Dict[str, str]:
    body = _extract_frames_body(text)
    frames: Dict[str, str] = {}
    for key, _, value in re.findall(r"\b([A-Za-z_]\w*)\s*:\s*(['\"])(.*?)\2", body):
        frames[key] = value
    return frames


def _build_frames_block(
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


def _replace_once(text: str, pattern: str, replacement: str, label: str, flags: int = re.DOTALL) -> Tuple[str, bool]:
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"could not uniquely replace {label}; matches={count}")
    return new_text, True


def _find_balanced(text: str, open_ch: str, close_ch: str, kw_pattern: str, label: str) -> Tuple[int, int]:
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


def _update_config_text(text: str, manifest: Dict[str, Any], plan: Dict[str, Any]) -> Tuple[str, List[str]]:
    warnings: List[str] = []
    required_frames = _required_frames_from_manifest(manifest)
    optional_frames = _optional_frames_from_manifest(manifest)
    existing_frames = _parse_existing_frames(text)
    frames_block = _build_frames_block(existing_frames, manifest["frames"], required_frames, optional_frames)

    fb_start, fb_end = _find_balanced(text, "{", "}", r"frames", "frames")
    while fb_end < len(text) and text[fb_end] in (",", " ", "\t", "\n", "\r"):
        fb_end += 1
    text = text[:fb_start] + frames_block + "\n" + text[fb_end:]

    quotes = manifest.get("quotes") if manifest.get("quotes") else plan.get("quotes")
    if quotes:
        if not isinstance(quotes, list):
            raise RuntimeError("quotes must be a list")
        qblock = "quotes: " + json.dumps(quotes, ensure_ascii=False)
        qb_start, qb_end = _find_balanced(text, "[", "]", r"quotes", "quotes")
        text = text[:qb_start] + qblock + text[qb_end:]
    else:
        warnings.append("quotes not provided; existing quotes preserved")

    base_size = manifest.get("baseSize") if manifest.get("baseSize") is not None else plan.get("baseSize")
    if base_size is not None:
        bblock = f"baseSize: {int(base_size)}"
        text, _ = _replace_once(text, r"baseSize\s*:\s*\d+", bblock, "baseSize", flags=0)
    else:
        warnings.append("baseSize not provided; existing baseSize preserved")
    return text, warnings


def _copy_sprites(manifest: Dict[str, Any], sprites_dir: Path, assets_pet: Path, dry_run: bool) -> List[str]:
    copied: List[str] = []
    for fname in manifest.get("files", []):
        source = sprites_dir / fname
        if not source.exists():
            raise RuntimeError(f"sprite listed in manifest is missing: {source}")
        if not dry_run:
            shutil.copy2(source, assets_pet / fname)
        copied.append(fname)
    return copied


def install_canvas_pet(
    manifest: Dict[str, Any],
    sprites_dir: Path,
    target: Path,
    plan: Dict[str, Any],
    allow_partial: bool = False,
    dry_run: bool = False,
    no_backup: bool = False,
) -> Dict[str, Any]:
    """把生成的 sprite 安装到 canvas-pet 项目（改 pet.config.js + 拷图到 assets/pet/）。"""
    errors = _validate_manifest(manifest, allow_partial=allow_partial)
    if errors:
        return {"ok": False, "errors": errors}

    config_path = target / "pet.config.js"
    assets_pet = target / "assets" / "pet"
    if not target.exists():
        return {"ok": False, "errors": [f"target does not exist: {target}"]}
    if not config_path.exists():
        return {"ok": False, "errors": [f"target is missing pet.config.js: {config_path}"]}
    if not dry_run:
        assets_pet.mkdir(parents=True, exist_ok=True)

    try:
        copied = _copy_sprites(manifest, sprites_dir, assets_pet, dry_run=dry_run)
        original = config_path.read_text(encoding="utf-8")
        updated, warnings = _update_config_text(original, manifest, plan)
    except Exception as exc:
        return {"ok": False, "errors": [str(exc)]}

    summary: Dict[str, Any] = {
        "ok": True,
        "dryRun": dry_run,
        "targetType": "canvas_pet",
        "target": str(target),
        "copied": copied,
        "config": str(config_path),
        "warnings": warnings,
    }

    if dry_run:
        return summary

    if not no_backup:
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        shutil.copy2(config_path, backup_path)
        summary["backup"] = str(backup_path)
    config_path.write_text(updated, encoding="utf-8")
    return summary
