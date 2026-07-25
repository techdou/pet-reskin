---
name: pet-reskin
description: Generate and install a complete canvas-pet / multi-skin web desktop-pet character. Supports two project architectures (single-skin canvas-pet with pet.config.js, multi-skin with pet.js skins array), two image providers (Gemini, image2-api with gpt-image-2), configurable frame sets (base8 / extended16 / custom), and reference-image reuse. Use when the user wants a full pet sprite set generated, replaced, or installed. Do not use for single mascot image, logo, avatar, or prompt-only illustration work.
---

# pet-reskin

Turn a character description into a complete, installable pet sprite set. Supports two architectures, two providers, and configurable frames.

## When to use

All true:
- The task is about a web desktop pet (canvas-pet single-skin, or multi-skin pet.js project).
- The expected output is a full sprite set, not a single image.
- The user wants generation, replacement, installation, or validation of a pet skin.

Do not use for:
- Single mascot illustration, logo, avatar, or image prompt.
- Generic web-pet animation advice.
- Projects using spritesheet atlases instead of separate PNG frames.

## Target project types (auto-detected)

| Type | Marker | Installer |
|---|---|---|
| **canvas-pet** (single-skin) | `pet.config.js` with flat `frames` object | `installers/canvas_pet.py` |
| **multi-skin** | `pet.js` with `PET_CONFIG.skins` array | `installers/multi_skin.py` |

`check_env.py --target <root>` auto-detects. `apply_config.py` dispatches accordingly.

## plan.json schema

Required:
- `character`: name/identity
- `description`: visual identity (body shape, colors, features, expression, outfit)

Optional (v2.0 additions):
- `provider`: `"gemini"` (default) | `"image2api"` — image API. image2api wraps the image2-api skill (gpt-image-2 + 8-provider fallback).
- `background`: `"chroma"` (default, green chroma-key) | `"white"` (white-bg post-processing, suits gpt-image-2)
- `frameSet`: `"base8"` (default) | `"extended16"` | custom template name
- `frames`: custom frame array (overrides frameSet). Each item: `{frame, file, role, pose}`
- `referenceImage`: path to existing reference image (skips idol generation, used as identity source for all frames)
- `referenceAsIdle`: bool — treat referenceImage as the idle frame directly (saves 2 API calls)
- `skinId` / `skinName`: multi-skin installer uses these for the new skin's id/name
- `startXRatio`, `idleVariants`, `idleEvents`: multi-skin extras written into the new skin object

Legacy (still supported):
- `style`, `baseSize`, `quotes`, `keyColor`, `generateCloud`, `reuse_idol`, `reuse_existing`

See `assets/example-plan-*.json` for complete examples.

## Frame templates

`assets/frame-templates.json` ships two templates:

- **base8** (default, backward compatible): idle / idleWink / walkFront1-2 / walkLeft / walkRight / walkBack / sleep
- **extended16**: base8 + idleThink / idleLook / walkLeft2 / walkRight2 / walkBack2 / sleep2 / wave / happy

Custom: set `plan.frames` to an array of `{frame, file, role, pose}` specs.

## Workflow

1. Read `references/character-prompt-guide.md` for vague→plan conversion, `references/image-prompt-style-guide.md` for prompt structure.
2. Preflight: `python scripts/check_env.py --target <root>` (auto-detects architecture, checks image2-api availability).
3. Generate + install in one command:
   ```bash
   python scripts/pet_reskin.py --plan <plan.json> --target <root> --out <workdir>/sprites
   ```
4. Optional cloud helper: add `--with-cloud`.
5. Manual steps if needed:
   ```bash
   python scripts/generate_sprites.py --skill-plan plan.json --out sprites
   python scripts/validate_output.py --manifest sprites/manifest.json --sprites sprites
   python scripts/apply_config.py --manifest sprites/manifest.json --sprites sprites --target <root>
   ```

## Provider selection guide

| Scenario | provider | background |
|---|---|---|
| Default / single Gemini key / canvas-pet classic | `gemini` (or omit) | `chroma` (or omit) |
| Want gpt-image-2 + multi-provider fallback (more stable) | `image2api` | `white` |
| Green character that collides with default chroma key | `gemini` | `chroma` + custom `keyColor: "#FF00FF"` |
| Have an existing reference image (cutout.png) | either | `white` (gpt-image-2) or `chroma` (Gemini) |

## Output contract

Generation produces (in `--out`):
- `plan.json` (resolved copy)
- `manifest.json` with `frames`, `files`, `quotes`, `baseSize`, `requiredFrames`, `optionalFrames`, `requestedFrames`, `failures`
- Transparent PNGs (8 base / 16 extended / custom)
- Optional `cloud.png`
- `raw/` subdirectory with unprocessed originals
- `idol.png` (only when no referenceImage; the master reference)

Installation:
- **canvas-pet**: copies PNGs to `<target>/assets/pet/`, backs up + updates `pet.config.js` (`frames`/`quotes`/`baseSize`).
- **multi-skin**: copies PNGs to `<target>/pet/assets/<skinId>/`, backs up + appends new skin object to `pet.js` `skins` array.

## Success criteria

Before reporting completion:
- `validate_output.py` returns ok.
- All required frame keys exist in `manifest.json`.
- Target config (pet.config.js or pet.js) contains all installed frame keys.
- At least one PNG inspected when vision tools available (especially walk-right faces right).
- For multi-skin: new skin id appears in pet.js skins array.

## Repair and iteration

- Single-frame repair: `python scripts/generate_sprites.py --skill-plan plan.json --out sprites --only walkRight`
- Reuse cached idol: `reuse_idol: true` in plan.json
- Skip finished sprites: `reuse_existing: true` in plan.json
- Dry run: `--dry-run`

## Important constraints

- Do not edit runtime engine files (pet.js engine logic, pet.config.js structure beyond frames/quotes/baseSize) unless explicitly asked.
- Do not assume target architecture — let auto-detection work or pass `--target-type`.
- Do not silently install incomplete sprite sets (strict by default; `--allow-partial` to override).
- Prefer scripts over ad-hoc edits; they encode the project contract.
