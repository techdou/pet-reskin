#!/usr/bin/env python3
"""
apply_config.py — 把生成的精灵图复制到目标 canvas-pet 项目，并改写 pet.config.js。

读取 generate_sprites.py 产出的 manifest.json，把精灵图复制到
<target>/assets/pet/，并把 pet.config.js 的 frames 字段替换为 manifest 里的路径，
同时用 plan 里的 quotes / baseSize 覆盖对应字段（如果 plan 提供）。

用法：
  python apply_config.py --manifest <manifest.json> --sprites <精灵目录> \
                         --target <canvas-pet 项目根>
"""

import argparse
import json
import re
import shutil
from pathlib import Path


def update_config(config_path, manifest, plan):
    """改写 pet.config.js 的 frames / quotes / baseSize。
    用字符串替换避免重排用户其余字段。
    """
    text = config_path.read_text(encoding="utf-8")

    frames_block = "frames: {\n"
    for k, v in manifest["frames"].items():
        frames_block += f"    {k}: '{v}',\n"
    frames_block += "  }"

    # 替换整个 frames: { ... } 块（非贪婪到第一个闭合的 }）
    text = re.sub(r"frames:\s*\{.*?\n\s*\},", frames_block + ",", text, count=1, flags=re.DOTALL)

    # quotes（可选）
    if plan.get("quotes"):
        q = ", ".join(json.dumps(q, ensure_ascii=False) for q in plan["quotes"])
        qblock = f"quotes: [{q}]"
        # 替换 quotes: [ ... ]（跨行）
        text = re.sub(r"quotes:\s*\[.*?\]", qblock, text, count=1, flags=re.DOTALL)

    # baseSize（可选）
    if plan.get("baseSize"):
        text = re.sub(r"baseSize:\s*\d+", f"baseSize: {int(plan['baseSize'])}", text, count=1)

    config_path.write_text(text, encoding="utf-8")
    print(f"✓ 已更新 {config_path.name}（frames / {('quotes ' if plan.get('quotes') else '')}{('baseSize' if plan.get('baseSize') else '')}）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sprites", required=True, help="精灵图所在目录")
    ap.add_argument("--target", required=True, help="canvas-pet 项目根")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    target = Path(args.target)
    assets_pet = target / "assets" / "pet"
    assets_pet.mkdir(parents=True, exist_ok=True)

    # 复制精灵图
    src_dir = Path(args.sprites)
    copied = []
    for fname in manifest["files"]:
        s = src_dir / fname
        if not s.exists():
            print(f"  ⚠ 缺失，跳过: {fname}", flush=True)
            continue
        d = assets_pet / fname
        shutil.copy2(s, d)
        copied.append(fname)
    print(f"✓ 复制 {len(copied)} 张精灵图 → {assets_pet}")

    # 改写 pet.config.js
    config_path = target / "pet.config.js"
    if not config_path.exists():
        print(f"⚠ 未找到 {config_path}，跳过配置改写")
        return

    # 尝试读 plan（与 manifest 同目录的 plan.json）
    plan_path = src_dir / "plan.json"
    plan = {}
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))

    update_config(config_path, manifest, plan)


if __name__ == "__main__":
    main()
