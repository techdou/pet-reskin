"""测试 frames.py：帧模板解析、自定义帧、cloud 帧。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from frames import resolve_frames, get_cloud_frame, load_templates, _normalize_frame


class FrameTemplateTests(unittest.TestCase):
    def test_base8_default(self):
        """无 frameSet 字段时默认 base8（8 帧）。"""
        frames = resolve_frames({})
        self.assertEqual(len(frames), 8)
        frame_keys = [f["frame"] for f in frames]
        self.assertIn("idle", frame_keys)
        self.assertIn("sleep", frame_keys)
        self.assertIn("walkFront1", frame_keys)

    def test_explicit_base8(self):
        frames = resolve_frames({"frameSet": "base8"})
        self.assertEqual(len(frames), 8)

    def test_extended16(self):
        """extended16 模板含 16 帧，包括新增的 idleThink/wave/happy 等。"""
        frames = resolve_frames({"frameSet": "extended16"})
        self.assertEqual(len(frames), 16)
        frame_keys = [f["frame"] for f in frames]
        # 基础 8 帧都在
        for k in ["idle", "idleWink", "walkFront1", "sleep"]:
            self.assertIn(k, frame_keys)
        # 扩展 8 帧也在
        for k in ["idleThink", "idleLook", "walkLeft2", "walkRight2", "walkBack2", "sleep2", "wave", "happy"]:
            self.assertIn(k, frame_keys)

    def test_custom_frames_array(self):
        """plan.frames 自定义数组优先于 frameSet。"""
        custom = [
            {"frame": "idle", "file": "idle.png"},
            {"frame": "jump", "file": "jump.png", "pose": "mid-air jump"}
        ]
        frames = resolve_frames({"frameSet": "base8", "frames": custom})
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0]["frame"], "idle")
        self.assertEqual(frames[1]["frame"], "jump")
        # pose 缺省时为空字符串
        self.assertEqual(frames[0]["pose"], "")
        self.assertEqual(frames[1]["pose"], "mid-air jump")

    def test_unknown_frame_set_raises(self):
        with self.assertRaises(ValueError):
            resolve_frames({"frameSet": "nonexistent"})

    def test_cloud_frame(self):
        """cloud 帧有 frame/file/role/needsRef 字段。"""
        cloud = get_cloud_frame()
        self.assertEqual(cloud["frame"], "cloud")
        self.assertEqual(cloud["file"], "cloud.png")
        self.assertFalse(cloud["needsRef"])

    def test_normalize_frame_fills_defaults(self):
        """_normalize_frame 补全 role/needsRef/pose 缺省值。"""
        f = _normalize_frame({"frame": "test", "file": "test.png"})
        self.assertEqual(f["role"], "test")  # role 缺省 = frame 名
        self.assertTrue(f["needsRef"])  # 默认需要参考图
        self.assertEqual(f["pose"], "")  # pose 缺省空

    def test_templates_file_loads(self):
        """frame-templates.json 能正常加载。"""
        t = load_templates()
        self.assertIn("templates", t)
        self.assertIn("base8", t["templates"])
        self.assertIn("extended16", t["templates"])


if __name__ == "__main__":
    unittest.main()
