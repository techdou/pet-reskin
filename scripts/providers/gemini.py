"""Gemini provider：封装 Google Gemini 图像生成 API。

从原 generate_sprites.py 抽出，行为完全一致，只是改成 Provider 接口。
背景默认走 chroma-key（绿底），由调用方在 prompt 里指定 keyColor。
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

DEFAULT_MODEL_ID = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image")
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_IMAGE_SIZE = os.environ.get("GEMINI_IMAGE_SIZE", "1K")


def _get_api_key(explicit: Optional[str] = None) -> str:
    key = explicit or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a key from https://aistudio.google.com/ "
            "and set GEMINI_API_KEY before running generation."
        )
    return key


def _build_url(model_id: str, api_key: str) -> str:
    return f"{API_BASE}/{model_id}:streamGenerateContent?key={api_key}"


def _call_gemini(
    api_key: str,
    model_id: str,
    parts: List[Dict[str, Any]],
    image_size: str = DEFAULT_IMAGE_SIZE,
    retries: int = 2,
) -> Any:
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "imageConfig": {"image_size": image_size},
        },
    }
    data = json.dumps(body).encode("utf-8")
    last_error: Optional[BaseException] = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            _build_url(model_id, api_key),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            try:
                detail = json.loads(exc.read().decode("utf-8"))["error"]["message"]
            except Exception:
                detail = str(exc)
            if exc.code == 429 and attempt < retries:
                wait = 10 * (attempt + 1)
                print(f"   ⚠ Rate limited, retrying in {wait}s… ({detail})", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc
    raise RuntimeError(f"Gemini retry exhausted: {last_error}")


def _extract_image_bytes(response: Any) -> bytes:
    chunks = response if isinstance(response, list) else [response]
    for chunk in chunks:
        for candidate in chunk.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
    raise ValueError(
        "Gemini response did not include image data; it may have been blocked or returned text only"
    )


class GeminiProvider:
    """Gemini 图像生成 provider。

    Gemini 的 generate 和 edit 走同一个 streamGenerateContent 端点，
    区别只是 parts 里是否带 inline_data（参考图）。
    """

    name = "gemini"

    def __init__(self, plan: dict, api_key: Optional[str] = None):
        self.plan = plan
        self.api_key = _get_api_key(api_key)
        self.model_id = os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL_ID)
        self.image_size = os.environ.get("GEMINI_IMAGE_SIZE", DEFAULT_IMAGE_SIZE)

    def generate(self, prompt: str, size: Optional[str] = None, quality: Optional[str] = None) -> bytes:
        """纯文本生成。quality 参数 Gemini 不用，仅为接口一致保留。"""
        parts = [{"text": prompt}]
        resp = _call_gemini(self.api_key, self.model_id, parts, image_size=size or self.image_size)
        return _extract_image_bytes(resp)

    def edit(self, prompt: str, reference: bytes, size: Optional[str] = None, quality: Optional[str] = None) -> bytes:
        """带参考图的生成。reference 是参考图字节，作为 inline_data 传入。"""
        parts = [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(reference).decode("ascii")}},
        ]
        resp = _call_gemini(self.api_key, self.model_id, parts, image_size=size or self.image_size)
        return _extract_image_bytes(resp)
