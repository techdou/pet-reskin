# 角色提示词指南

本文件帮助 skill 把用户的角色描述翻译成高质量的 `generate_sprites.py` 计划。
模型在需要细化角色风格、风格关键词或文案时阅读本文件。

## plan.json 结构

`generate_sprites.py --skill-plan` 接收一个 JSON：

```json
{
  "character": "小橘猫「栗子」",
  "description": "一只圆滚滚的橘色虎斑猫，大眼睛，短腿，尾巴翘起，肚皮白色",
  "style": "现代扁平矢量插画，柔和的描边，配色温暖",
  "baseSize": 88,
  "quotes": [
    "今天也要好好吃饭。",
    "摸鱼是人类进步的阶梯。"
  ],
  "reuse_idol": false,
  "reuse_existing": false
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `character` | 是 | 角色名 / 身份，会嵌进提示词。如「小橘猫栗子」「一只赛博朋克机器人」。 |
| `description` | 是 | 外观细节：体型、配色、服饰、表情特征。越具体，一致性越好。 |
| `style` | 否 | 美术风格关键词。默认「现代扁平矢量插画」。 |
| `baseSize` | 否 | 写入 pet.config.js 的尺寸，默认沿用模板的 88。 |
| `quotes` | 否 | 金句气泡文案，写入 pet.config.js。建议 6–12 条，贴合角色性格。 |
| `reuse_idol` | 否 | true 时复用已有立绘不重新生成（调试/迭代用）。 |
| `reuse_existing` | 否 | true 时跳过已存在的成品图。 |

## description 怎么写

一致性靠 `description` 承载。给出**可量化、可视化的特征**，而非抽象感觉。

好的写法：
- 体型：「圆滚滚的矮胖体型」「修长的狐狸身材」
- 主色 + 辅色：「橘色为主，肚皮和爪尖白色，鼻头粉色」
- 标志性特征：「头顶有一片闪电状的呆毛」「戴一副圆框眼镜」
- 表情：「眼睛又大又圆，总是微张着嘴」

差的写法（太抽象，模型每次画得不一样）：
- 「可爱的」「酷酷的」「有科技感的」

## style 关键词菜单

按需组合，风格统一是 9 张图一致性的关键：

- **插画类**：flat vector illustration / chibi style / sticker style / kawaii
- **质感**：clean outlines / soft cel shading / no outline / thick outline
- **配色**：warm palette / pastel colors / high contrast / monochrome
- **避免**：不要写「photorealistic / 3D render」——精灵图与桌宠场景不搭。

## quotes 怎么写

- 长度：8–16 字一句最合适（气泡会自动换行，但太长不好看）。
- 语气：贴合角色性格。猫可以慵懒、机器人可以机械冷幽默、学者可以引用风。
- 中英可混排，引擎逐字测量宽度，不会乱排。

## 常见问题

**Q: 9 张图角色长得不太像？**
A: `description` 加更多固定特征；确认立绘 `_idol.png` 生成成功（它是其余 8 张的参考基准）。Pro 模型支持参考图，但不是 100% 复刻，特征越鲜明越稳。

**Q: 背景没抠干净 / 角色里有绿色？**
A: 色键用的是中绿 `#78C878`，提示词已要求角色不出现该色。如果角色本身就是绿色系（如青蛙、绿龙），改 `generate_sprites.py` 的 `KEY_COLOR` 为角色不用的对比色（如品红 `(200,120,200)`）并同步 `KEY_HEX`。
