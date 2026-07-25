"""Installer 抽象层：分发到 canvas_pet（单皮肤）或 multi_skin（多皮肤）适配器。

目标项目类型由 target 目录结构自动探测：
- 有 pet.config.js + flat frames 对象 → canvas_pet（原 canvas-pet 项目）
- 有 pet.js 且含 PET_CONFIG.skins 数组 → multi_skin（如 techdou-profile）

老 apply_config.py 的全部行为平移到 canvas_pet.py，保证向后兼容。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def detect_target_type(target: Path) -> str:
    """探测目标项目的皮肤架构类型。

    返回 "canvas_pet" | "multi_skin" | "unknown"
    """
    if not target.exists():
        return "unknown"
    if (target / "pet.config.js").exists():
        return "canvas_pet"
    # multi-skin：pet.js 里含 skins 数组（PET_CONFIG.skins）
    pet_js = target / "pet.js"
    if pet_js.exists():
        text = pet_js.read_text(encoding="utf-8")
        if "skins" in text and ("PET_CONFIG" in text or "skins:" in text):
            return "multi_skin"
    return "unknown"


def install(
    manifest: Dict[str, Any],
    sprites_dir: Path,
    target: Path,
    target_type: Optional[str] = None,
    plan: Optional[Dict[str, Any]] = None,
    allow_partial: bool = False,
    dry_run: bool = False,
    no_backup: bool = False,
) -> Dict[str, Any]:
    """统一安装入口。根据 target_type 分发到对应 installer。

    返回 summary dict（含 ok/copied/config/warnings/backup 等字段）。
    """
    if target_type is None:
        target_type = detect_target_type(target)

    if target_type == "canvas_pet":
        from .canvas_pet import install_canvas_pet
        return install_canvas_pet(
            manifest=manifest,
            sprites_dir=sprites_dir,
            target=target,
            plan=plan or {},
            allow_partial=allow_partial,
            dry_run=dry_run,
            no_backup=no_backup,
        )
    if target_type == "multi_skin":
        from .multi_skin import install_multi_skin
        return install_multi_skin(
            manifest=manifest,
            sprites_dir=sprites_dir,
            target=target,
            plan=plan or {},
            allow_partial=allow_partial,
            dry_run=dry_run,
            no_backup=no_backup,
        )
    raise RuntimeError(
        f"无法识别 target 类型: {target}\n"
        f"期望找到 pet.config.js（canvas-pet）或含 skins 数组的 pet.js（multi-skin）。"
    )
