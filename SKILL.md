---
name: pet-reskin
description: >-
  为 canvas-pet 桌宠模板生成一整套全新的角色形象（9 张精灵图 + 配置），并把它们
  安装进一个 canvas-pet 项目。当用户想「给桌宠换个皮肤」「生成一只新宠物」「做一个
  新的 canvas-pet 角色」「换皮」「设计一个 pet 形象」，或提供了角色描述（如「一只
  戴眼镜的猫」「赛博朋克机器人」）并提到 canvas-pet / 桌宠时，使用本 skill。即使用户
  没明说「换皮」，只要上下文是围绕 canvas-pet 创建新角色，也应触发。
---

# pet-reskin — 为 canvas-pet 生成新桌宠形象

本 skill 接收一段角色描述（自然语言），生成一套 9 张风格一致的精灵图（透明 PNG），
自动改写目标 canvas-pet 项目的 `pet.config.js`，让新角色立即可用。

## 你（模型）的职责

1. 与用户确认角色设定，把自然语言整理成 `plan.json`。
2. 调用 `scripts/generate_sprites.py` 生成精灵图。
3. 调用 `scripts/apply_config.py` 安装到目标项目。
4. 引导用户本地预览验证。

不要自己手写图片生成代码或手抠透明——这些已经封装在脚本里。你的核心价值是把模糊的
角色描述翻译成**精准、可视化、一致性强的** plan。

## 前置检查（每次都做）

1. **API key**：确认环境变量 `GEMINI_API_KEY` 已设置。未设置则停下，告诉用户去
   https://aistudio.google.com/ 取免费 key，并给出设置命令（Windows CMD：
   `set GEMINI_API_KEY=...`；PowerShell：`$env:GEMINI_API_KEY="..."`）。
2. **目标项目**：确认用户要把新形象装进哪个 canvas-pet 项目目录。若用户没指定，
   先问；不要假设默认路径。目标目录应包含 `pet.config.js` 和 `assets/pet/`。
3. **Python + Pillow**：脚本需要 Python 3.6+ 和 Pillow。若 `python -c "import PIL"`
   失败，提示 `pip install Pillow`。

## 第一步：把描述整理成 plan.json

读 `references/character-prompt-guide.md` 了解 description / style / quotes 的写法要点，
然后向用户收集或推断以下信息，写成 JSON：

```json
{
  "character": "角色名/身份",
  "description": "可量化的外观特征：体型、主辅配色、标志特征、表情",
  "style": "美术风格关键词（默认：现代扁平矢量插画，柔和描边）",
  "baseSize": 88,
  "quotes": ["金句1", "金句2"]
}
```

**description 的质量决定 9 张图的一致性。** 给可视化特征，不给抽象形容词。
- 好：「圆滚滚的橘色虎斑猫，绿眼睛，短腿，尾巴翘起，肚皮白色，鼻头粉色，头顶一撮呆毛」
- 差：「可爱的、萌萌的小猫」

如果用户的描述太简略（只有「一只猫」），主动追问 2–3 个关键特征再生成，
而不是直接跑脚本——跑一次要生成 9 张图，返工成本高。

把 plan 写到一个临时文件，例如 `<工作目录>/plan.json`。可参考
`assets/example-plan.json`。

## 第二步：生成精灵图

```bash
python <skill-dir>/scripts/generate_sprites.py --skill-plan <工作目录>/plan.json --out <工作目录>/sprites
```

脚本会：
- 先生成一张角色立绘作为基准（`<out>/raw/_idol.png`）。
- 以立绘为参考图生成其余 8 张，保持一致性。
- 对每张做色键抠图（Gemini 不输出 alpha，脚本把纯色底转成透明）。
- 产出 9 张透明 PNG 到 `<out>/`，并写一份 `manifest.json`。

生成约需 2–5 分钟（9 次 API 调用）。告诉用户耐心等待。脚本对单张失败会跳过不中断。

生成后，**用 Read 工具看一两张成品 PNG**（如 `idle.png`、`walk-right-1.png`），
检查角色是否一致、朝向是否正确。`walk-right-1.png` 必须是朝右的——canvas-pet 引擎
不做运行时镜像，方向错了右行会「倒退」。

## 第三步：安装到目标项目

```bash
python <skill-dir>/scripts/apply_config.py --manifest <工作目录>/sprites/manifest.json --sprites <工作目录>/sprites --target <canvas-pet 项目根>
```

脚本会：
- 把 9 张 PNG 复制到 `<target>/assets/pet/`（覆盖同名旧图）。
- 改写 `<target>/pet.config.js`：替换 `frames` 路径，并按 plan 覆盖 `quotes` / `baseSize`。

`<skill-dir>` 是本 skill 所在目录（即本 SKILL.md 的父目录）。

## 第四步：验证

让用户在目标项目根目录起服务预览：

```bash
npx serve .
# 打开 http://localhost:3000/pet.html 或 /index.html
```

重点看：
- 各方向行走朝向正确（尤其右行）。
- 金句气泡文案符合预期。
- 云朵（`cloud.png`）位置合适，必要时调 `pet.config.js` 的 `cloudScaleW/cloudScaleH/cloudOffsetY`。
- 角色尺寸是否合适，必要时调 `baseSize`。

## 失败与迭代

- **某张图方向/姿态不对**：单独重跑——把 `plan.json` 设 `"reuse_idol": true, "reuse_existing": true`，
  删掉那张成品图再跑（脚本会只补缺的）。
- **整体不满意**：改 `description` 重跑（`reuse_idol: false` 会重新生成基准立绘）。
- **背景抠不干净**：通常是角色含绿色——改 `generate_sprites.py` 顶部的 `KEY_COLOR`/`KEY_HEX`
  为角色不用的对比色（见 `character-prompt-guide.md` 末尾）。
- **限流（429）**：脚本自动等待重试；若仍频繁，让用户歇几分钟或换更高配额的 key。

## 不要做的事

- 不要手写调 Gemini API 的代码——用脚本。
- 不要生成后不验证就宣称完成——至少 Read 一张图确认。
- 不要改动 canvas-pet 的 `pet.js`（引擎）；所有个性化都通过 `pet.config.js` 表达。
- 不要假设目标项目路径——先问用户。

## 关于 canvas-pet 模板契约

精灵图的命名、方向约束、配置字段对应关系定义在 canvas-pet 项目的
`docs/reskin.md`。本 skill 的 `SPRITES` 表与之严格一致。若模板契约变更，
以目标项目里的 `docs/reskin.md` 为准。
