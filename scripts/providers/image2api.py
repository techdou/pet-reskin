"""image2-api provider：封装 image2-api skill 的 image2lib 客户端。

image2-api 是独立的 Agent Skill（路径通常在 ~/.agents/skills/image2-api），
带 8 个 provider 的 fallback 链和 gpt-image-2 支持，实测比单 Gemini 稳定。

本 provider 自动探测 image2-api skill 位置并加入 sys.path，然后 import image2lib。
背景默认走白底（gpt-image-2 不支持透明输出，白底 + 后处理更稳）。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

# image2-api skill 的可能位置（按优先级）
_SKILL_CANDIDATES = [
    # 用户默认 skills 目录
    Path.home() / ".agents" / "skills" / "image2-api",
    # zcode skills 目录
    Path.home() / ".zcode" / "skills" / "image2-api",
    # 同级目录（如果两个 skill 放一起）
    Path(__file__).resolve().parents[3] / "image2-api",
    # 环境变量显式指定
    Path(os.environ["IMAGE2_API_ROOT"]) if os.environ.get("IMAGE2_API_ROOT") else None,
]


def _find_image2api_root() -> Optional[Path]:
    """探测 image2-api skill 的根目录。"""
    for candidate in _SKILL_CANDIDATES:
        if candidate is None:
            continue
        scripts_dir = candidate / "scripts"
        if (scripts_dir / "image2lib" / "__init__.py").exists():
            return scripts_dir
    return None


def _ensure_image2lib_importable() -> None:
    """把 image2-api/scripts 加入 sys.path，让 image2lib 可 import。"""
    # 已 import 过就不用重复加
    if "image2lib" in sys.modules:
        return
    root = _find_image2api_root()
    if root is None:
        raise RuntimeError(
            "image2-api skill 未找到。请确认它安装在以下任一位置：\n"
            "  - ~/.agents/skills/image2-api/\n"
            "  - ~/.zcode/skills/image2-api/\n"
            "或设置环境变量 IMAGE2_API_ROOT 指向其根目录。\n"
            "image2-api 提供 gpt-image-2 + 多 provider fallback，比单 Gemini 更稳定。"
        )
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


class Image2APIProvider:
    """image2-api skill 的 provider 封装。

    通过 image2lib.ImageAPIClient 调用，自动加载 image2-api skill 的 .env
    （8 个 provider 的凭证 + fallback 链配置）。
    """

    name = "image2api"

    def __init__(self, plan: dict):
        _ensure_image2lib_importable()
        # 延迟 import，避免 image2-api 不在时整模块加载失败
        from image2lib.config import APIConfig
        from image2lib.client import ImageAPIClient, extract_image_entries, entry_to_bytes

        self._extract_image_entries = extract_image_entries
        self._entry_to_bytes = entry_to_bytes
        self.plan = plan
        # APIConfig.from_env 会读 image2-api skill 的 .env
        self.config = APIConfig.from_env()
        self.client = ImageAPIClient(self.config)

    def _default_payload(self, prompt: str, size: Optional[str], quality: Optional[str]) -> dict:
        """构造 generate 请求 payload。"""
        return {
            "model": self.config.primary_profile.model,
            "prompt": prompt,
            "size": size or "1024x1024",
            "quality": quality or "high",
            "background": "opaque",  # gpt-image-2 不支持透明，走白底由后处理抠图
            "n": 1,
        }

    def generate(self, prompt: str, size: Optional[str] = None, quality: Optional[str] = None) -> bytes:
        """纯文本生成。"""
        payload = self._default_payload(prompt, size, quality)
        result = self.client.generate(payload)
        entries = self._extract_image_entries(result.payload)
        if not entries:
            raise RuntimeError("image2-api 返回了空结果，未包含图片数据")
        return self._entry_to_bytes(entries[0])

    def edit(self, prompt: str, reference: bytes, size: Optional[str] = None, quality: Optional[str] = None) -> bytes:
        """带参考图的编辑。reference 是参考图字节，写入临时文件后走 multipart edit 端点。"""
        # 判断 reference 的 mime type（按字节头）
        suffix = ".png"
        if reference[:3] == b"\xff\xd8\xff":
            suffix = ".jpg"
        elif reference[:4] == b"RIFF" and reference[8:12] == b"WEBP":
            suffix = ".webp"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(reference)
            tmp_path = Path(tmp.name)
        try:
            fields = {
                "model": self.config.primary_profile.model,
                "prompt": prompt,
                "size": size or "1024x1024",
                "quality": quality or "high",
                "background": "opaque",
                "n": "1",
            }
            result = self.client.edit(fields=fields, image_paths=[tmp_path])
            entries = self._extract_image_entries(result.payload)
            if not entries:
                raise RuntimeError("image2-api edit 返回了空结果，未包含图片数据")
            return self._entry_to_bytes(entries[0])
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
