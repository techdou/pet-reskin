# pet-reskin

> 一个 ZCode / Claude Code skill：为 [canvas-pet](../canvas-pet) 桌宠模板生成一整套全新的角色形象。

给它一段角色描述（「一只戴圆框眼镜的橘猫」「赛博朋克小机器人」），它会生成 9 张风格一致的透明精灵图，自动改写 canvas-pet 项目的 `pet.config.js`，让新角色立即可用。

## 它解决什么问题

canvas-pet 是一个「一行 iframe 嵌入的桌宠」模板，但默认只有一套角色皮肤。想换形象，得手动准备 9 张精灵图（idle / walk×4 方向×帧 / sleep / wink / cloud）、保证方向正确、保持风格一致、抠成透明 PNG、再改配置——流程繁琐且容易出错。本 skill 把这套流程自动化。

## 工作原理

1. 用 Google Gemini 3 Pro Image（`gemini-3-pro-image-preview`）生成一张角色**立绘**作为基准。
2. 以立绘为参考图生成其余 8 张精灵，利用 Pro 模型的参考图混合能力保持角色一致性。
3. 对每张做色键抠图（Gemini 不输出 alpha 通道，脚本把纯色底转成透明）。
4. 复制到目标项目的 `assets/pet/` 并改写 `pet.config.js`。

## 安装

把本目录复制（或软链）到 skills 发现路径之一：

```
~/.agents/skills/pet-reskin/        # 推荐：跨项目可用
<project>/.agents/skills/pet-reskin/  # 仅当前项目
```

安装后，在 ZCode / Claude Code 里说「帮我给 canvas-pet 做一只新桌宠，要一只……」即可触发。

## 依赖

- Python 3.6+
- Pillow（`pip install Pillow`）
- `GEMINI_API_KEY` 环境变量（[免费获取](https://aistudio.google.com/)）

> 图像生成走 Gemini REST API，**仅用 Python 标准库**（`urllib`），无需安装 google-genai SDK。

## 结构

```
pet-reskin/
├── SKILL.md                          # skill 定义（模型读这个）
├── scripts/
│   ├── generate_sprites.py           # 生成 9 张精灵图
│   └── apply_config.py               # 安装到目标项目 + 改写配置
├── references/
│   └── character-prompt-guide.md     # 角色 description / style / quotes 写法
├── assets/
│   └── example-plan.json             # plan.json 示例
└── LICENSE
```

## 手动使用脚本（脱离 skill 也能跑）

```bash
# 1. 写 plan.json（参考 assets/example-plan.json）

# 2. 生成精灵图
python scripts/generate_sprites.py --skill-plan plan.json --out ./sprites

# 3. 安装到 canvas-pet 项目
python scripts/apply_config.py --manifest ./sprites/manifest.json --sprites ./sprites --target /path/to/canvas-pet
```

## 与 canvas-pet 的关系

本 skill 严格遵循 canvas-pet 的 `docs/reskin.md` 模板契约（精灵图命名、方向约束、配置字段）。canvas-pet 是运行时模板，pet-reskin 是它的换皮工具链。两者可独立使用，但配合最佳。

## 许可证

MIT。
