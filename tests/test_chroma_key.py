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
    def _keyed(self, arr: np.ndarray, key_rgb=gs.DEFAULT_KEY_RGB) -> np.ndarray:
        return np.asarray(Image.open(io.BytesIO(gs.chroma_key(_png(arr), key_rgb))))

    def test_pure_background_becomes_fully_transparent(self):
        arr = np.full((8, 8, 3), gs.DEFAULT_KEY_RGB, dtype=np.uint8)
        result = self._keyed(arr)
        self.assertTrue((result[:, :, 3] == 0).all(), "纯背景应全透明")

    def test_far_from_background_becomes_fully_opaque(self):
        arr = np.full((8, 8, 3), (220, 30, 30), dtype=np.uint8)
        result = self._keyed(arr)
        self.assertTrue((result[:, :, 3] == 255).all(), "远离背景色应全不透明")

    def test_transition_pixels_get_partial_alpha(self):
        """抗锯齿过渡像素应得到介于 0 与 255 之间的 alpha，而不是二值化。"""
        arr = np.full((8, 8, 3), gs.DEFAULT_KEY_RGB, dtype=np.uint8)
        mid = tuple((gs.DEFAULT_KEY_RGB[i] + 220) // 2 for i in range(3))
        arr[3, 3] = mid
        result = self._keyed(arr)
        alpha = int(result[3, 3, 3])
        self.assertNotEqual(alpha, 0, "过渡像素不该被一刀切成全透明")
        self.assertNotEqual(alpha, 255, "过渡像素不该被一刀切成全不透明")

    def test_despill_suppresses_dominant_channel(self):
        """去溢色：不透明像素的主导通道不该明显超过其他通道（避免背景色调残留）。"""
        # 偏绿的角色像素（G 远大于 R 和 B），离绿色背景远，应不透明且被去溢色
        arr = np.full((8, 8, 3), (60, 200, 70), dtype=np.uint8)
        result = self._keyed(arr)
        r, g, b = int(result[0, 0, 0]), int(result[0, 0, 1]), int(result[0, 0, 2])
        self.assertLessEqual(g, max(r, b) + 10, f"去溢色后 G({g}) 应 <= max(R,B)+10")

    def test_custom_key_color_red(self):
        """自定义红色 keyColor：红色背景变透明，绿色角色保留。"""
        red_key = (255, 0, 0)
        arr = np.full((8, 8, 3), red_key, dtype=np.uint8)
        arr[2:6, 2:6] = (30, 200, 30)  # 绿色角色
        result = self._keyed(arr, key_rgb=red_key)
        # 红色背景全透明
        self.assertEqual(int(result[0, 0, 3]), 0)
        # 绿色角色不透明
        self.assertEqual(int(result[3, 3, 3]), 255)


class ColorCollisionTests(unittest.TestCase):
    def test_no_collision_when_character_far_from_key(self):
        """角色（红色）远离绿色背景 → 不撞色。"""
        arr = np.full((20, 20, 3), gs.DEFAULT_KEY_RGB, dtype=np.uint8)
        arr[5:15, 5:15] = (220, 30, 30)
        diag = gs.detect_color_collision(_png(arr), gs.DEFAULT_KEY_RGB)
        self.assertFalse(diag["collision"])
        self.assertLess(diag["ratio"], 0.1)

    def test_collision_when_character_close_to_key(self):
        """角色（偏绿，接近背景色）→ 撞色。"""
        arr = np.full((20, 20, 3), gs.DEFAULT_KEY_RGB, dtype=np.uint8)
        # 角色用与背景同色相的绿，棋盘距离 60，落在渐变带（30-120）中间
        arr[5:15, 5:15] = (60, 140, 60)
        diag = gs.detect_color_collision(_png(arr), gs.DEFAULT_KEY_RGB)
        self.assertTrue(diag["collision"], f"应判撞色，ratio={diag['ratio']:.2f}")
        self.assertIsNotNone(diag["sample_pixel"])

    def test_collision_avoided_by_switching_key_color(self):
        """撞色场景换 keyColor（品红）后不再撞色。"""
        arr = np.full((20, 20, 3), gs.DEFAULT_KEY_RGB, dtype=np.uint8)
        arr[5:15, 5:15] = (60, 140, 60)  # 偏绿角色
        # 同一张图，绿 key 判撞色，品红 key 不撞色（因为品红离绿色角色远）
        magenta = (255, 0, 255)
        diag_green = gs.detect_color_collision(_png(arr), gs.DEFAULT_KEY_RGB)
        diag_magenta = gs.detect_color_collision(_png(arr), magenta)
        self.assertTrue(diag_green["collision"])
        self.assertFalse(diag_magenta["collision"])


class ResolveKeyColorTests(unittest.TestCase):
    def test_default_when_not_specified(self):
        rgb, hex_ = gs.resolve_key_color({})
        self.assertEqual(rgb, gs.DEFAULT_KEY_RGB)
        self.assertEqual(hex_, gs.DEFAULT_KEY_HEX)

    def test_accepts_hex_with_hash(self):
        rgb, hex_ = gs.resolve_key_color({"keyColor": "#FF00FF"})
        self.assertEqual(rgb, (255, 0, 255))

    def test_accepts_hex_without_hash(self):
        rgb, _ = gs.resolve_key_color({"keyColor": "00FFFF"})
        self.assertEqual(rgb, (0, 255, 255))

    def test_rejects_invalid_hex(self):
        with self.assertRaises(SystemExit):
            gs.resolve_key_color({"keyColor": "not-a-color"})


if __name__ == "__main__":
    unittest.main()
