# Changelog

## 1.3.1

### Added

- `plan.keyColor` field (`#RRGGBB`) to override the chroma-key background color per character.
- Automatic color-collision detection: after the idol is generated, the script checks whether too many character pixels fall inside the chroma-key gradient band and stops with actionable advice before wasting the 8 sprite API calls.
- `manifest.json` now records the resolved `keyColor`.
- Unit tests for collision detection, custom keyColor, parameterized chroma_key, and hex parsing.

### Changed

- `chroma_key` now takes the key color as a parameter instead of reading module-level globals; prompt builders thread the key hex through so the model is told the correct background color.
- Despill is now channel-agnostic: it suppresses whichever channel dominates the key color (green/red/blue), so non-green key colors still get clean edges.
- Removed the `PET_RESKIN_KEY_INNER` / `PET_RESKIN_KEY_OUTER` environment variables. The gradient band is fixed (30–120) because edge anti-aliasing width is model-intrinsic; tuning thresholds could not save a true color collision anyway.

## 1.3.0

### Added

- `references/image-prompt-style-guide.md` for GPT Image 2 / Nano Banana style prompt structure.

### Changed

- Reworked `idol_prompt`, `sprite_prompt`, and `cloud_prompt` into structured section prompts.
- Sprite prompts now separate task, reference usage, pose, style, composition, and output constraints.
- Strengthened identity invariants for reference-based generation: palette, proportions, head size, outline thickness, eye shape, accessories, and signature features.
- Improved composition constraints for sprite production: square canvas, one subject, full body, consistent scale, clean silhouette, and chroma-key safety.

## 1.2.0

### Added

- Optional cloud generation control via `plan.generateCloud`.
- CLI overrides: `--with-cloud` and `--without-cloud`.
- Manifest fields `optionalFrames`, `requestedFrames`, and `missingRequiredFrames`.
- Tests for cloud-optional validation and config preservation.

### Changed

- Core required frame set is now 8 frames; `cloud.png` is treated as an optional helper asset.
- Prompt strategy was strengthened for better sprite consistency: tighter identity locking, cleaner silhouette, and stronger canvas/framing constraints.
- `apply_config.py` now preserves an existing `cloud` frame when the manifest does not include a new cloud.
- `validate_output.py` now validates required, optional, and requested frames separately.

### Fixed

- Fixed over-strict validation that previously rejected valid outputs when cloud was intentionally omitted.
- Fixed config rewriting behavior so skipping cloud no longer removes an existing `cloud` entry from `pet.config.js`.

## 1.1.0

### Added

- One-command orchestrator: `scripts/pet_reskin.py`.
- Environment preflight: `scripts/check_env.py`.
- Output and installation validator: `scripts/validate_output.py`.
- `requirements.txt`.
- `references/canvas-pet-contract.md`.
- Unit tests for config updates, strict partial handling, and validation.
- `--dry-run`, `--only`, `--model`, and `--allow-partial` controls.

### Changed

- `SKILL.md` rewritten for Agent Skills routing clarity and progressive disclosure.
- Gemini image model is configurable through `--model` or `GEMINI_IMAGE_MODEL`.
- `generate_sprites.py` now copies `plan.json` into the output directory and writes plan-derived `quotes`/`baseSize` into `manifest.json`.
- `apply_config.py` now backs up `pet.config.js` by default and uses checked single-match replacements.

### Fixed

- Fixed the contract break where `apply_config.py` expected `sprites/plan.json` but generation never copied it.
- Prevented silent installation of incomplete sprite sets.
- Prevented silent config corruption when regex replacement does not match exactly once.

## 1.0.0

- Initial skill with `SKILL.md`, sprite generation script, config installer, example plan, and prompt guide.
