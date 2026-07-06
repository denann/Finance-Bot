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


# Define require api key for callers in this flow.
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
    # Handle the missing or empty GEMINI_API_KEY case.
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY belum tersedia.")
    # Return GEMINI_API_KEY to the caller.
    return GEMINI_API_KEY


# Apply this decorator before the callable is registered or executed.
@lru_cache(maxsize=32)
# Define get gemini llm for callers in this flow.
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
    # Return ChatGoogleGenerativeAI( to the caller.
    return ChatGoogleGenerativeAI(
        # Prepare model for the next step.
        model=model_name,
        # Prepare google api key for the next step.
        google_api_key=_require_api_key(),
        # Prepare temperature for the next step.
        temperature=temperature,
    # Close the structure that was opened above.
    )


# Define extract text for callers in this flow.
def _extract_text(response: Any) -> str:
    """Extract the required part of input for text."""
    content = getattr(response, "content", "")

    # Handle the case where isinstance(content, str).
    if isinstance(content, str):
        # Return content.strip() to the caller.
        return content.strip()

    # Handle the case where isinstance(content, list).
    if isinstance(content, list):
        # Run this statement as part of the current workflow.
        parts: list[str] = []
        # Process each item in the current collection.
        for item in content:
            # Handle the case where isinstance(item, str).
            if isinstance(item, str):
                # Update parts with the current value.
                parts.append(item)
            # Handle the alternate case where isinstance(item, dict).
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                # Handle the case where text.
                if text:
                    # Update parts with the current value.
                    parts.append(str(text))
        return "\n".join(parts).strip()

    return str(content or "").strip()


# Define generate text with gemini for callers in this flow.
def generate_text_with_gemini(
    # Include this value in the surrounding collection or call.
    prompt: str,
    # Include this value in the surrounding collection or call.
    *,
    # Include this value in the surrounding collection or call.
    model_name: str | None = None,
    # Include this value in the surrounding collection or call.
    temperature: float = 0.0,
# Close the structure that was opened above.
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
    # Prepare llm for the next step.
    llm = get_gemini_llm(model_name or DEFAULT_TEXT_MODEL, float(temperature))
    # Prepare response for the next step.
    response = llm.invoke([HumanMessage(content=prompt)])
    # Return _extract_text(response) to the caller.
    return _extract_text(response)


# Define make data url for callers in this flow.
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


# Define generate text from image with gemini for callers in this flow.
def generate_text_from_image_with_gemini(
    # Include this value in the surrounding collection or call.
    prompt: str,
    # Include this value in the surrounding collection or call.
    image_bytes: bytes,
    # Include this value in the surrounding collection or call.
    *,
    mime_type: str = "image/jpeg",
    # Include this value in the surrounding collection or call.
    model_name: str | None = None,
    # Include this value in the surrounding collection or call.
    temperature: float = 0.0,
# Close the structure that was opened above.
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
    # Handle the missing or empty image_bytes case.
    if not image_bytes:
        raise ValueError("File gambar kosong atau gagal dibaca.")

    # Prepare llm for the next step.
    llm = get_gemini_llm(model_name or DEFAULT_IMAGE_MODEL, float(temperature))
    # Prepare data url for the next step.
    data_url = _make_data_url(image_bytes, mime_type)

    # Format standar LangChain multimodal.
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": data_url},
    # Close the structure that was opened above.
    ]

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare response for the next step.
        response = llm.invoke([HumanMessage(content=content)])
        # Return _extract_text(response) to the caller.
        return _extract_text(response)
    # Handle an expected failure from the guarded operation above.
    except Exception as first_error:
        # Parser rule note for an Indonesian finance input edge case.
        alt_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        # Close the structure that was opened above.
        ]
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare response for the next step.
            response = llm.invoke([HumanMessage(content=alt_content)])
            # Return _extract_text(response) to the caller.
            return _extract_text(response)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Raise a clear error so the caller can stop this invalid flow.
            raise first_error
