"""LangChain wrapper for calling Gemini consistently across AI features."""

from __future__ import annotations

import base64
import os
from functools import lru_cache
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import GEMINI_API_KEY


DEFAULT_TEXT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
DEFAULT_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash")
DEFAULT_INSIGHT_MODEL = os.getenv("GEMINI_INSIGHT_MODEL", "gemini-2.5-flash")


def _require_api_key() -> str:
    """Helper for require api key in the parser and NLP layer."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY belum tersedia.")
    return GEMINI_API_KEY


@lru_cache(maxsize=32)
def get_gemini_llm(model_name: str, temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """Retrieve data needed for gemini llm."""
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=_require_api_key(),
        temperature=temperature,
    )


def _extract_text(response: Any) -> str:
    """Extract the important part of the input for text."""
    content = getattr(response, "content", "")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()

    return str(content or "").strip()


def generate_text_with_gemini(
    prompt: str,
    *,
    model_name: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Helper for generate text with gemini in the parser and NLP layer."""
    llm = get_gemini_llm(model_name or DEFAULT_TEXT_MODEL, float(temperature))
    response = llm.invoke([HumanMessage(content=prompt)])
    return _extract_text(response)


def _make_data_url(image_bytes: bytes, mime_type: str) -> str:
    """Helper for make data url in the parser and NLP layer."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type or 'image/jpeg'};base64,{encoded}"


def generate_text_from_image_with_gemini(
    prompt: str,
    image_bytes: bytes,
    *,
    mime_type: str = "image/jpeg",
    model_name: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Helper for generate text from image with gemini in the parser and NLP layer."""
    if not image_bytes:
        raise ValueError("File gambar kosong atau gagal dibaca.")

    llm = get_gemini_llm(model_name or DEFAULT_IMAGE_MODEL, float(temperature))
    data_url = _make_data_url(image_bytes, mime_type)

    # Format standar LangChain multimodal.
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": data_url},
    ]

    try:
        response = llm.invoke([HumanMessage(content=content)])
        return _extract_text(response)
    except Exception as first_error:
        # Parser rule note for an Indonesian finance input edge case.
        alt_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        try:
            response = llm.invoke([HumanMessage(content=alt_content)])
            return _extract_text(response)
        except Exception:
            raise first_error
