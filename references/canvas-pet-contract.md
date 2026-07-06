# canvas-pet Contract

This file defines the minimum project contract expected by `pet-reskin`.

## Target project

The target project root must contain:

```text
pet.config.js
assets/pet/
```

`assets/pet/` may be created by the installer if missing, but `pet.config.js` must already exist.

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
