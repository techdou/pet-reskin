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
  "keyColor": "#78C878",
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
| `keyColor` | no | Chroma-key background hex (`#RRGGBB`). Default `#78C878` (green). Change to a color the character does **not** use when the character is green-ish; see collision note below. |
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

## Chroma key & color collision

生成器让模型把角色画在纯色 `keyColor`（默认 `#78C878` 绿）背景上，再用 alpha 平滑渐变 + 去溢色把背景抠透明。渐变区间写死（背景色附近 30 以内全透、120 以外全不透、中间渐变），因为抗锯齿过渡带宽度是图像生成固有的，与角色颜色无关。

真正影响抠图质量的是 **keyColor 与角色色的接近程度**——如果角色本身偏绿（绿皮史莱克、绿色机器人），它的颜色会落在背景色的渐变带内，被误抠成半透明，调阈值救不回来。所以脚本在生成 idol 后、生成 8 张精灵图之前会**自动诊断撞色**：统计角色像素里有多少比例落入渐变带，超过 15% 就判定撞色，直接报错停下，并给出可操作建议。

撞色时的修法：在 `plan.json` 里把 `keyColor` 换成角色不用的对比色。常见对照：

| 角色主色调 | 推荐 keyColor |
|---|---|
| 绿色系（默认撞色） | `#FF00FF` 品红 |
| 红色系 | `#00FFFF` 青 |
| 蓝色系 | `#FFFF00` 黄 |
| 紫色系 | `#FFFF00` 黄 |

改了 `keyColor` 后，生成器会要求模型用新背景色作画，抠图、去溢色、撞色诊断都自动按新颜色走，无需改代码。
