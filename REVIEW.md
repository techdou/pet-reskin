# pet-reskin Skill Review

## Overall status

This package has been upgraded from a script-oriented prototype into a stricter Agent Skill package, and now supports cloud-optional generation.

## User-facing improvements

- Clear quickstart and manual workflow.
- Preflight check before expensive API calls.
- Strict default installation so broken partial outputs are not copied into the project.
- Automatic `pet.config.js.bak` backup.
- Validation report for final handoff.
- `cloud.png` is now explicitly optional instead of being forced into every run.

## Agent-matching improvements

- Narrower `description` in `SKILL.md` to prevent activation for generic mascot/image tasks.
- Explicit negative triggers.
- Required inputs, output contract, success criteria, and repair workflow are now separate and easy to follow.
- Detailed prompt-writing guidance moved to `references/character-prompt-guide.md`.
- The skill now makes the cloud decision explicit: default skip, enable only when requested.

## Engineering improvements

- `plan.json` and `manifest.json` now form a closed contract.
- `manifest.json` carries `quotes`, `baseSize`, `requiredFrames`, `optionalFrames`, `requestedFrames`, missing frames, and failures.
- Config replacement uses checked `re.subn` logic through `replace_once`.
- Existing optional frames such as `cloud` are preserved if not regenerated.
- Tests cover the main cloud-optional and required-frame paths.

## Prompt improvements

- Idol prompt now uses structured sections: Task, Subject, Style, Composition, Output constraints.
- Sprite prompts now use reference-oriented sections: Task, Reference image usage, Pose, Style, Composition, Output constraints.
- Sprite prompts lock identity more tightly: palette, proportions, head size, eye shape, outline thickness, accessories, and signature features.
- Prompts explicitly constrain square framing, scale consistency, small-size readability, background uniformity, and chroma-key safety.
- Cloud has its own optimized helper-asset prompt instead of being treated like a normal sprite.

## Remaining limitations

- Image quality still depends on the chosen Gemini model and prompt specificity.
- `apply_config.py` assumes a flat `pet.config.js` structure. Complex dynamic configs may need manual adaptation.
- Chroma keying is simple RGB thresholding; green characters require changing the key color.
