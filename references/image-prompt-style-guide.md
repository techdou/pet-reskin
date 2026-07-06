# Image Prompt Style Guide

This guide records the prompt style used by `scripts/generate_sprites.py` for modern image models such as GPT Image 2 and Nano Banana.

## Design principles

1. Use structured sections instead of one long sentence.
2. Start with a strong task verb: `Create`, `Draw`, `Generate`, or `Edit`.
3. Separate what changes from what must remain invariant.
4. Describe composition explicitly: subject count, framing, viewpoint, canvas placement, margins, and scale.
5. Use positive framing first, then add minimal hard constraints for production safety.
6. Repeat critical identity invariants on every reference-based sprite frame.
7. Keep sprite prompts short enough to debug, but detailed enough to remove ambiguity.

## Section pattern

For the master reference image:

```text
Task
Subject
Style
Composition
Output constraints
```

For reference-based sprite frames:

```text
Task
Reference image usage
Pose
Style
Composition
Output constraints
```

For optional helper assets such as cloud:

```text
Task
Subject
Style
Composition
Output constraints
```

## Why this structure works

- GPT Image style models respond well to clearly separated goals, details, and constraints.
- Nano Banana style models benefit from concrete subject, style, action, and composition descriptions.
- Reference-based image generation needs repeated invariants; otherwise the character may drift between frames.
- Sprite assets need tighter composition than normal illustrations: one subject, centered, full-body, clean silhouette, uniform background.

## Prompt invariants for pet sprites

Always preserve:

- color palette
- head size
- body ratio
- eye shape
- outline thickness
- clothing/accessories if present
- signature features
- small-size readability

Always constrain:

- one character only
- square canvas
- full body visible
- consistent scale across frames
- solid chroma-key background
- no text/watermark/logo
- no scene/floor/shadow

## Current chroma-key contract

The script uses:

```text
#78C878
```

The prompt asks the model to use that exact solid background. The post-processing script removes pixels near this RGB value. If a character is green, change the key color in `generate_sprites.py` before generation.
