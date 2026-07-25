"""帧模板加载器：解析 plan.frameSet / plan.frames，返回最终帧清单。

支持三种来源（优先级从高到低）：
1. plan.frames: 完全自定义帧清单（数组）
2. plan.frameSet: "base8" | "extended16"（从 frame-templates.json 加载）
3. 默认: base8（向后兼容）

每个帧 spec: {frame, file, role, needsRef, pose}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

# 内置模板路径
TEMPLATES_PATH = Path(__file__).parent.parent / "assets" / "frame-templates.json"

# 向后兼容：老 BASE_SPRITES / OPTIONAL_SPRITES 定义（generate_sprites.py 老代码引用）
# 现在改成从模板加载，但保留这两个常量做 fallback
LEGACY_BASE_SPRITES = [
    {"frame": "idle", "file": "idle.png", "role": "idle", "needsRef": True},
    {"frame": "idleWink", "file": "idle-wink.png", "role": "wink", "needsRef": True},
    {"frame": "walkFront1", "file": "walk-front-1.png", "role": "walk_front_1", "needsRef": True},
    {"frame": "walkFront2", "file": "walk-front-2.png", "role": "walk_front_2", "needsRef": True},
    {"frame": "walkLeft", "file": "walk-left-1.png", "role": "walk_left", "needsRef": True},
    {"frame": "walkRight", "file": "walk-right-1.png", "role": "walk_right", "needsRef": True},
    {"frame": "walkBack", "file": "walk-back-1.png", "role": "walk_back", "needsRef": True},
    {"frame": "sleep", "file": "sleep.png", "role": "sleep", "needsRef": True},
]
LEGACY_OPTIONAL_SPRITES = [
    {"frame": "cloud", "file": "cloud.png", "role": "cloud", "needsRef": False},
]


def load_templates() -> Dict[str, Any]:
    """加载 frame-templates.json。"""
    if not TEMPLATES_PATH.exists():
        return {"templates": {}, "cloudFrame": LEGACY_OPTIONAL_SPRITES[0]}
    return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))


def resolve_frames(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析 plan，返回基础帧清单（不含 cloud）。

    优先级：plan.frames（自定义数组）> plan.frameSet（模板名）> base8 默认
    """
    # 1. 完全自定义帧清单
    custom_frames = plan.get("frames")
    if isinstance(custom_frames, list) and custom_frames:
        return [_normalize_frame(f) for f in custom_frames]

    # 2. 模板名
    frame_set = plan.get("frameSet", "base8")
    templates = load_templates().get("templates", {})
    if frame_set in templates:
        return list(templates[frame_set]["frames"])

    # 3. 兼容老 plan：无 frameSet 字段时走 legacy base8
    if frame_set == "base8" and "base8" not in templates:
        return list(LEGACY_BASE_SPRITES)

    raise ValueError(
        f"unknown frameSet: {frame_set!r}. "
        f"Available templates: {list(templates.keys())}. "
        f"Or set plan.frames to a custom frame array."
    )


def get_cloud_frame() -> Dict[str, Any]:
    """返回 cloud 帧的 spec（可选帧）。"""
    templates = load_templates()
    cloud = templates.get("cloudFrame")
    if cloud:
        return cloud
    return dict(LEGACY_OPTIONAL_SPRITES[0])


def _normalize_frame(f: Any) -> Dict[str, Any]:
    """把用户自定义帧 spec 标准化（补全缺省字段）。"""
    if isinstance(f, dict):
        return {
            "frame": f["frame"],
            "file": f["file"],
            "role": f.get("role", f["frame"]),
            "needsRef": f.get("needsRef", True),
            "pose": f.get("pose", ""),
        }
    raise ValueError(f"invalid frame spec: {f!r} (must be a dict with frame/file)")
