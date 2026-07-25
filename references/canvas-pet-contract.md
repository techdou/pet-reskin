# Pet Project Contracts

This file defines the project contracts supported by `pet-reskin` v2.0+.

Two architectures are auto-detected from the target directory structure.

## Architecture 1: canvas-pet (single-skin, legacy)

The target project root must contain:

```text
pet.config.js
assets/pet/
```

`assets/pet/` may be created by the installer if missing, but `pet.config.js` must already exist.

`pet.config.js` must expose a flat `frames` object with these 8 required keys:

```js
frames: {
  idle: './assets/pet/idle.png',
  idleWink: './assets/pet/idle-wink.png',
  walkFront1: './assets/pet/walk-front-1.png',
  walkFront2: './assets/pet/walk-front-2.png',
  walkLeft: './assets/pet/walk-left-1.png',
  walkRight: './assets/pet/walk-right-1.png',
  walkBack: './assets/pet/walk-back-1.png',
  sleep: './assets/pet/sleep.png',
}
```

Optional: `cloud` frame. The installer preserves an existing `cloud` entry if cloud generation is skipped.

The installer updates only `frames`, `quotes`, `baseSize` — never runtime engine code.

## Architecture 2: multi-skin (pet.js skins array)

The target project root must contain:

```text
pet.js              (with PET_CONFIG.skins array)
pet/assets/         (each skin in its own subdirectory)
```

`pet.js` must contain a `skins` array, typically inside `PET_CONFIG`:

```js
const PET_CONFIG = {
  // ... config ...
  skins: [
    {
      id: 'techdou',
      name: '科技豆',
      frames: { idle: './assets/techdou/idle.webp', ... },
      quotes: [...],
    },
    {
      id: 'douknow',
      name: '豆懂AI',
      frames: { idle: './assets/douknow/idle.webp', ... },
      quotes: [...],
    }
  ]
};
```

The multi-skin installer:
1. Determines the new skin's id (from `plan.skinId`, or derived from `plan.character`).
2. Creates `pet/assets/<skinId>/` and copies generated sprites there.
3. Appends a new skin object to the `skins` array in `pet.js` (using balanced-bracket scanning to locate the array).
4. Backs up `pet.js` → `pet.js.bak`.

The new skin object includes `id`, `name`, `frames` (with cache-busting `?v=1`), `quotes`, plus any extras from plan (`startXRatio`, `idleVariants`, `idleEvents`).

## Frame naming convention

File names use kebab-case (`walk-left-1.png`), config keys use camelCase (`walkLeft1`). The multi-skin installer auto-converts. Frame key set depends on `plan.frameSet`:
- `base8`: 8 classic keys
- `extended16`: 16 keys (base8 + idleThink/idleLook/walkLeft2/walkRight2/walkBack2/sleep2/wave/happy)
- custom: whatever `plan.frames` defines

## Direction constraints

- `walk-left-*.png`: side profile facing left.
- `walk-right-*.png`: side profile facing right.
- `walk-front-*.png`: front view alternate walking frames.
- `walk-back-*.png`: back view walking frame.

## Config fields updated by this skill

- canvas-pet: `frames`, `quotes`, `baseSize` in pet.config.js
- multi-skin: appends new skin object (id/name/frames/quotes/extras) to pet.js skins array

It must not modify runtime engine logic (state machine, getCurrentFrame, etc.).

## Required frame keys

`pet.config.js` must expose a flat `frames` object with these 8 required keys:

```js
frames: {
  idle: './assets/pet/idle.png',
  idleWink: './assets/pet/idle-wink.png',
  walkFront1: './assets/pet/walk-front-1.png',
  walkFront2: './assets/pet/walk-front-2.png',
  walkLeft: './assets/pet/walk-left-1.png',
  walkRight: './assets/pet/walk-right-1.png',
  walkBack: './assets/pet/walk-back-1.png',
  sleep: './assets/pet/sleep.png',
}
```

## Optional frame key

`cloud` is optional. If present, it usually looks like:

```js
frames: {
  cloud: './assets/pet/cloud.png',
}
```

If `cloud` already exists and a new cloud is not generated, the installer preserves the existing `cloud` entry.

## Generated file names

Required:

```text
idle.png
idle-wink.png
walk-front-1.png
walk-front-2.png
walk-left-1.png
walk-right-1.png
walk-back-1.png
sleep.png
```

Optional:

```text
cloud.png
```

## Direction constraints

- `walk-left-1.png`: side profile facing left.
- `walk-right-1.png`: side profile facing right.
- `walk-front-1.png` and `walk-front-2.png`: front view alternate walking frames.
- `walk-back-1.png`: back view walking frame.

## Config fields updated by this skill

The installer updates only:

- `frames`
- `quotes`
- `baseSize`

It must not modify runtime engine files such as `pet.js`.
