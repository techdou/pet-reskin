#!/usr/bin/env python3
"""
generate_sprites.py — Generate a canvas-pet sprite set.

Behavior summary:
- Always generates the 8 core canvas-pet frames.
- `cloud.png` is optional and controlled by plan.generateCloud or CLI override.
- Writes both plan.json and manifest.json into --out.
- Uses a green chroma-key background for deterministic post-processing.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(2)

DEFAULT_MODEL_ID = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image")
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
IMAGE_SIZE = os.environ.get("GEMINI_IMAGE_SIZE", "1K")
KEY_COLOR = (120, 200, 120)
KEY_HEX = "#78C878"
KEY_TOLERANCE = int(os.environ.get("PET_RESKIN_KEY_TOLERANCE", "42"))

BASE_SPRITES: List[Dict[str, Any]] = [
    {"frame": "idle",       "file": "idle.png",         "role": "idle",         "needs_ref": True},
    {"frame": "idleWink",   "file": "idle-wink.png",    "role": "wink",         "needs_ref": True},
    {"frame": "walkFront1", "file": "walk-front-1.png", "role": "walk_front_1", "needs_ref": True},
    {"frame": "walkFront2", "file": "walk-front-2.png", "role": "walk_front_2", "needs_ref": True},
    {"frame": "walkLeft",   "file": "walk-left-1.png",  "role": "walk_left",    "needs_ref": True},
    {"frame": "walkRight",  "file": "walk-right-1.png", "role": "walk_right",   "needs_ref": True},
    {"frame": "walkBack",   "file": "walk-back-1.png",  "role": "walk_back",    "needs_ref": True},
    {"frame": "sleep",      "file": "sleep.png",        "role": "sleep",        "needs_ref": True},
]
OPTIONAL_SPRITES: List[Dict[str, Any]] = [
    {"frame": "cloud",      "file": "cloud.png",        "role": "cloud",        "needs_ref": False},
]
ALL_SPRITES = BASE_SPRITES + OPTIONAL_SPRITES
BASE_REQUIRED_FRAMES = [sp["frame"] for sp in BASE_SPRITES]
OPTIONAL_FRAME_NAMES = [sp["frame"] for sp in OPTIONAL_SPRITES]


def load_plan(path: Path) -> Dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: plan is not valid JSON: {path}: {exc}") from exc
    required = ["character", "description"]
    missing = [key for key in required if not str(plan.get(key, "")).strip()]
    if missing:
        raise SystemExit(f"ERROR: plan missing required fields: {', '.join(missing)}")
    plan.setdefault("style", "现代扁平矢量插画，柔和描边，透明桌宠精灵图风格")
    plan.setdefault("generateCloud", False)
    if "baseSize" in plan:
        try:
            plan["baseSize"] = int(plan["baseSize"])
        except (TypeError, ValueError) as exc:
            raise SystemExit("ERROR: plan.baseSize must be an integer") from exc
    if "quotes" in plan and not isinstance(plan["quotes"], list):
        raise SystemExit("ERROR: plan.quotes must be a list of strings")
    plan["generateCloud"] = bool(plan.get("generateCloud"))
    return plan


def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit(
            "ERROR: GEMINI_API_KEY is not set. Get a key from https://aistudio.google.com/ "
            "and set GEMINI_API_KEY before running generation."
        )
    return key


def build_api_url(model_id: str, api_key: str) -> str:
    return f"{API_BASE}/{model_id}:streamGenerateContent?key={api_key}"


def call_gemini(api_key: str, model_id: str, parts: List[Dict[str, Any]], retries: int = 2) -> Any:
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "imageConfig": {"image_size": IMAGE_SIZE},
        },
    }
    data = json.dumps(body).encode("utf-8")
    last_error: Optional[BaseException] = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            build_api_url(model_id, api_key),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            try:
                detail = json.loads(exc.read().decode("utf-8"))["error"]["message"]
            except Exception:
                detail = str(exc)
            if exc.code == 429 and attempt < retries:
                wait = 10 * (attempt + 1)
                print(f"   ⚠ Rate limited, retrying in {wait}s… ({detail})", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc
    raise RuntimeError(f"Gemini retry exhausted: {last_error}")


def extract_image_bytes(response: Any) -> bytes:
    chunks = response if isinstance(response, list) else [response]
    for chunk in chunks:
        for candidate in chunk.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
    raise ValueError("Gemini response did not include image data; it may have been blocked or returned text only")


def resolve_generate_cloud(plan: Dict[str, Any], cloud_override: Optional[bool]) -> bool:
    return bool(plan.get("generateCloud")) if cloud_override is None else cloud_override


def resolve_sprite_list(plan: Dict[str, Any], only: Optional[str], cloud_override: Optional[bool]) -> List[Dict[str, Any]]:
    if not only:
        sprites = list(BASE_SPRITES)
        if resolve_generate_cloud(plan, cloud_override):
            sprites += OPTIONAL_SPRITES
        return sprites

    requested = {item.strip() for item in only.split(",") if item.strip()}
    selected = []
    all_aliases = {alias for sp in ALL_SPRITES for alias in (sp["frame"], sp["file"], sp["role"])}
    for sp in ALL_SPRITES:
        aliases = {sp["frame"], sp["file"], sp["role"]}
        if aliases & requested:
            selected.append(sp)
    unknown = requested - all_aliases
    if unknown:
        raise SystemExit(f"ERROR: unknown --only sprite(s): {', '.join(sorted(unknown))}")
    return selected


def compact_prompt(sections: Dict[str, Iterable[str] | str]) -> str:
    blocks: List[str] = []
    for title, content in sections.items():
        if isinstance(content, str):
            lines = [content.strip()] if content.strip() else []
        else:
            lines = [str(item).strip() for item in content if str(item).strip()]
        if not lines:
            continue
        if len(lines) == 1:
            blocks.append(f"{title}: {lines[0]}")
        else:
            blocks.append(title + ":\n" + "\n".join(f"- {line}" for line in lines))
    return "\n\n".join(blocks)


def common_output_constraints() -> List[str]:
    return [
        f"Use a single flat chroma-key green background: {KEY_HEX}.",
        "Keep the background perfectly solid and uniform, with no gradient, texture, scenery, floor, or shadow.",
        "Leave a small transparent-safe margin around the subject after background removal.",
        "Do not add text, captions, UI elements, watermarks, logos, duplicate characters, extra props, or extra objects.",
        "Avoid using any character color close to the chroma-key background color.",
    ]


def idol_prompt(plan: Dict[str, Any]) -> str:
    return compact_prompt({
        "Task": "Create a production-ready master reference image for a web desktop pet sprite. This is a character reference asset, not a scene illustration.",
        "Subject": [
            f"Character name: {plan['character']}.",
            f"Visual identity: {plan['description']}.",
            "Make the signature features readable at small UI size.",
        ],
        "Style": [
            f"{plan.get('style')}.",
            "Clean mascot / vector-illustration feeling, simple readable shapes, soft polished outlines, compact desktop-pet proportions.",
        ],
        "Composition": [
            "Exactly one character only.",
            "Full body visible from head to toe, centered in a square canvas, facing forward at eye level.",
            "Neutral relaxed standing pose, head looking toward the viewer.",
            "Clean silhouette; avoid tiny fragile details that will disappear when scaled down.",
        ],
        "Output constraints": common_output_constraints(),
    })


def sprite_pose(role: str) -> str:
    poses = {
        "idle": "front view, standing still, relaxed neutral pose",
        "wink": "front view, standing still, one eye closed in a friendly wink, otherwise matching the idle pose",
        "walk_front_1": "front view, walking toward the viewer, mid-stride, left leg forward",
        "walk_front_2": "front view, walking toward the viewer, mid-stride, right leg forward, alternate step from walk_front_1",
        "walk_left": "side profile, walking to the left, the character clearly faces left, mid-stride",
        "walk_right": "side profile, walking to the right, the character clearly faces right, mid-stride",
        "walk_back": "back view, walking away from the viewer, mid-stride",
        "sleep": "sleeping peacefully, eyes closed, curled up or resting in a compact pose",
        "cloud": "a soft fluffy white cloud, viewed from slightly above, simple isolated helper asset",
    }
    return poses[role]


def cloud_prompt() -> str:
    return compact_prompt({
        "Task": "Create a production-ready helper cloud sprite for a web desktop pet UI.",
        "Subject": [
            "One soft fluffy white cloud only.",
            "Simple rounded silhouette with gentle volume; use very light gray shading only where needed.",
            "It should work as a small decorative/helper asset under or near a pet character.",
        ],
        "Style": [
            "Clean mascot/vector-illustration style, soft edges, friendly and minimal.",
            "Match a modern flat web-sprite visual language rather than a realistic sky cloud.",
        ],
        "Composition": [
            "Single cloud centered in a square canvas.",
            "Fully visible with comfortable margins and no cropped edges.",
            "No character and no scene elements.",
        ],
        "Output constraints": common_output_constraints(),
    })


def sprite_prompt(plan: Dict[str, Any], role: str) -> str:
    if role == "cloud":
        return cloud_prompt()
    return compact_prompt({
        "Task": "Create one frame for a consistent web desktop pet sprite animation, using the provided reference image as the identity source.",
        "Reference image usage": [
            f"Use the reference image as the canonical design for {plan['character']}.",
            "Preserve identity; do not redesign the character.",
            "Keep the same color palette, head size, body ratio, eye shape, outline thickness, clothing/accessories if any, and all signature features.",
        ],
        "Pose": sprite_pose(role),
        "Style": [
            f"Match the reference style: {plan.get('style')}.",
            "Clean mascot/vector-illustration sprite, readable at small size, polished but simple.",
        ],
        "Composition": [
            "Exactly one character only.",
            "Full body visible, centered in a square canvas, fully inside the canvas, with consistent scale across frames.",
            "Clean silhouette suitable for animation; avoid motion blur, perspective distortion, and overly detailed textures.",
        ],
        "Output constraints": common_output_constraints(),
    })


def chroma_key(src_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(src_bytes)).convert("RGB")
    width, height = image.size
    source = image.load()
    output = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    target = output.load()
    kr, kg, kb = KEY_COLOR
    for y in range(height):
        for x in range(width):
            r, g, b = source[x, y]
            if abs(r - kr) <= KEY_TOLERANCE and abs(g - kg) <= KEY_TOLERANCE and abs(b - kb) <= KEY_TOLERANCE:
                continue
            target[x, y] = (r, g, b, 255)
    buffer = io.BytesIO()
    output.save(buffer, format="PNG")
    return buffer.getvalue()


def write_manifest(
    out: Path,
    plan: Dict[str, Any],
    model_id: str,
    requested_sprites: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    failures: List[Dict[str, str]],
) -> Dict[str, Any]:
    frames = {sp["frame"]: f"./assets/pet/{sp['file']}" for sp in results}
    requested_frames = [sp["frame"] for sp in requested_sprites]
    required_frames = list(BASE_REQUIRED_FRAMES)
    optional_frames = [sp["frame"] for sp in OPTIONAL_SPRITES]
    manifest = {
        "schema": "pet-reskin.manifest.v2",
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": model_id,
        "character": plan.get("character", ""),
        "baseSize": plan.get("baseSize"),
        "quotes": plan.get("quotes", []),
        "generateCloud": bool(plan.get("generateCloud")),
        "requiredFrames": required_frames,
        "optionalFrames": optional_frames,
        "requestedFrames": requested_frames,
        "frames": frames,
        "files": [sp["file"] for sp in results],
        "missingFrames": [frame for frame in requested_frames if frame not in frames],
        "missingRequiredFrames": [frame for frame in required_frames if frame not in frames],
        "failures": failures,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def run(
    plan_path: Path,
    out_dir: Path,
    model_id: str,
    strict: bool,
    only: Optional[str],
    dry_run: bool,
    cloud_override: Optional[bool],
) -> int:
    plan = load_plan(plan_path)
    plan["generateCloud"] = resolve_generate_cloud(plan, cloud_override)
    selected = resolve_sprite_list(plan, only, cloud_override)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw").mkdir(exist_ok=True)
    shutil.copy2(plan_path, out_dir / "plan.json")
    # Ensure copied plan reflects CLI cloud override when used.
    (out_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    if dry_run:
        preview = {
            "ok": True,
            "dryRun": True,
            "plan": plan,
            "model": model_id,
            "selectedSprites": [sp["frame"] for sp in selected],
            "requiredFrames": BASE_REQUIRED_FRAMES,
            "optionalFrames": OPTIONAL_FRAME_NAMES,
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    api_key = get_api_key()

    idol_path = out_dir / "idol.png"
    if idol_path.exists() and plan.get("reuse_idol"):
        idol_bytes = idol_path.read_bytes()
        print(f"✓ Reusing idol reference: {idol_path}")
    else:
        print("▶ Generating idol reference…")
        idol_bytes = extract_image_bytes(call_gemini(api_key, model_id, [{"text": idol_prompt(plan)}]))
        idol_path.write_bytes(idol_bytes)
        print(f"  ✓ {idol_path}")

    idol_part = {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(idol_bytes).decode("ascii")}}
    results: List[Dict[str, Any]] = []
    failures: List[Dict[str, str]] = []

    for sp in selected:
        dest = out_dir / sp["file"]
        if dest.exists() and plan.get("reuse_existing"):
            print(f"✓ Reusing existing sprite: {sp['file']}")
            results.append(sp)
            continue
        parts = [{"text": sprite_prompt(plan, sp["role"])}]
        if sp["needs_ref"]:
            parts.append(idol_part)
        print(f"▶ Generating {sp['file']} ({sp['role']})…")
        try:
            raw = extract_image_bytes(call_gemini(api_key, model_id, parts))
            (out_dir / "raw" / sp["file"]).write_bytes(raw)
            dest.write_bytes(chroma_key(raw))
            print(f"  ✓ {dest}")
            results.append(sp)
        except Exception as exc:
            message = str(exc)
            failures.append({"frame": sp["frame"], "file": sp["file"], "error": message})
            print(f"  ✗ {sp['file']} failed: {message}", file=sys.stderr)

    manifest = write_manifest(out_dir, plan, model_id, selected, results, failures)
    print(f"\n✅ Generated {len(results)}/{len(selected)} requested sprites → {out_dir}")
    print(f"   manifest: {out_dir / 'manifest.json'}")

    if strict and not only and manifest["missingRequiredFrames"]:
        print(
            f"ERROR: strict mode requires all 8 core frames. Missing: {', '.join(manifest['missingRequiredFrames'])}",
            file=sys.stderr,
        )
        return 1
    if strict and failures:
        missing = manifest["missingFrames"]
        label = ", ".join(missing) if missing else "one or more requested frames"
        print(f"ERROR: strict mode detected generation failures. Missing/failed: {label}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a canvas-pet sprite set")
    parser.add_argument("--skill-plan", required=True, type=Path, help="Path to plan.json")
    parser.add_argument("--out", required=True, type=Path, help="Output directory for sprites")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID, help="Gemini image model ID; defaults to GEMINI_IMAGE_MODEL or gemini-3-pro-image")
    parser.add_argument("--allow-partial", action="store_true", help="Do not fail if some requested frames are missing")
    parser.add_argument("--only", help="Generate only specific frame/file/role names, comma-separated, for repair workflows")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the resolved plan without calling Gemini")
    cloud_group = parser.add_mutually_exclusive_group()
    cloud_group.add_argument("--with-cloud", action="store_true", help="Force generation of optional cloud.png")
    cloud_group.add_argument("--without-cloud", action="store_true", help="Force skip optional cloud.png")
    args = parser.parse_args()
    cloud_override = True if args.with_cloud else False if args.without_cloud else None
    raise SystemExit(
        run(
            args.skill_plan,
            args.out,
            args.model,
            strict=not args.allow_partial,
            only=args.only,
            dry_run=args.dry_run,
            cloud_override=cloud_override,
        )
    )


if __name__ == "__main__":
    main()
