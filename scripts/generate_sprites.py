#!/usr/bin/env python3
"""
generate_sprites.py — 为 canvas-pet 模板生成一整套桌宠精灵图。

流程：
  1. 用 gemini-3-pro-image-preview 生成一张「立绘（idol sprite）」作为角色基准。
  2. 以这张立绘为参考图，逐张生成其余 8 张精灵（idle/walk×4/sleep/wink/cloud），
     保持角色一致性（Pro 模型支持参考图混合）。
  3. 对每张图做色键抠图：把纯色底变成透明（Gemini 不输出 alpha 通道）。
  4. 产出 9 张透明 PNG + 一份 manifest，供 SKILL 读取后写入目标项目的 pet.config.js。

用法：
  见 SKILL.md。脚本被 skill 调用，参数 --skill-plan 指向一个 JSON 计划文件。

环境变量：
  GEMINI_API_KEY  必填

零第三方依赖调用 API（仅标准库 urllib）。色键抠图依赖 Pillow。
"""

import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: 需要 Pillow。安装: pip install Pillow", file=sys.stderr)
    sys.exit(2)


# ---------- 配置 ----------

MODEL_ID = "gemini-3-pro-image-preview"
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL_ID}:streamGenerateContent"
)
IMAGE_SIZE = "1K"            # 1024 量级，方图够用且不慢
ASPECT = "1:1"               # 引擎按方图绘制
# 色键背景：让模型把角色画在这种纯色底上，便于事后抠成透明。
KEY_COLOR = (120, 200, 120)  # 中绿
KEY_HEX = "#78C878"
KEY_TOLERANCE = 42           # 与 KEY_COLOR 的 RGB 距离阈值，<= 视为背景
FEATHER = 1                  # 边缘羽化（像素）

# 9 张精灵的契约（与 canvas-pet/docs/reskin.md 一致）
SPRITES = [
    # key=pet.config frames 键; file=输出文件名; role=语义; needs_ref=是否传立绘参考
    {"frame": "idle",        "file": "idle.png",        "role": "idle",       "needs_ref": True},
    {"frame": "idleWink",    "file": "idle-wink.png",   "role": "wink",       "needs_ref": True},
    {"frame": "walkFront1",  "file": "walk-front-1.png","role": "walk_front_1","needs_ref": True},
    {"frame": "walkFront2",  "file": "walk-front-2.png","role": "walk_front_2","needs_ref": True},
    {"frame": "walkLeft",    "file": "walk-left-1.png", "role": "walk_left",  "needs_ref": True},
    {"frame": "walkRight",   "file": "walk-right-1.png","role": "walk_right", "needs_ref": True},
    {"frame": "walkBack",    "file": "walk-back-1.png", "role": "walk_back",  "needs_ref": True},
    {"frame": "sleep",       "file": "sleep.png",       "role": "sleep",      "needs_ref": True},
    {"frame": "cloud",       "file": "cloud.png",       "role": "cloud",      "needs_ref": False},
]


# ---------- Gemini API ----------

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("ERROR: 未设置 GEMINI_API_KEY 环境变量。", file=sys.stderr)
        print("获取免费 key: https://aistudio.google.com/", file=sys.stderr)
        sys.exit(1)
    return key


def call_gemini(api_key, parts, retries=2):
    """parts: list of {"text": ...} | {"inline_data": {"mime_type", "data"}}"""
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "imageConfig": {"image_size": IMAGE_SIZE},
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}?key={api_key}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read().decode("utf-8"))["error"]["message"]
            except Exception:
                pass
            if e.code == 429 and attempt < retries:
                wait = 10 * (attempt + 1)
                print(f"   ⚠ 限流，{wait}s 后重试… ({detail})", file=sys.stderr)
                time.sleep(wait)
                last_err = e
                continue
            print(f"ERROR: Gemini HTTP {e.code}: {detail}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"ERROR: 网络错误: {e.reason}", file=sys.stderr)
            sys.exit(1)
    print(f"ERROR: 重试耗尽: {last_err}", file=sys.stderr)
    sys.exit(1)


def extract_image_bytes(response):
    """从 streamGenerateContent 响应里取出第一张图的 bytes。"""
    if isinstance(response, list):
        response = response[0] if response else {}
    candidates = response.get("candidates", [])
    if not candidates:
        raise ValueError(f"无 candidates: {json.dumps(response)[:300]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    for p in parts:
        inline = p.get("inlineData") or p.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    raise ValueError("响应中没有图片数据（可能被安全过滤）")


# ---------- 提示词 ----------

def idol_prompt(plan):
    """生成角色立绘（基准）的提示词。"""
    name = plan.get("character", "the character")
    desc = plan.get("description", "")
    style = plan.get("style", "flat vector illustration, clean outlines")
    return (
        f"A single full-body character design of {name}. "
        f"{desc}. "
        f"Art style: {style}. "
        f"Standing, facing forward, centered, full body visible, head looking at viewer. "
        f"Draw the character on a SOLID flat {KEY_HEX} background (no gradient, no scenery). "
        f"No text, no shadows on the ground. The character must not use any color close to {KEY_HEX}."
    )


def sprite_prompt(plan, role):
    """生成单张精灵的提示词。role 见 SPRITES 的 role 字段。"""
    name = plan.get("character", "the same character")
    style = plan.get("style", "flat vector illustration, clean outlines")
    poses = {
        "idle":         "standing still facing forward, neutral relaxed pose",
        "wink":         "standing still facing forward, one eye closed in a friendly wink, same pose as idle",
        "walk_front_1": "walking towards the viewer, mid-stride, left leg forward (front view)",
        "walk_front_2": "walking towards the viewer, mid-stride, right leg forward (front view, alternate frame)",
        "walk_left":    "walking to the LEFT, side profile, mid-stride (the character faces left)",
        "walk_right":   "walking to the RIGHT, side profile, mid-stride (the character faces right)",
        "walk_back":    "walking away from the viewer, back view, mid-stride",
        "sleep":        "sleeping peacefully, eyes closed, curled or resting pose",
        "cloud":        "a soft fluffy white cloud seen from above, simple flat shape, isolated",
    }
    body = poses.get(role, poses["idle"])

    if role == "cloud":
        return (
            f"A single soft fluffy cloud, simple flat vector style, pure white with light grey shading, "
            f"no character. Draw on a SOLID flat {KEY_HEX} background."
        )

    return (
        f"Draw the SAME character as in the reference image: {name}. "
        f"Keep its appearance, colors, proportions, and art style ({style}) identical to the reference. "
        f"Pose: {body}. "
        f"Full body, centered, on a SOLID flat {KEY_HEX} background (no scenery, no ground shadow). "
        f"No text. The character must not use any color close to {KEY_HEX}."
    )


# ---------- 色键抠图 ----------

def chroma_key(src_bytes):
    """把 KEY_COLOR 附近的像素置为透明，其余保留。返回 RGBA PNG bytes。"""
    im = Image.open(io.BytesIO(src_bytes)).convert("RGB")
    w, h = im.size
    px = im.load()
    out = Image.new("RGBA", (w, h))
    ox = out.load()
    kr, kg, kb = KEY_COLOR
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if abs(r - kr) <= KEY_TOLERANCE and abs(g - kg) <= KEY_TOLERANCE and abs(b - kb) <= KEY_TOLERANCE:
                continue  # 透明
            ox[x, y] = (r, g, b, 255)
    # 简易羽化：把仍残留的边缘绿点（单独通道异常）压一下——可选，保持简单先不做复杂卷积。
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


# ---------- 主流程 ----------

def run(plan_path, out_dir):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    api_key = get_api_key()
    (out / "raw").mkdir(exist_ok=True)
    idol_path = out / "raw" / "_idol.png"

    # 1. 立绘（基准）
    if idol_path.exists() and plan.get("reuse_idol"):
        print("✓ 复用已有立绘 _idol.png")
        idol_bytes = idol_path.read_bytes()
    else:
        print("▶ 生成角色立绘（基准）…")
        resp = call_gemini(api_key, [{"text": idol_prompt(plan)}])
        idol_bytes = extract_image_bytes(resp)
        idol_path.write_bytes(idol_bytes)
        print(f"  立绘已存: {idol_path}")

    # 立绘转 base64 作为参考图
    idol_b64 = base64.b64encode(idol_bytes).decode()
    idol_part = {
        "inline_data": {"mime_type": "image/png", "data": idol_b64}
    }

    # 2. 逐张生成
    results = []
    for sp in SPRITES:
        dest = out / sp["file"]
        if dest.exists() and plan.get("reuse_existing"):
            print(f"✓ 跳过已存在: {sp['file']}")
            results.append(sp)
            continue

        parts = [{"text": sprite_prompt(plan, sp["role"])}]
        if sp["needs_ref"]:
            parts.append(idol_part)

        print(f"▶ 生成 {sp['file']} ({sp['role']})…")
        try:
            resp = call_gemini(api_key, parts)
            raw = extract_image_bytes(resp)
            (out / "raw" / (sp["file"])).write_bytes(raw)
            png = chroma_key(raw)
            dest.write_bytes(png)
            print(f"  ✓ {dest}")
            results.append(sp)
        except Exception as e:
            print(f"  ✗ {sp['file']} 失败: {e}", file=sys.stderr)
            # 单张失败不中断整体

    # 3. manifest
    manifest = {
        "character": plan.get("character", ""),
        "frames": {sp["frame"]: f"./assets/pet/{sp['file']}" for sp in results},
        "files": [sp["file"] for sp in results],
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✅ 完成 {len(results)}/{len(SPRITES)} 张 → {out}")
    print(f"   manifest: {out / 'manifest.json'}")


def main():
    ap = argparse.ArgumentParser(description="为 canvas-pet 生成一整套桌宠精灵图")
    ap.add_argument("--skill-plan", required=True, help="JSON 计划文件路径")
    ap.add_argument("--out", required=True, help="输出目录（精灵图落到这里）")
    args = ap.parse_args()
    run(args.skill_plan, args.out)


if __name__ == "__main__":
    main()
