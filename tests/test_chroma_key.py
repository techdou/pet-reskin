from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_sprites as gs  # noqa: E402


def _png(arr: np.ndarray) -> bytes:
    Image.fromarray(arr.astype(np.uint8), "RGB").save((buf := io.BytesIO()), format="PNG")
    return buf.getvalue()


class ChromaKeyTests(unittest.TestCase):
    def _keyed(self, arr: np.ndarray) -> np.ndarray:
        return np.asarray(Image.open(io.BytesIO(gs.chroma_key(_png(arr)))))

    def test_pure_background_becomes_fully_transparent(self):
        arr = np.full((8, 8, 3), gs.KEY_COLOR, dtype=np.uint8)
        result = self._keyed(arr)
        self.assertTrue((result[:, :, 3] == 0).all(), "纯背景应全透明")

    def test_far_from_background_becomes_fully_opaque(self):
        # 纯红，离绿色很远
        arr = np.full((8, 8, 3), (220, 30, 30), dtype=np.uint8)
        result = self._keyed(arr)
        self.assertTrue((result[:, :, 3] == 255).all(), "远离背景色应全不透明")

    def test_transition_pixels_get_partial_alpha(self):
        """抗锯齿过渡像素应得到介于 0 与 255 之间的 alpha，而不是二值化。"""
        arr = np.full((8, 8, 3), gs.KEY_COLOR, dtype=np.uint8)
        # 一个介于背景绿和角色红之间的过渡色
        transition = tuple((gs.KEY_COLOR[i] + 220 // 2 + 30 // 2) // 2 for i in range(3))
        # 构造一个明显在渐变区间的像素：背景与红色的中点
        mid = tuple((gs.KEY_COLOR[i] + 220) // 2 for i in range(3))
        arr[3, 3] = mid
        result = self._keyed(arr)
        alpha = result[3, 3, 3]
        self.assertNotEqual(alpha, 0, "过渡像素不该被一刀切成全透明")
        self.assertNotEqual(alpha, 255, "过渡像素不该被一刀切成全不透明")

    def test_despill_suppresses_green_in_opaque_pixels(self):
        """去溢色：不透明像素的 G 通道不该明显超过 R/B（避免绿调残留）。"""
        # 一个偏绿的角色像素（G 远大于 R 和 B），远离背景仍不透明
        arr = np.full((8, 8, 3), (60, 200, 70), dtype=np.uint8)
        result = self._keyed(arr)
        r, g, b = int(result[0, 0, 0]), int(result[0, 0, 1]), int(result[0, 0, 2])
        # despill 会把 G 压到 max(R,B)+5 附近
        self.assertLessEqual(g, max(r, b) + 10, f"去溢色后 G({g}) 应 <= max(R,B)+10")


if __name__ == "__main__":
    unittest.main()
