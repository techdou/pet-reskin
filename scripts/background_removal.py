"""背景抠图层：支持 chroma-key（绿底）和 white（白底）两种策略。

chroma 策略：从 generate_sprites.py 抽出的现有逻辑，行为不变。适用于 Gemini
  默认的绿色 chroma-key 背景。
white 策略：白底 → 透明，带边缘抗锯齿。适用于 gpt-image-2 等不支持透明输出的
  模型（生成时走白底，后处理抠图）。

由 plan.background 字段选择（"chroma" 默认 | "white"）。
"""

from __future__ import annotations

import io
from typing import Dict, Tuple

import numpy as np
from PIL import Image

# ===== chroma-key 参数（从原 generate_sprites.py 平移，行为不变）=====
DEFAULT_KEY_RGB = (120, 200, 120)   # #78C878
DEFAULT_KEY_HEX = "#78C878"
KEY_INNER = 30
KEY_OUTER = 120
COLLISION_RATIO_THRESHOLD = 0.15

KeyRGB = Tuple[int, int, int]


def chroma_key(src_bytes: bytes, key_rgb: KeyRGB = DEFAULT_KEY_RGB) -> bytes:
    """纯色背景转透明，抗锯齿边缘 alpha 平滑渐变，并去溢色。

    行为与原 generate_sprites.py 的 chroma_key 完全一致（平移而来）。
    """
    image = Image.open(io.BytesIO(src_bytes)).convert("RGB")
    arr = np.asarray(image, dtype=np.float32)
    key = np.array(key_rgb, dtype=np.float32)
    dist = np.max(np.abs(arr - key), axis=2)
    alpha = np.clip((dist - KEY_INNER) / (KEY_OUTER - KEY_INNER), 0.0, 1.0) * 255.0
    alpha = alpha.astype(np.uint8)

    # 去溢色：压制与 key_rgb 主导通道同色的溢出
    kr, kg, kb = key_rgb
    if kg >= kr and kg >= kb:
        channel = 1
    elif kr >= kg and kr >= kb:
        channel = 0
    else:
        channel = 2
    others = [i for i in range(3) if i != channel]
    excess = arr[:, :, channel] - np.maximum(arr[:, :, others[0]], arr[:, :, others[1]]) - 5.0
    mask = excess > 0
    arr[:, :, channel] = np.where(mask, arr[:, :, channel] - excess, arr[:, :, channel])
    arr = np.clip(arr, 0, 255).astype(np.uint8)

    rgba = np.dstack([arr, alpha])
    Image.fromarray(rgba, "RGBA").save((buf := io.BytesIO()), format="PNG")
    return buf.getvalue()


def detect_color_collision(idol_bytes: bytes, key_rgb: KeyRGB = DEFAULT_KEY_RGB) -> Dict:
    """诊断角色主体是否与 keyColor 撞色（不可抠）。

    行为与原 generate_sprites.py 的 detect_color_collision 完全一致（平移而来）。
    """
    image = Image.open(io.BytesIO(idol_bytes)).convert("RGB")
    arr = np.asarray(image, dtype=np.float32)
    key = np.array(key_rgb, dtype=np.float32)
    dist = np.max(np.abs(arr - key), axis=2)
    non_bg_mask = dist > KEY_INNER
    non_bg_count = int(non_bg_mask.sum())
    if non_bg_count == 0:
        return {"collision": False, "ratio": 0.0, "sample_pixel": None}
    danger_mask = (dist > KEY_INNER) & (dist <= KEY_OUTER)
    danger_count = int(danger_mask.sum())
    ratio = danger_count / non_bg_count
    collision = ratio > COLLISION_RATIO_THRESHOLD
    sample = None
    if collision:
        danger_pixels = arr[danger_mask]
        sample_idx = np.argsort(dist[danger_mask])[len(danger_pixels) // 2]
        sample = tuple(int(v) for v in danger_pixels[sample_idx])
    return {"collision": collision, "ratio": float(ratio), "sample_pixel": sample}


# ===== white 策略（新增）=====

# 白底阈值：>250 全透明，240-250 渐变，<240 不透明
WHITE_FULL_TRANSPARENT = 250
WHITE_OPAQUE_THRESHOLD = 240


def white_to_alpha(src_bytes: bytes) -> bytes:
    """白底 → 透明，带边缘抗锯齿。

    适用于 gpt-image-2 等不支持透明输出的模型。生成时走纯白背景，
    这里把接近白的像素转透明，240-250 之间线性渐变处理抗锯齿边缘。

    实战验证（小豆 pet 17 帧全部白残留 = 0）：效果干净，无需撞色诊断。
    """
    image = Image.open(io.BytesIO(src_bytes)).convert("RGBA")
    arr = np.array(image).astype(np.int16)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]

    # 白度 = min(r, g, b)，越高越接近白
    whiteness = np.minimum(np.minimum(r, g), b)
    # >250 全透明；240-250 线性渐变；<240 不透明
    new_alpha = np.where(
        whiteness >= WHITE_FULL_TRANSPARENT,
        0,
        np.where(
            whiteness >= WHITE_OPAQUE_THRESHOLD,
            ((WHITE_FULL_TRANSPARENT - whiteness) / (WHITE_FULL_TRANSPARENT - WHITE_OPAQUE_THRESHOLD) * 255).astype(np.uint8),
            255
        )
    ).astype(np.uint8)

    # 把原本就透明的像素保持透明（不动输入 alpha）
    new_alpha = np.minimum(new_alpha, a.astype(np.uint8))

    arr_out = arr.copy()
    arr_out[..., 3] = new_alpha
    Image.fromarray(arr_out.astype(np.uint8), "RGBA").save((buf := io.BytesIO()), format="PNG")
    return buf.getvalue()


def remove_background(src_bytes: bytes, strategy: str = "chroma", key_rgb: KeyRGB = DEFAULT_KEY_RGB) -> bytes:
    """统一入口：按策略选择抠图方法。

    strategy: "chroma" (默认) | "white"
    key_rgb: chroma 策略的背景色（白底策略忽略此参数）
    """
    if strategy == "white":
        return white_to_alpha(src_bytes)
    if strategy == "chroma":
        return chroma_key(src_bytes, key_rgb)
    raise ValueError(f"unknown background strategy: {strategy!r}. Supported: 'chroma', 'white'.")
