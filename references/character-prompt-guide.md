# Character Prompt Guide

Use this file when turning a vague character idea into a stable `plan.json`.

## Plan schema

```json
{
  "character": "小橘猫「栗子」",
  "description": "圆滚滚的橘色虎斑猫，大而圆的绿眼睛，短粗四肢，尾巴向上翘起，肚皮和嘴部白色，鼻头粉色，头顶一撮呆毛",
  "style": "现代扁平矢量插画，柔和的深棕色描边，配色温暖明亮",
  "baseSize": 88,
  "quotes": ["今天也要好好吃饭。", "别催，在想了。"],
  "reuse_idol": false,
  "reuse_existing": false
}
```

| Field | Required | Purpose |
|---|---:|---|
| `character` | yes | Character name or identity. |
| `description` | yes | Visual identity: body shape, colors, features, expression, outfit. |
| `style` | no | Art direction. Default should be flat/vector desktop-pet style. |
| `baseSize` | no | Size written to `pet.config.js`. Usually 72–110. |
| `quotes` | no | Speech bubble lines. Keep each line short. |
| `reuse_idol` | no | Reuse the cached idol reference at `<out>/idol.png` (and its raw original at `<out>/raw/idol.png`) during iteration. |
| `reuse_existing` | no | Skip finished PNG files during iteration. |

## Good descriptions

The description must be visual, not abstract.

Good:

```text
圆滚滚的橘色虎斑猫，大而圆的绿眼睛，短粗四肢，尾巴向上翘起，肚皮和嘴部为白色，鼻头粉色，头顶一撮翘起的呆毛。
```

Weak:

```text
一只可爱的小猫。
```

## Ask at most three clarification questions

Ask only when generation would be unstable. Good questions:

1. 主体是什么动物/角色？
2. 主色和辅色是什么？
3. 有什么一眼能认出的标志特征？

If the user already supplied these details, do not ask again.

## Animal template

```json
{
  "character": "角色名",
  "description": "物种 + 体型 + 主色 + 辅色 + 眼睛 + 尾巴/耳朵 + 标志特征 + 表情",
  "style": "现代扁平矢量插画，柔和描边，适合作为网页桌宠"
}
```

## Robot/IP template

```json
{
  "character": "角色名",
  "description": "小型机器人，圆角机身，主色，灯光颜色，屏幕表情，标志配件，动作气质",
  "style": "简洁科技感矢量插画，柔和描边，低饱和配色"
}
```

## Style menu

Use combinations like:

- `flat vector illustration`
- `sticker style`
- `chibi proportions`
- `clean outlines`
- `soft cel shading`
- `pastel colors`
- `warm palette`

Avoid:

- `photorealistic`
- `3D render`
- complex scenery
- strong shadows
- text inside the image

## Quote guidance

- 6–12 lines is enough.
- 8–16 Chinese characters per line is ideal.
- Match the character personality.
- Avoid long paragraphs because bubbles become noisy.

## Chroma key note

The generator asks Gemini to draw on `#78C878` and removes pixels near that color. Keying uses a **smooth alpha gradient** (not a hard threshold) so anti-aliased edges fade out cleanly instead of leaving a green halo:

- pixels within `PET_RESKIN_KEY_INNER` (default 30) of `#78C878` → fully transparent
- pixels beyond `PET_RESKIN_KEY_OUTER` (default 120) → fully opaque
- in between → linear alpha gradient, plus a despill pass that suppresses residual green in edge pixels

If the character itself is green, change `KEY_COLOR` and `KEY_HEX` in `scripts/generate_sprites.py` to a color the character does not use.
