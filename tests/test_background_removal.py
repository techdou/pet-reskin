"""测试 background_removal.py：chroma_key（向后兼容）+ white_to_alpha（新增）。"""
import io
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from background_removal import chroma_key, white_to_alpha, remove_background, detect_color_collision


def _make_image(rgb_color, size=(10, 10)):
    """生成纯色 RGB 图，返回字节。"""
    arr = np.full((*size, 3), rgb_color, dtype=np.uint8)
    Image.fromarray(arr, "RGB").save((buf := io.BytesIO()), format="PNG")
    return buf.getvalue()


class WhiteToAlphaTests(unittest.TestCase):
    def test_pure_white_becomes_transparent(self):
        """纯白像素应完全透明。"""
        src = _make_image((255, 255, 255))
        result = white_to_alpha(src)
        img = Image.open(io.BytesIO(result)).convert("RGBA")
        arr = np.array(img)
        # 所有像素 alpha 应为 0
        self.assertTrue((arr[..., 3] == 0).all())

    def test_pure_black_becomes_opaque(self):
        """纯黑像素应完全不透明。"""
        src = _make_image((0, 0, 0))
        result = white_to_alpha(src)
        img = Image.open(io.BytesIO(result)).convert("RGBA")
        arr = np.array(img)
        self.assertTrue((arr[..., 3] == 255).all())

    def test_colored_pixel_becomes_opaque(self):
        """非白色彩色像素应保持不透明。"""
        src = _make_image((200, 100, 50))  # 橙色，远离白
        result = white_to_alpha(src)
        img = Image.open(io.BytesIO(result)).convert("RGBA")
        arr = np.array(img)
        self.assertTrue((arr[..., 3] == 255).all())
        # RGB 不应变
        self.assertTrue((arr[..., 0] == 200).all())


class RemoveBackgroundDispatchTests(unittest.TestCase):
    def test_white_strategy(self):
        src = _make_image((255, 255, 255))
        result = remove_background(src, strategy="white")
        img = Image.open(io.BytesIO(result)).convert("RGBA")
        self.assertTrue((np.array(img)[..., 3] == 0).all())

    def test_chroma_strategy_default_color(self):
        """chroma 策略默认绿底：纯绿应透明。"""
        src = _make_image((120, 200, 120))  # #78C878 默认 keyColor
        result = remove_background(src, strategy="chroma")
        img = Image.open(io.BytesIO(result)).convert("RGBA")
        arr = np.array(img)
        # 纯背景色 alpha 应为 0
        self.assertTrue((arr[..., 3] == 0).all())

    def test_unknown_strategy_raises(self):
        with self.assertRaises(ValueError):
            remove_background(_make_image((0, 0, 0)), strategy="unknown")


class ChromaKeyBackwardCompatTests(unittest.TestCase):
    """验证从 generate_sprites.py 平移的 chroma_key 行为不变。"""

    def test_pure_background_becomes_fully_transparent(self):
        src = _make_image((120, 200, 120))
        result = chroma_key(src)
        img = Image.open(io.BytesIO(result)).convert("RGBA")
        self.assertTrue((np.array(img)[..., 3] == 0).all())

    def test_far_from_background_becomes_fully_opaque(self):
        src = _make_image((0, 0, 0))
        result = chroma_key(src)
        img = Image.open(io.BytesIO(result)).convert("RGBA")
        self.assertTrue((np.array(img)[..., 3] == 255).all())


if __name__ == "__main__":
    unittest.main()
