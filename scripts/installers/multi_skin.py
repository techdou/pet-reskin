"""multi-skin installer：多皮肤架构（pet.js 含 PET_CONFIG.skins 数组 + pet/assets/<skin>/）。

适用项目如 techdou-profile：pet.js 里有一个 skins 数组，每个皮肤独立 frames/quotes，
图片放在 pet/assets/<skin-id>/ 下。

安装流程：
1. 按 manifest.character 或 plan.skinId 确定新皮肤的 id（目录名）
2. 把生成的图拷到 target/pet/assets/<skin-id>/
3. 在 pet.js 的 skins 数组末尾追加新皮肤对象（用平衡括号扫描定位数组闭合位置）
4. 备份 pet.js → pet.js.bak
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _find_balanced_array(text: str, kw_pattern: str, label: str) -> Tuple[int, int]:
    """定位 `kw_pattern: [ ... ]`，返回 (关键字起始索引, 闭合 ] 后一位)。

    用平衡扫描代替正则，避免 frames 值里含 ] 时误匹配。
    """
    start_match = re.search(kw_pattern + r"\s*:\s*\[", text)
    if not start_match:
        raise RuntimeError(f"could not find {label} array")
    kw_start = start_match.start()
    bracket_start = start_match.end() - 1
    depth = 0
    i = bracket_start
    in_str: Optional[str] = None
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"'):
                in_str = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return kw_start, i + 1
        i += 1
    raise RuntimeError(f"unbalanced [] in {label}")


def _frames_block(frames: Dict[str, str], indent: str = "        ") -> str:
    """生成 skin 对象里的 frames 块（8 空格缩进，对应 skin 对象内部）。"""
    lines = ["frames: {"]
    for key, value in frames.items():
        lines.append(f"{indent}  {key}: {json.dumps(value, ensure_ascii=False)},")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def _quotes_block(quotes: List[str], indent: str = "        ") -> str:
    """生成 skin 对象里的 quotes 数组块。"""
    if not quotes:
        return "quotes: []"
    lines = ["quotes: ["]
    for q in quotes:
        lines.append(f"{indent}  {json.dumps(q, ensure_ascii=False)},")
    lines.append(f"{indent}]")
    return "\n".join(lines)


def _camel_key(kebab: str) -> str:
    """'idle-think' → 'idleThink'，'walk-left-1' → 'walkLeft1'：kebab-case → camelCase。

    匹配 -后任意字母数字字符（不只字母），因为文件名如 walk-left-1 的数字段也要处理。
    """
    return re.sub(r"-([a-z0-9])", lambda m: m.group(1).upper(), kebab, flags=re.IGNORECASE)


def build_skin_object(
    skin_id: str,
    name: str,
    frames: Dict[str, str],
    quotes: List[str],
    base_size: Optional[int] = None,
    extras: Optional[Dict[str, Any]] = None,
    indent: str = "      ",
) -> str:
    """构造一个完整的 skin 对象字符串（6 空格缩进，对应 skins 数组元素）。

    frames 是 {frame_key: file_path} 映射；file_path 相对 target 根目录。
    extras 允许传入 startXRatio/cloudScaleW 等额外字段。
    """
    lines = [f"{indent}{{"]
    lines.append(f"{indent}  id: {json.dumps(skin_id, ensure_ascii=False)},")
    lines.append(f"{indent}  name: {json.dumps(name, ensure_ascii=False)},")
    if extras:
        for k, v in extras.items():
            if isinstance(v, str):
                lines.append(f"{indent}  {k}: {json.dumps(v, ensure_ascii=False)},")
            elif isinstance(v, bool):
                lines.append(f"{indent}  {k}: {'true' if v else 'false'},")
            elif v is not None:
                lines.append(f"{indent}  {k}: {json.dumps(v, ensure_ascii=False)},")
    # quotes 块（8 空格缩进）
    qb = _quotes_block(quotes, indent=indent + "  ")
    for line in qb.split("\n"):
        lines.append(f"{indent}  {line}" if not line.startswith("quotes") else f"{indent}  {line}")
    # frames 块（8 空格缩进）
    fb = _frames_block(frames, indent=indent + "  ")
    for line in fb.split("\n"):
        lines.append(f"{indent}  {line}" if not line.startswith("frames") else f"{indent}  {line}")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def _resolve_skin_id(manifest: Dict[str, Any], plan: Dict[str, Any]) -> str:
    """决定新皮肤的 id（用作 assets 子目录名 + pet.js 里的 id 字段）。

    优先级：plan.skinId > plan.character 的英文/pinyin 化 > 'newskin'
    """
    if plan.get("skinId"):
        return str(plan["skinId"])
    char = manifest.get("character") or plan.get("character") or "newskin"
    # 简单处理：中文等非 ASCII 字符保留原样做 id（文件系统支持），但去掉空格
    return re.sub(r"\s+", "", str(char)).lower()


def install_multi_skin(
    manifest: Dict[str, Any],
    sprites_dir: Path,
    target: Path,
    plan: Dict[str, Any],
    allow_partial: bool = False,
    dry_run: bool = False,
    no_backup: bool = False,
) -> Dict[str, Any]:
    """把生成的 sprite 安装到 multi-skin 项目（追加 skin 到 pet.js + 拷图到 assets/<skin>/）。"""
    pet_js = target / "pet.js"
    if not target.exists():
        return {"ok": False, "errors": [f"target does not exist: {target}"]}
    if not pet_js.exists():
        return {"ok": False, "errors": [f"target is missing pet.js: {pet_js}"]}

    skin_id = _resolve_skin_id(manifest, plan)
    skin_name = plan.get("skinName") or manifest.get("character") or skin_id
    assets_skin = target / "pet" / "assets" / skin_id

    # 拷贝图片到 pet/assets/<skin-id>/
    copied: List[str] = []
    for fname in manifest.get("files", []):
        source = sprites_dir / fname
        if not source.exists():
            if not allow_partial:
                return {"ok": False, "errors": [f"sprite listed in manifest is missing: {source}"]}
            continue
        if not dry_run:
            assets_skin.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, assets_skin / fname)
        copied.append(fname)

    # 构造新 skin 的 frames 映射（文件名相对 target 根，带 cache-busting 版本号）
    frames_map: Dict[str, str] = {}
    for frame_key, file_path in manifest.get("frames", {}).items():
        # file_path 形如 "./assets/pet/idle.png"，改成 multi-skin 路径
        fname = Path(file_path).name
        camel = _camel_key(Path(fname).stem)
        # multi-skin 路径 + 版本号（避免缓存问题）
        rel = f"./assets/{skin_id}/{fname}?v=1"
        frames_map[camel] = rel

    extras: Dict[str, Any] = {}
    if "startXRatio" in plan:
        extras["startXRatio"] = plan["startXRatio"]
    if plan.get("idleVariants"):
        extras["idleVariants"] = plan["idleVariants"]
    if plan.get("idleEvents"):
        extras["idleEvents"] = plan["idleEvents"]

    skin_block = build_skin_object(
        skin_id=skin_id,
        name=skin_name,
        frames=frames_map,
        quotes=manifest.get("quotes") or plan.get("quotes") or [],
        extras=extras,
    )

    # 读取 pet.js，定位 skins 数组，在闭合 ] 前追加新 skin
    original = pet_js.read_text(encoding="utf-8")
    try:
        sk_start, sk_end = _find_balanced_array(original, r"skins", "skins")
    except RuntimeError as exc:
        return {"ok": False, "errors": [f"pet.js 里找不到 skins 数组: {exc}"]}

    # array_segment 是 original[sk_start:sk_end]，形如 "skins: [\n      {...},\n      {...}\n    ]"
    array_segment = original[sk_start:sk_end]
    # 找到最后一个 ]（数组闭合符）的位置
    close_idx = array_segment.rfind("]")
    if close_idx == -1:
        return {"ok": False, "errors": ["skins 数组结构异常：找不到闭合 ]"]}
    # 闭合 ] 之前的内容，去掉尾随空白
    before_close = array_segment[:close_idx].rstrip()
    # 去掉尾随逗号（如果有），统一由我们控制
    if before_close.endswith(","):
        before_close = before_close[:-1].rstrip()
    # 重建数组：原内容 + 逗号 + 新 skin + 闭合 ]
    # 缩进用 6 空格（对应 skins 数组元素的缩进）
    new_array = before_close + ",\n" + skin_block + "\n    ]"
    updated = original[:sk_start] + new_array + original[sk_end:]

    summary: Dict[str, Any] = {
        "ok": True,
        "dryRun": dry_run,
        "targetType": "multi_skin",
        "target": str(target),
        "skinId": skin_id,
        "copied": copied,
        "config": str(pet_js),
        "warnings": [],
    }

    if dry_run:
        summary["previewSkinBlock"] = skin_block
        return summary

    if not no_backup:
        backup_path = pet_js.with_suffix(pet_js.suffix + ".bak")
        shutil.copy2(pet_js, backup_path)
        summary["backup"] = str(backup_path)
    pet_js.write_text(updated, encoding="utf-8")
    return summary
