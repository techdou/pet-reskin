# pet-reskin

`pet-reskin` is an Agent Skill for generating and installing a complete `canvas-pet` character skin.

It converts a character description into:

- 8 required transparent PNG sprites
- an optional `cloud.png` helper asset
- `manifest.json`
- copied assets under `<canvas-pet>/assets/pet/`
- safe `pet.config.js` updates for `frames`, `quotes`, and `baseSize`

The skill follows the Agent Skills pattern: a small `SKILL.md` for routing and core workflow, deterministic scripts for repeatable operations, and reference files for detailed guidance.

## When to use

Use this for a full `canvas-pet`/web desktop-pet reskin.

Do not use it for a single illustration, logo, mascot avatar, generic animation explanation, or prompt-only image task.

## Requirements

- Python 3.8+
- Pillow
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- A target project with `pet.config.js`

Install Python dependency:

```bash
pip install -r requirements.txt
```

Set API key:

```bash
# macOS/Linux
export GEMINI_API_KEY="your-key"

# Windows PowerShell
$env:GEMINI_API_KEY="your-key"

# Windows CMD
set GEMINI_API_KEY=your-key
```

Optional model override:

```bash
export GEMINI_IMAGE_MODEL="gemini-3-pro-image"
```

## Directory structure

```text
pet-reskin/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── REVIEW.md
├── requirements.txt
├── assets/
│   └── example-plan.json
├── references/
│   ├── character-prompt-guide.md
│   ├── canvas-pet-contract.md
│   └── image-prompt-style-guide.md
├── scripts/
│   ├── check_env.py
│   ├── generate_sprites.py
│   ├── apply_config.py
│   ├── validate_output.py
│   └── pet_reskin.py
└── tests/
    ├── fixtures/
    │   └── sample-pet.config.js
    ├── test_apply_config.py
    └── test_validate_output.py
```

## Quickstart

Create a plan:

```json
{
  "character": "小橘猫「栗子」",
  "description": "圆滚滚的橘色虎斑猫，大而圆的绿眼睛，短粗四肢，尾巴向上翘起，肚皮和嘴部为白色，鼻头粉色，头顶一撮呆毛",
  "style": "现代扁平矢量插画，柔和的深棕色描边，配色温暖明亮",
  "baseSize": 88,
  "generateCloud": false,
  "quotes": ["今天也要好好吃饭。", "别催，在想了。"],
  "reuse_idol": false,
  "reuse_existing": false
}
```

Run the one-command pipeline:

```bash
python scripts/pet_reskin.py \
  --plan plan.json \
  --target /path/to/canvas-pet \
  --out ./sprites
```

If you also want the optional cloud helper asset:

```bash
python scripts/pet_reskin.py \
  --plan plan.json \
  --target /path/to/canvas-pet \
  --out ./sprites \
  --with-cloud
```

This runs:

1. environment check
2. image generation
3. sprite validation
4. safe config installation
5. final target validation

## Manual steps

```bash
python scripts/check_env.py --target /path/to/canvas-pet
python scripts/generate_sprites.py --skill-plan plan.json --out ./sprites
python scripts/validate_output.py --manifest ./sprites/manifest.json --sprites ./sprites
python scripts/apply_config.py --manifest ./sprites/manifest.json --sprites ./sprites --target /path/to/canvas-pet
python scripts/validate_output.py --manifest ./sprites/manifest.json --sprites ./sprites --target /path/to/canvas-pet --report ./sprites/validation-report.json
```

## Dry run

Validate routing and plan shape without calling Gemini:

```bash
python scripts/pet_reskin.py --plan plan.json --target /path/to/canvas-pet --out ./sprites --dry-run
```

## Repair one sprite

```bash
python scripts/generate_sprites.py --skill-plan plan.json --out ./sprites --only walkRight
```

Repair mode skips installation because it creates a partial manifest. Inspect the PNG first, then run a full generation/install when satisfied.

## Safety behavior

By default, installation is strict:

- Missing any of the 8 required frame keys fails.
- Missing PNG files fail.
- Ambiguous `pet.config.js` replacements fail.
- `pet.config.js` is backed up as `pet.config.js.bak`.
- `--dry-run` shows the operation without writing files.
- `cloud` is optional and preserved if it already exists in the target config and cloud generation was skipped.

Partial installation requires explicit opt-in:

```bash
python scripts/apply_config.py --manifest ./sprites/manifest.json --sprites ./sprites --target /path/to/canvas-pet --allow-partial
```

## Prompt design

The generation script uses a modern structured prompt strategy for GPT Image 2, Nano Banana, and similar current image models:

1. **idol prompt**: creates a single master reference image for the character.
2. **sprite prompts**: each required frame reuses the idol as a reference so the appearance stays consistent.
3. **cloud prompt**: only used when cloud generation is requested.

Prompt optimization highlights:

- sectioned prompts instead of one long sentence: `Task / Subject / Style / Composition / Output constraints`
- reference-frame prompts use `Reference image usage / Pose / Style / Composition / Output constraints`
- stronger identity locking: color palette, head size, body ratio, eye shape, outline thickness, clothing/accessories, signature features
- consistent framing: square canvas, full body, centered, fully inside the canvas, consistent scale across frames
- sprite-friendly composition: one subject, clean silhouette, no background clutter, no cast shadow
- chroma-key safety: solid `#78C878` background and instruction to avoid similar character colors

See `references/image-prompt-style-guide.md` for the prompt pattern.

## Testing

Run unit tests:

```bash
python -m unittest discover -s tests -v
```

These tests do not call Gemini. They validate config replacement, strict partial protection, cloud-optional behavior, and output validation behavior.

## Troubleshooting

### `GEMINI_API_KEY` missing

Set the environment variable before running generation. `check_env.py` reports this before API calls. Run `check_env.py --probe` (or let `pet_reskin.py` do it) to also verify the key is accepted by the API, so auth failures surface before any image is generated.

### Some sprites failed

The manifest records `failures`, `missingFrames`, and `missingRequiredFrames`. Strict mode refuses installation. Improve the plan description, rerun, or repair a single frame with `--only`. Strict checks only fire on full runs; repair mode (`--only`) intentionally skips them so partial manifests can be inspected.

### Green halo / residue around the character

Chroma keying uses a smooth alpha gradient (not a hard cutoff) plus a despill pass, so anti-aliased edges fade cleanly. If you still see a green halo, tune the gradient via `PET_RESKIN_KEY_INNER` (default 30, below = fully transparent) and `PET_RESKIN_KEY_OUTER` (default 120, above = fully opaque). If the character itself is green, change `KEY_COLOR` and `KEY_HEX` in `generate_sprites.py` to a color the character does not use.

### `pet.config.js` cannot be replaced

The script expects flat `frames`, `quotes`, and numeric `baseSize` fields. It now uses balanced-brace scanning (not regex) to locate the `frames` and `quotes` blocks, so string values containing `}` or `]` no longer break replacement. If the target config uses a different structure, update the config manually or adapt `apply_config.py` after reading `references/canvas-pet-contract.md`.

## License

MIT.
