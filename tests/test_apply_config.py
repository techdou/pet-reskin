from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import apply_config  # noqa: E402


REQUIRED_FILES = [
    "idle.png", "idle-wink.png", "walk-front-1.png", "walk-front-2.png",
    "walk-left-1.png", "walk-right-1.png", "walk-back-1.png", "sleep.png"
]
REQUIRED_FRAMES = [
    "idle", "idleWink", "walkFront1", "walkFront2", "walkLeft", "walkRight", "walkBack", "sleep"
]


def sample_manifest(include_cloud: bool = False):
    frames = {
        "idle": "./assets/pet/idle.png",
        "idleWink": "./assets/pet/idle-wink.png",
        "walkFront1": "./assets/pet/walk-front-1.png",
        "walkFront2": "./assets/pet/walk-front-2.png",
        "walkLeft": "./assets/pet/walk-left-1.png",
        "walkRight": "./assets/pet/walk-right-1.png",
        "walkBack": "./assets/pet/walk-back-1.png",
        "sleep": "./assets/pet/sleep.png",
    }
    files = list(REQUIRED_FILES)
    if include_cloud:
        frames["cloud"] = "./assets/pet/cloud.png"
        files.append("cloud.png")
    return {
        "frames": frames,
        "files": files,
        "quotes": ["新金句一", "新金句二"],
        "baseSize": 88,
        "requiredFrames": REQUIRED_FRAMES,
        "optionalFrames": ["cloud"],
        "requestedFrames": list(frames.keys()),
    }


class ApplyConfigTests(unittest.TestCase):
    def test_update_config_text_replaces_required_frames_quotes_and_base_size(self):
        fixture = Path(__file__).parent / "fixtures" / "sample-pet.config.js"
        text = fixture.read_text(encoding="utf-8")
        updated, warnings = apply_config.update_config_text(text, sample_manifest(include_cloud=False), {})
        self.assertEqual(warnings, [])
        for frame in REQUIRED_FRAMES:
            self.assertIn(f"{frame}:", updated)
        self.assertIn("baseSize: 88", updated)
        self.assertIn('quotes: ["新金句一", "新金句二"]', updated)
        self.assertNotIn("old-idle", updated)
        # cloud is preserved when not provided in manifest
        self.assertIn("cloud: \"./assets/pet/old-cloud.png\"", updated)

    def test_partial_manifest_is_rejected_by_default_when_required_frame_missing(self):
        manifest = sample_manifest(include_cloud=False)
        manifest["frames"].pop("sleep")
        errors = apply_config.validate_manifest(manifest, allow_partial=False)
        self.assertTrue(any("sleep" in error for error in errors))

    def test_missing_cloud_is_allowed_by_default(self):
        manifest = sample_manifest(include_cloud=False)
        errors = apply_config.validate_manifest(manifest, allow_partial=False)
        self.assertEqual(errors, [])

    def test_run_creates_backup_and_copies_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "canvas-pet"
            sprites = root / "sprites"
            (target / "assets" / "pet").mkdir(parents=True)
            sprites.mkdir()
            shutil.copy2(Path(__file__).parent / "fixtures" / "sample-pet.config.js", target / "pet.config.js")
            for fname in REQUIRED_FILES:
                Image.new("RGBA", (4, 4), (255, 0, 0, 128)).save(sprites / fname)
            manifest_path = sprites / "manifest.json"
            manifest_path.write_text(json.dumps(sample_manifest(include_cloud=False), ensure_ascii=False), encoding="utf-8")
            (sprites / "plan.json").write_text(json.dumps({"quotes": ["fallback"], "baseSize": 90}), encoding="utf-8")

            code = apply_config.run(manifest_path, sprites, target, allow_partial=False, dry_run=False, no_backup=False)
            self.assertEqual(code, 0)
            self.assertTrue((target / "pet.config.js.bak").exists())
            self.assertTrue((target / "assets" / "pet" / "idle.png").exists())
            config_text = (target / "pet.config.js").read_text(encoding="utf-8")
            self.assertIn("baseSize: 88", config_text)
            self.assertIn("cloud: \"./assets/pet/old-cloud.png\"", config_text)

    def test_balance_scanner_handles_braces_and_brackets_in_string_values(self):
        """frames 路径含 }、quotes 金句含 ] 时，平衡扫描不该误截断。"""
        config_text = (
            "export default {\n"
            "  baseSize: 72,\n"
            "  frames: {\n"
            "    idle: \"./a}.png\",\n"
            "    cloud: \"./c.png\",\n"
            "  },\n"
            "  quotes: ['金句含 ] 方括号', '第二条'],\n"
            "}\n"
        )
        manifest = sample_manifest(include_cloud=False)
        updated, warnings = apply_config.update_config_text(config_text, manifest, {})
        self.assertEqual(warnings, [])
        # frames 替换后仍含 } 字符的路径（说明没被误截断）
        self.assertIn("./assets/pet/idle.png", updated)
        # quotes 替换后应是 manifest 的新金句，旧金句消失
        self.assertIn("新金句一", updated)
        self.assertNotIn("金句含 ] 方括号", updated)

    def test_parse_existing_frames_ignores_non_frames_keys(self):
        """parse_existing_frames 只读 frames 块，不抓 baseSize/quotes 等其他键。"""
        config_text = (
            "export default {\n"
            "  baseSize: 72,\n"
            "  frames: {\n"
            "    idle: './a.png',\n"
            "    sleep: './b.png',\n"
            "  },\n"
            "  quotes: ['x'],\n"
            "}\n"
        )
        frames = apply_config.parse_existing_frames(config_text)
        self.assertIn("idle", frames)
        self.assertIn("sleep", frames)
        self.assertNotIn("baseSize", frames)
        self.assertNotIn("quotes", frames)


if __name__ == "__main__":
    unittest.main()
