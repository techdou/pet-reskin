---
name: pet-reskin
description: Generate and install a complete canvas-pet/web desktop-pet reskin: 8 required transparent PNG sprite frames, plus an optional cloud.png helper asset, and safe pet.config.js updates. Use only when the user wants a full canvas-pet character skin or asks to replace/install sprites for a project that uses pet.config.js and assets/pet. Do not use for a single mascot image, logo, avatar, generic web-pet animation advice, or prompt-only illustration work.
---

# pet-reskin

Use this skill to turn a character idea into a complete, installable `canvas-pet` skin: 8 core PNG sprite frames, an optional `cloud.png`, a `manifest.json`, and a safe update to `pet.config.js`.

## Routing

Use this skill when all are true:
- The task is about `canvas-pet`, a web desktop pet, or a project with `pet.config.js` and `assets/pet/`.
- The expected output is a full sprite set, not just one image.
- The user wants generation, replacement, installation, or validation of a pet skin.

Do not use this skill when:
- The user only wants a mascot illustration, logo, avatar, or image prompt.
- The user asks how web-pet animation works in general.
- The target uses a spritesheet atlas instead of separate PNG frames.
- There is no canvas-pet-like project contract to update.

## Required inputs

- Character concept with visual identity. If vague, ask for up to three visual details before generation.
- Target project root containing `pet.config.js` and usually `assets/pet/`.
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` in the environment.
- Decide whether `cloud.png` should also be generated. Default is no.

## Workflow

1. Read `references/character-prompt-guide.md` when converting a vague user idea into `plan.json`. Read `references/image-prompt-style-guide.md` before changing prompt templates.
2. Run preflight checks:
   ```bash
   python scripts/check_env.py --target <canvas-pet-root>
   ```
3. Generate and install in one command:
   ```bash
   python scripts/pet_reskin.py --plan <plan.json> --target <canvas-pet-root> --out <workdir>/sprites
   ```
4. To include the optional cloud helper asset:
   ```bash
   python scripts/pet_reskin.py --plan <plan.json> --target <canvas-pet-root> --out <workdir>/sprites --with-cloud
   ```
5. If using separate steps:
   ```bash
   python scripts/generate_sprites.py --skill-plan <plan.json> --out <workdir>/sprites
   python scripts/validate_output.py --manifest <workdir>/sprites/manifest.json --sprites <workdir>/sprites
   python scripts/apply_config.py --manifest <workdir>/sprites/manifest.json --sprites <workdir>/sprites --target <canvas-pet-root>
   python scripts/validate_output.py --manifest <workdir>/sprites/manifest.json --sprites <workdir>/sprites --target <canvas-pet-root>
   ```

## Output contract

Generation must produce:
- `plan.json` copied into the output directory.
- `manifest.json` with `frames`, `files`, `quotes`, `baseSize`, `requiredFrames`, `optionalFrames`, `requestedFrames`, and failures if any.
- These 8 required transparent PNGs: `idle.png`, `idle-wink.png`, `walk-front-1.png`, `walk-front-2.png`, `walk-left-1.png`, `walk-right-1.png`, `walk-back-1.png`, `sleep.png`.
- Optional: `cloud.png` when requested.

Installation must:
- Copy generated PNGs to `<target>/assets/pet/`.
- Back up `<target>/pet.config.js` to `pet.config.js.bak` unless explicitly disabled.
- Replace `frames`, `quotes`, and `baseSize` in `pet.config.js`.
- Preserve an existing `cloud` frame if cloud generation was skipped.
- Refuse partial installs by default.

## Success criteria

Before reporting completion, confirm:
- `validate_output.py` returns `ok: true` or prints `OK`.
- All 8 required frame keys exist in `manifest.json`.
- `pet.config.js` contains all 8 required frame keys.
- If cloud was requested, `pet.config.js` also contains the `cloud` key.
- At least one generated PNG has been inspected when image-viewing tools are available; especially check that `walk-right-1.png` faces right.

## Repair and iteration

- Single-frame repair:
  ```bash
  python scripts/generate_sprites.py --skill-plan <plan.json> --out <workdir>/sprites --only walkRight
  ```
  Then inspect the repaired PNG. Do not install a repair-only partial manifest unless the user explicitly accepts partial installation.
- Full rerun with same idol: set `reuse_idol: true` in `plan.json`.
- Skip already generated sprites: set `reuse_existing: true` in `plan.json`.
- Include cloud via plan: set `generateCloud: true` in `plan.json`.
- Dry run without API calls:
  ```bash
  python scripts/pet_reskin.py --plan <plan.json> --target <canvas-pet-root> --out <workdir>/sprites --dry-run
  ```

## Important constraints

- Do not edit `pet.js` or the runtime engine unless the user explicitly asks for engine work.
- Do not assume the target project path.
- Do not silently install incomplete sprite sets.
- Prefer the scripts over ad-hoc edits; they encode the project contract and validation checks.
