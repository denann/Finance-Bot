"""LangChain wrapper for calling Gemini consistently across text and image features."""


# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import base64 for this module's local operations.
import base64
# Import os for this module's local operations.
import os
# Import functools so this module can use its helpers.
from functools import lru_cache
# Import typing so this module can use its helpers.
from typing import Any

# Import langchain_core.messages so this module can use its helpers.
from langchain_core.messages import HumanMessage
# Import langchain_google_genai so this module can use its helpers.
from langchain_google_genai import ChatGoogleGenerativeAI

# Import app.config so this module can use its helpers.
from app.config import GEMINI_API_KEY


DEFAULT_TEXT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
DEFAULT_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash")
DEFAULT_INSIGHT_MODEL = os.getenv("GEMINI_INSIGHT_MODEL", "gemini-2.5-flash")


# Helper for require api key.
def _require_api_key() -> str:
    """Coordinate the require api key logic in the NLP/parser layer.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Validate missing GEMINI API KEY before continuing.
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY belum tersedia.")
    return GEMINI_API_KEY


# Apply this decorator before the callable is registered or executed.
@lru_cache(maxsize=32)
# Helper for get gemini llm.
def get_gemini_llm(model_name: str, temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """Retrieve data needed by the get gemini llm workflow in the NLP/parser layer.

    Args:
        model_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        temperature: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `ChatGoogleGenerativeAI` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=_require_api_key(),
        temperature=temperature,
    )


# Helper for extract text.
def _extract_text(response: Any) -> str:
    """Extract the required part of input for text."""
    content = getattr(response, "content", "")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        # Iterate through each item.
        for item in content:
            if isinstance(item, str):
                # Append the current value to parts.
                parts.append(item)
            # Fall back when isinstance(item, dict).
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    # Append the current value to parts.
                    parts.append(str(text))
        return "\n".join(parts).strip()

    return str(content or "").strip()


# Helper for generate text with gemini.
def generate_text_with_gemini(
    prompt: str,
    *,
    model_name: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Coordinate the generate text with gemini logic in the NLP/parser layer.

    Args:
        prompt: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        model_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        temperature: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    llm = get_gemini_llm(model_name or DEFAULT_TEXT_MODEL, float(temperature))
    response = llm.invoke([HumanMessage(content=prompt)])
    return _extract_text(response)


# Helper for make data url.
def _make_data_url(image_bytes: bytes, mime_type: str) -> str:
    """Coordinate the make data url logic in the NLP/parser layer.

    Args:
        image_bytes: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        mime_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type or 'image/jpeg'};base64,{encoded}"


# Helper for generate text from image with gemini.
def generate_text_from_image_with_gemini(
    prompt: str,
    image_bytes: bytes,
    *,
    mime_type: str = "image/jpeg",
    model_name: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Coordinate the generate text from image with gemini logic in the NLP/parser layer.

    Args:
        prompt: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        image_bytes: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        mime_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        model_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        temperature: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Validate missing image bytes before continuing.
    if not image_bytes:
        raise ValueError("File gambar kosong atau gagal dibaca.")

    llm = get_gemini_llm(model_name or DEFAULT_IMAGE_MODEL, float(temperature))
    data_url = _make_data_url(image_bytes, mime_type)

    # Format standar LangChain multimodal.
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": data_url},
    ]

    # Run this operation in a guarded block so failures can be handled.
    try:
        response = llm.invoke([HumanMessage(content=content)])
        return _extract_text(response)
    # Handle an expected failure from the guarded operation above.
    except Exception as first_error:
        alt_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        # Run this operation in a guarded block so failures can be handled.
        try:
            response = llm.invoke([HumanMessage(content=alt_content)])
            return _extract_text(response)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Raise a clear error so the caller can stop this invalid flow.
            raise first_error
