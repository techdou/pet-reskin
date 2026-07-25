"""Provider 抽象层：统一 Gemini 和 image2-api 两种图像生成 API。

统一接口：
    generate(prompt: str) -> bytes            # 纯文本生成
    edit(prompt: str, reference: bytes) -> bytes  # 带参考图的编辑/生成

provider 选择由 plan.provider 决定（"gemini" 默认 | "image2api"）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol


class ImageProvider(Protocol):
    """所有 provider 实现的统一接口。"""

    name: str

    def generate(self, prompt: str, size: Optional[str] = None, quality: Optional[str] = None) -> bytes:
        """纯文本生成，返回图片字节。"""
        ...

    def edit(self, prompt: str, reference: bytes, size: Optional[str] = None, quality: Optional[str] = None) -> bytes:
        """带参考图的编辑/生成（用于锁定角色一致性），返回图片字节。

        reference 是参考图的原始字节（PNG/JPEG/WebP 均可）。
        """
        ...


def get_provider(plan: dict, api_key: Optional[str] = None) -> ImageProvider:
    """根据 plan.provider 选择并返回 provider 实例。

    plan.provider: "gemini" (默认) | "image2api"
    """
    name = (plan.get("provider") or "gemini").lower()
    if name == "image2api":
        from .image2api import Image2APIProvider
        return Image2APIProvider(plan=plan)
    if name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(plan=plan, api_key=api_key)
    raise ValueError(
        f"unknown provider: {name!r}. Supported: 'gemini', 'image2api'. "
        f"Set plan.provider or omit it (defaults to 'gemini')."
    )
