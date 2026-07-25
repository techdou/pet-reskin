# Changelog

## 2.0.0

### Summary

通用化改造：从「canvas-pet 单皮肤专用 + Gemini only + 固定 8 帧」升级为「通用 pet reskin 工具」。支持多项目架构、双 provider、可配置帧清单、参考图直用。**完全向后兼容**——老 plan.json 和老 canvas-pet 项目不动也能跑。

### Added

- **双 provider 支持**：新增 `image2api` provider，封装 image2-api skill 的 image2lib（gpt-image-2 + 8 provider fallback 链）。`plan.provider` 字段切换（默认 `gemini`，可选 `image2api`）。
- **可配置帧清单**：`plan.frameSet` 支持 `base8`（默认）| `extended16`（含 idle 变体/walk 2 帧循环/sleep 2 帧/wave/happy）| 自定义 `plan.frames` 数组。新增 `assets/frame-templates.json` 内置两套模板。
- **参考图直用**：`plan.referenceImage` 支持已有参考图（如 cutout.png），跳过 idol 生成；`plan.referenceAsIdle` 直接把参考图当 idle 帧，省 2 次调用。
- **白底抠图策略**：`plan.background: "white"` 走白底 → 透明后处理（适配 gpt-image-2 不支持透明输出的限制）。原有 `chroma` 绿底策略不变。
- **多皮肤架构适配器**：新增 `multi_skin` installer，支持 `pet.js` 含 `PET_CONFIG.skins` 数组的项目（如 techdou-profile）。自动按 skin id 创建 `assets/<skin>/` 目录、在 skins 数组追加新皮肤。
- **target 类型自动探测**：`check_env.py` 和 `apply_config.py` 自动识别 canvas-pet（pet.config.js）或 multi-skin（pet.js skins 数组）。
- **image2-api 可用性检查**：`check_env.py` 探测 image2-api skill 位置并报告。
- 新增示例：`example-plan-extended.json`（16 帧 + referenceImage）、`example-plan-image2api.json`（image2api provider）。
- 新增模块：`scripts/providers/`、`scripts/installers/`、`scripts/background_removal.py`、`scripts/frames.py`。

### Changed

- `generate_sprites.py` 重构为双路径：新字段触发新模式（provider 抽象 + 可插拔抠图 + 帧模板 + referenceImage），无新字段走老模式（行为与 1.3.1 完全一致）。
- `apply_config.py` 改为薄封装，分发到 `installers/canvas_pet.py` 或 `installers/multi_skin.py`。
- `check_env.py` target 检查改为自动探测架构类型。

### Backward compatibility

- 老 plan.json（无新字段）→ 走 Gemini + base8 + chroma + 无 referenceImage，行为等同 1.3.1。
- 老 canvas-pet 项目（pet.config.js）→ 走 canvas_pet installer，行为等同 1.3.1。
- 现有 23 个单元测试全部通过。
- 所有老 CLI 参数保留，新增参数全部可选。

## 1.3.1

### Added

- `plan.keyColor` field (`#RRGGBB`) to override the chroma-key background color per character.
- Automatic color-collision detection: after the idol is generated, the script checks whether too many character pixels fall inside the chroma-key gradient band and stops with actionable advice before wasting the 8 sprite API calls.
- `manifest.json` now records the resolved `keyColor`.
- Unit tests for collision detection, custom keyColor, parameterized chroma_key, and hex parsing.

### Changed

- `chroma_key` now takes the key color as a parameter instead of reading module-level globals; prompt builders thread the key hex through so the model is told the correct background color.
- Despill is now channel-agnostic: it suppresses whichever channel dominates the key color (green/red/blue), so non-green key colors still get clean edges.
- Removed the `PET_RESKIN_KEY_INNER` / `PET_RESKIN_KEY_OUTER` environment variables. The gradient band is fixed (30–120) because edge anti-aliasing width is model-intrinsic; tuning thresholds could not save a true color collision anyway.
