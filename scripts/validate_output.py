#!/usr/bin/env python3
"""validate_output.py — Validate generated sprites and optional target installation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(2)

BASE_REQUIRED_FRAMES = [
    "idle", "idleWink", "walkFront1", "walkFront2", "walkLeft", "walkRight", "walkBack", "sleep"
]
DEFAULT_OPTIONAL_FRAMES = ["cloud"]
ALL_KNOWN_FRAMES = BASE_REQUIRED_FRAMES + DEFAULT_OPTIONAL_FRAMES


def load_manifest(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid manifest JSON: {path}: {exc}") from exc


def required_frames_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    required = manifest.get("requiredFrames")
    if isinstance(required, list) and required:
        return [str(item) for item in required]
    return list(BASE_REQUIRED_FRAMES)


def optional_frames_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    optional = manifest.get("optionalFrames")
    if isinstance(optional, list):
        return [str(item) for item in optional]
    return list(DEFAULT_OPTIONAL_FRAMES)


def requested_frames_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    requested = manifest.get("requestedFrames")
    if isinstance(requested, list) and requested:
        return [str(item) for item in requested]
    return required_frames_from_manifest(manifest)


def check_png(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {"file": str(path), "exists": path.exists()}
    if not path.exists():
        result["ok"] = False
        return result
    try:
        with Image.open(path) as image:
            result.update({
                "format": image.format,
                "mode": image.mode,
                "size": image.size,
                "hasAlpha": image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info),
                "ok": image.format == "PNG",
            })
    except Exception as exc:
        result.update({"ok": False, "error": str(exc)})
    return result


def parse_frame_keys_from_config(text: str) -> List[str]:
    keys = sorted(set(re.findall(r"\b([A-Za-z_]\w*)\s*:", text)))
    return [key for key in keys if key in ALL_KNOWN_FRAMES]


def validate(manifest_path: Path, sprites_dir: Path, target: Path | None, allow_partial: bool) -> Dict[str, Any]:
    manifest = load_manifest(manifest_path)
    frames = manifest.get("frames", {}) if isinstance(manifest.get("frames"), dict) else {}
    files = manifest.get("files", []) if isinstance(manifest.get("files"), list) else []
    required_frames = required_frames_from_manifest(manifest)
    optional_frames = optional_frames_from_manifest(manifest)
    requested_frames = requested_frames_from_manifest(manifest)
    errors: List[str] = []
    warnings: List[str] = []

    missing_required = [frame for frame in required_frames if frame not in frames]
    missing_requested = [frame for frame in requested_frames if frame not in frames]
    if missing_required and not allow_partial:
        errors.append("missing required frames: " + ", ".join(missing_required))

    pngs = [check_png(sprites_dir / fname) for fname in files]
    for item in pngs:
        if not item.get("exists"):
            errors.append("missing file: " + item["file"])
        elif item.get("format") != "PNG":
            errors.append("not a PNG: " + item["file"])
        elif not item.get("hasAlpha"):
            warnings.append("PNG has no alpha channel: " + item["file"])

    target_report: Dict[str, Any] | None = None
    if target is not None:
        config_path = target / "pet.config.js"
        target_report = {"config": str(config_path), "exists": config_path.exists()}
        if not config_path.exists():
            errors.append("target missing pet.config.js")
        else:
            text = config_path.read_text(encoding="utf-8")
            frame_keys = parse_frame_keys_from_config(text)
            target_report["frameKeys"] = frame_keys
            target_required_missing = [frame for frame in required_frames if frame not in frame_keys]
            target_manifest_missing = [frame for frame in frames if frame not in frame_keys]
            target_report["missingRequiredFrameKeys"] = target_required_missing
            target_report["missingManifestFrameKeys"] = target_manifest_missing
            if target_required_missing and not allow_partial:
                errors.append("pet.config.js missing required frame keys: " + ", ".join(target_required_missing))
            if target_manifest_missing and not allow_partial:
                errors.append("pet.config.js missing installed manifest frame keys: " + ", ".join(target_manifest_missing))

    return {
        "ok": not errors,
        "manifest": str(manifest_path),
        "spritesDir": str(sprites_dir),
        "requiredFrames": required_frames,
        "optionalFrames": optional_frames,
        "requestedFrames": requested_frames,
        "missingRequiredFrames": missing_required,
        "missingRequestedFrames": missing_requested,
        "pngs": pngs,
        "target": target_report,
        "warnings": warnings,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate pet-reskin output")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--sprites", required=True, type=Path)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report", type=Path, help="Write validation report JSON")
    args = parser.parse_args()
    report = validate(args.manifest, args.sprites, args.target, args.allow_partial)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    if args.json:
        print(output)
    else:
        print("OK" if report["ok"] else "FAILED")
        for error in report["errors"]:
            print("ERROR:", error)
        for warning in report["warnings"]:
            print("WARNING:", warning)
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
