from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import validate_output  # noqa: E402


FILES = [
    "idle.png", "idle-wink.png", "walk-front-1.png", "walk-front-2.png",
    "walk-left-1.png", "walk-right-1.png", "walk-back-1.png", "sleep.png"
]
FRAMES = [
    "idle", "idleWink", "walkFront1", "walkFront2", "walkLeft", "walkRight", "walkBack", "sleep"
]


def manifest(include_cloud: bool = False):
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
    files = list(FILES)
    requested = list(frames.keys())
    if include_cloud:
        frames["cloud"] = "./assets/pet/cloud.png"
        files.append("cloud.png")
        requested.append("cloud")
    return {
        "frames": frames,
        "files": files,
        "requiredFrames": FRAMES,
        "optionalFrames": ["cloud"],
        "requestedFrames": requested,
    }


class ValidateOutputTests(unittest.TestCase):
    def test_validate_complete_output_and_target_without_cloud(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sprites = root / "sprites"
            target = root / "target"
            sprites.mkdir()
            (target / "assets" / "pet").mkdir(parents=True)
            for fname in FILES:
                Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(sprites / fname)
            manifest_path = sprites / "manifest.json"
            manifest_path.write_text(json.dumps(manifest(include_cloud=False)), encoding="utf-8")
            shutil.copy2(Path(__file__).parent / "fixtures" / "sample-pet.config.js", target / "pet.config.js")

            report = validate_output.validate(manifest_path, sprites, target, allow_partial=False)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["errors"], [])

    def test_validate_rejects_missing_required_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sprites = root / "sprites"
            sprites.mkdir()
            data = manifest(include_cloud=False)
            data["frames"].pop("sleep")
            data["files"] = data["files"][:-1]
            data["requestedFrames"] = [f for f in data["requestedFrames"] if f != "sleep"]
            manifest_path = sprites / "manifest.json"
            manifest_path.write_text(json.dumps(data), encoding="utf-8")
            for fname in data["files"]:
                Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(sprites / fname)

            report = validate_output.validate(manifest_path, sprites, target=None, allow_partial=False)
            self.assertFalse(report["ok"])
            self.assertTrue(any("sleep" in error for error in report["errors"]))

    def test_validate_allows_missing_cloud_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sprites = root / "sprites"
            sprites.mkdir()
            data = manifest(include_cloud=False)
            manifest_path = sprites / "manifest.json"
            manifest_path.write_text(json.dumps(data), encoding="utf-8")
            for fname in data["files"]:
                Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(sprites / fname)

            report = validate_output.validate(manifest_path, sprites, target=None, allow_partial=False)
            self.assertTrue(report["ok"], report)

    def test_parse_frame_keys_ignores_keys_outside_frames_block(self):
        """帧键解析只认 frames 块内部，不抓注释/字符串里的同名伪键。"""
        config_text = (
            "export default {\n"
            "  baseSize: 72,\n"
            "  frames: {\n"
            "    idle: './a.png',\n"
            "    sleep: './b.png',\n"
            "  },\n"
            "  // 注释里出现的 idle: 不该被算进去\n"
            "  quotes: ['idle: fake', 'walkRight: also fake'],\n"
            "}\n"
        )
        keys = validate_output.parse_frame_keys_from_config(config_text)
        self.assertEqual(keys, ["idle", "sleep"])
        # 不该混入 walkRight（只出现在 quotes 字符串里）
        self.assertNotIn("walkRight", keys)

    def test_validate_reports_failures_field_in_manifest(self):
        """manifest 带 failures 字段时，validate 应原样返回（不报错，供调用方决策）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sprites = root / "sprites"
            sprites.mkdir()
            data = manifest(include_cloud=False)
            data["failures"] = [{"frame": "cloud", "file": "cloud.png", "error": "rate limited"}]
            manifest_path = sprites / "manifest.json"
            manifest_path.write_text(json.dumps(data), encoding="utf-8")
            for fname in data["files"]:
                Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(sprites / fname)

            report = validate_output.validate(manifest_path, sprites, target=None, allow_partial=False)
            # cloud 是可选帧，失败不影响 ok
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
