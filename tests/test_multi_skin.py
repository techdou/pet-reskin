"""测试 multi_skin installer：pet.js skins 数组追加、skin id 解析、frames 映射。"""
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from installers.multi_skin import (
    _resolve_skin_id,
    _camel_key,
    build_skin_object,
    install_multi_skin,
)
from installers import detect_target_type


class CamelKeyTests(unittest.TestCase):
    def test_kebab_to_camel(self):
        self.assertEqual(_camel_key("idle-think"), "idleThink")
        self.assertEqual(_camel_key("walk-left-1"), "walkLeft1")
        self.assertEqual(_camel_key("idle"), "idle")
        self.assertEqual(_camel_key("sleep-2"), "sleep2")


class ResolveSkinIdTests(unittest.TestCase):
    def test_explicit_skin_id(self):
        self.assertEqual(_resolve_skin_id({}, {"skinId": "xiaodou"}), "xiaodou")

    def test_from_character(self):
        self.assertEqual(_resolve_skin_id({"character": "小豆"}, {}), "小豆")

    def test_default_when_empty(self):
        self.assertEqual(_resolve_skin_id({}, {}), "newskin")


class BuildSkinObjectTests(unittest.TestCase):
    def test_minimal_skin_object(self):
        block = build_skin_object(
            skin_id="test",
            name="测试",
            frames={"idle": "./assets/test/idle.png?v=1"},
            quotes=["hello"],
        )
        self.assertIn("id: \"test\"", block)
        self.assertIn("name: \"测试\"", block)
        self.assertIn("idle:", block)
        self.assertIn("hello", block)


class DetectTargetTypeTests(unittest.TestCase):
    def test_canvas_pet_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "pet.config.js").write_text("export default {}", encoding="utf-8")
            self.assertEqual(detect_target_type(tmp), "canvas_pet")

    def test_multi_skin_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "pet.js").write_text(
                "const PET_CONFIG = { skins: [{id:'a'}] };",
                encoding="utf-8",
            )
            self.assertEqual(detect_target_type(tmp), "multi_skin")

    def test_unknown_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_target_type(Path(tmp)), "unknown")


class InstallMultiSkinTests(unittest.TestCase):
    """集成测试：在临时 pet.js 上追加新 skin。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.target = Path(self.tmp)
        self.sprites_dir = self.target / "sprites"
        self.sprites_dir.mkdir()
        # 复制 fixture pet.js
        fixture = Path(__file__).parent / "fixtures" / "sample-pet.js"
        (self.target / "pet.js").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
        # 假 sprite 文件
        for name in ["idle.png", "sleep.png"]:
            (self.sprites_dir / name).write_bytes(b"\x89PNG fake")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _make_manifest(self, **overrides):
        manifest = {
            "character": "小豆",
            "frames": {
                "idle": "./assets/pet/idle.png",
                "sleep": "./assets/pet/sleep.png",
            },
            "files": ["idle.png", "sleep.png"],
            "quotes": ["测试金句"],
            "requiredFrames": ["idle", "sleep"],
        }
        manifest.update(overrides)
        return manifest

    def test_dry_run_does_not_modify_pet_js(self):
        original = (self.target / "pet.js").read_text(encoding="utf-8")
        result = install_multi_skin(
            manifest=self._make_manifest(),
            sprites_dir=self.sprites_dir,
            target=self.target,
            plan={"skinId": "xiaodou"},
            dry_run=True,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["skinId"], "xiaodou")
        # dry-run 不应改动 pet.js
        self.assertEqual((self.target / "pet.js").read_text(encoding="utf-8"), original)

    def test_appends_new_skin_to_array(self):
        result = install_multi_skin(
            manifest=self._make_manifest(),
            sprites_dir=self.sprites_dir,
            target=self.target,
            plan={"skinId": "xiaodou", "skinName": "小豆"},
            dry_run=False,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["skinId"], "xiaodou")
        # pet.js 应包含新 skin id
        text = (self.target / "pet.js").read_text(encoding="utf-8")
        self.assertIn("xiaodou", text)
        self.assertIn("小豆", text)
        # 备份应存在
        self.assertTrue((self.target / "pet.js.bak").exists())
        # 图片应拷贝到 pet/assets/xiaodou/
        self.assertTrue((self.target / "pet" / "assets" / "xiaodou" / "idle.png").exists())

    def test_pet_js_remains_valid_structure(self):
        """追加后 pet.js 应仍是有效的 JS（skins 数组闭合、三个 skin 对象）。"""
        install_multi_skin(
            manifest=self._make_manifest(),
            sprites_dir=self.sprites_dir,
            target=self.target,
            plan={"skinId": "newskin"},
            dry_run=False,
        )
        text = (self.target / "pet.js").read_text(encoding="utf-8")
        # 简单验证：3 个 id 字段（原 2 个 + 新增 1 个）
        self.assertEqual(text.count("id:"), 3)
        # skins 数组闭合 ] 应在文件中（只一个）
        self.assertIn("]", text)


if __name__ == "__main__":
    unittest.main()
