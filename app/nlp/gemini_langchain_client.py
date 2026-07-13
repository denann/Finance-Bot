"""LangChain wrapper for calling Gemini consistently across text and image features."""


# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import base64 for this module's local operations.
import base64
# Import os for this module's local operations.
# Import functools so this module can use its helpers.
from functools import lru_cache
# Import typing so this module can use its helpers.
from typing import Any

# Import langchain_core.messages so this module can use its helpers.
from langchain_core.messages import HumanMessage
# Import langchain_google_genai so this module can use its helpers.
from langchain_google_genai import ChatGoogleGenerativeAI

# Import app.config so this module can use its helpers.
from app.config import (
    GEMINI_API_KEY,
    GEMINI_IMAGE_MODEL,
    GEMINI_INSIGHT_MODEL,
    GEMINI_MAX_OUTPUT_CHARS,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MAX_INPUT_CHARS,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
)
from app.observability import emit_event, increment_metric, monotonic_ms, observe_duration
from app.application.gemini_governance import (
    GeminiInputTooLarge,
    current_or_local_budget,
    prompt_version as resolve_prompt_version,
)


DEFAULT_TEXT_MODEL = GEMINI_MODEL
DEFAULT_IMAGE_MODEL = GEMINI_IMAGE_MODEL
DEFAULT_INSIGHT_MODEL = GEMINI_INSIGHT_MODEL
GEMINI_CLIENT_VERSION = "phase1b-v1"


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
        timeout=GEMINI_TIMEOUT_SECONDS,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
    )


# Helper for extract text.
def _extract_text(response: Any) -> str:
    """Extract the required part of input for text."""
    content = getattr(response, "content", "")

    if isinstance(content, str):
        return content.strip()[:GEMINI_MAX_OUTPUT_CHARS]

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
        return "\n".join(parts).strip()[:GEMINI_MAX_OUTPUT_CHARS]

    return str(content or "").strip()[:GEMINI_MAX_OUTPUT_CHARS]


def _extract_usage(response: Any) -> dict[str, int | None]:
    """Extract provider usage only when the response exposes numeric metadata."""

    usage = getattr(response, "usage_metadata", None) or {}
    if not isinstance(usage, dict):
        usage = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    def numeric(*keys: str) -> int | None:
        for key in keys:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                return int(value)
        return None

    return {
        "input_tokens": numeric("input_tokens", "prompt_token_count", "prompt_tokens"),
        "output_tokens": numeric("output_tokens", "candidates_token_count", "completion_tokens"),
        "total_tokens": numeric("total_tokens", "total_token_count"),
    }


def _invoke_with_observability(
    llm: Any,
    message: HumanMessage,
    *,
    model_name: str,
    modality: str,
    feature: str,
    prompt_version: str,
    input_characters: int,
    attempt: int,
    fallback_source: str = "",
    fallback_target: str = "",
) -> Any:
    """Invoke Gemini with bounded metadata logging and no prompt content."""

    started = monotonic_ms()
    increment_metric("gemini.calls")
    try:
        response = llm.invoke([message])
    except Exception as exc:
        duration_ms = monotonic_ms() - started
        increment_metric("gemini.errors")
        observe_duration("gemini.latency_ms", duration_ms)
        emit_event(
            "gemini_call_failed",
            model=model_name,
            modality=modality,
            feature=feature,
            prompt_version=prompt_version,
            input_characters=input_characters,
            attempt=attempt,
            fallback_source=fallback_source,
            fallback_target=fallback_target,
            client_version=GEMINI_CLIENT_VERSION,
            duration_ms=round(duration_ms, 3),
            error_type=type(exc).__name__,
        )
        raise

    duration_ms = monotonic_ms() - started
    usage = _extract_usage(response)
    observe_duration("gemini.latency_ms", duration_ms)
    increment_metric("gemini.success")
    emit_event(
        "gemini_call_completed",
        model=model_name,
        modality=modality,
        client_version=GEMINI_CLIENT_VERSION,
        duration_ms=round(duration_ms, 3),
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        total_tokens=usage["total_tokens"],
        usage_available=any(value is not None for value in usage.values()),
        feature=feature,
        prompt_version=prompt_version,
        input_characters=input_characters,
        output_characters=len(_extract_text(response)),
        attempt=attempt,
        fallback_source=fallback_source,
        fallback_target=fallback_target,
    )
    return response


# Helper for generate text with gemini.
def generate_text_with_gemini(
    prompt: str,
    *,
    model_name: str | None = None,
    temperature: float = 0.0,
    feature: str = "generic_text",
    prompt_version: str | None = None,
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
    selected_model = model_name or DEFAULT_TEXT_MODEL
    input_characters = len(str(prompt or ""))
    if input_characters > GEMINI_MAX_INPUT_CHARS:
        increment_metric("gemini.input_too_large")
        raise GeminiInputTooLarge("Input Gemini melewati batas karakter.")
    budget = current_or_local_budget()
    attempt = budget.consume(feature)
    version = prompt_version or resolve_prompt_version(feature)
    llm = get_gemini_llm(selected_model, float(temperature))
    response = _invoke_with_observability(
        llm,
        HumanMessage(content=prompt),
        model_name=selected_model,
        modality="text",
        feature=feature,
        prompt_version=version,
        input_characters=input_characters,
        attempt=attempt,
    )
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
    feature: str = "image_receipt_parser",
    prompt_version: str | None = None,
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

    selected_model = model_name or DEFAULT_IMAGE_MODEL
    input_characters = len(str(prompt or ""))
    if input_characters > GEMINI_MAX_INPUT_CHARS:
        increment_metric("gemini.input_too_large")
        raise GeminiInputTooLarge("Input Gemini melewati batas karakter.")
    budget = current_or_local_budget()
    attempt = budget.consume(feature)
    version = prompt_version or resolve_prompt_version(feature)
    llm = get_gemini_llm(selected_model, float(temperature))
    data_url = _make_data_url(image_bytes, mime_type)

    # Format standar LangChain multimodal.
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": data_url},
    ]

    # Run this operation in a guarded block so failures can be handled.
    try:
        response = _invoke_with_observability(
            llm,
            HumanMessage(content=content),
            model_name=selected_model,
            modality="image",
            feature=feature,
            prompt_version=version,
            input_characters=input_characters,
            attempt=attempt,
        )
        return _extract_text(response)
    # Handle an expected failure from the guarded operation above.
    except Exception as first_error:
        message = str(first_error).lower()
        compatibility_error = isinstance(first_error, (TypeError, ValueError)) and any(
            marker in message for marker in ("image_url", "schema", "content format", "invocation format")
        )
        if not compatibility_error:
            raise
        fallback_attempt = budget.consume(feature, compatibility=True)
        increment_metric("gemini.fallback")
        alt_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        # Run this operation in a guarded block so failures can be handled.
        try:
            response = _invoke_with_observability(
                llm,
                HumanMessage(content=alt_content),
                model_name=selected_model,
                modality="image_fallback",
                feature=feature,
                prompt_version=version,
                input_characters=input_characters,
                attempt=fallback_attempt,
                fallback_source="image_url_string",
                fallback_target="image_url_object",
            )
            return _extract_text(response)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Raise a clear error so the caller can stop this invalid flow.
            raise first_error
