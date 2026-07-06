"""Gemini helper for generating category aliases.

The category wizard uses this module only to ask Gemini for candidate words.
The final aliases are still normalized by `resolver_service` before they are
shown in preview or written to Google Sheets.
"""

# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import json for this module's local operations.
import json
# Import re for this module's local operations.
import re

# Import app.nlp.gemini_langchain_client so this module can use its helpers.
from app.nlp.gemini_langchain_client import generate_text_with_gemini


# Define extract json object for callers in this flow.
def _extract_json_object(text: str) -> dict:
    """Extract the first JSON object from a Gemini text response.

    Args:
        text: Raw model response. Expected ideal form is compact JSON such as
            `{"aliases":["belanja","shopping"]}`, but the function also accepts
            responses wrapped in extra prose or code fences.

    Returns:
        Parsed JSON as a dict. Returns an empty dict when the text is empty,
        invalid JSON, or does not contain a JSON object.
    """
    # Normalize the model response before JSON parsing.
    raw = str(text or "").strip()
    # Empty model output cannot produce aliases.
    if not raw:
        # Return {} to the caller.
        return {}

    # First try the ideal contract: response is already pure JSON.
    try:
        # Return json.loads(raw) to the caller.
        return json.loads(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # If Gemini wraps JSON in prose, extract the first object-shaped block.
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    # Handle the missing or empty match case.
    if not match:
        # Return {} to the caller.
        return {}

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return json.loads(match.group(0)) to the caller.
        return json.loads(match.group(0))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return {} to the caller.
        return {}


# Define generate category alias candidates for callers in this flow.
def generate_category_alias_candidates(
    # Include this value in the surrounding collection or call.
    category_name: str,
    # Include this value in the surrounding collection or call.
    transaction_type: str,
    # Include this value in the surrounding collection or call.
    *,
    # Include this value in the surrounding collection or call.
    limit: int = 20,
# Close the structure that was opened above.
) -> list[str]:
    """Generate raw alias candidates for a finance category using Gemini.

    Args:
        category_name: Category name supplied by the user, for example
            `Belanja Online`, `Freelance`, or `Cashback`.
        transaction_type: Category type from the wizard. `income` is treated as
            income; any other value is treated as expense.
        limit: Requested maximum number of aliases. The helper clamps this to
            the safe range 8-24 so the sheet value stays readable.

    Returns:
        A list of raw alias strings from Gemini. The list is not trusted as the
        final sheet value; callers must pass it through
        `normalize_category_aliases`.

    Prompt contract:
        Gemini is instructed to return only JSON with an `aliases` array,
        lowercase words or short phrases, no emoji, no amounts, no full
        sentences, and no overly broad finance words.
    """
    # Clean category name for prompt readability.
    clean_name = str(category_name or "").strip()
    # Only income stays income; all other inputs follow expense alias rules.
    clean_type = "income" if str(transaction_type or "").strip().lower() == "income" else "expense"
    # Clamp alias count so Gemini output stays useful and sheet-friendly.
    safe_limit = min(max(int(limit or 20), 8), 24)

    # Prompt is strict because downstream resolver expects short alias phrases.
    prompt = f"""
You generate aliases for an Indonesian personal finance Telegram bot.

Category name: {clean_name}
Transaction type: {clean_type}

Return ONLY compact JSON with this exact shape:
{{"aliases":["alias 1","alias 2"]}}

Rules:
- Generate {safe_limit} or fewer aliases.
- Include the category name itself as one alias.
- Use Indonesian daily finance words first, then common English words if useful.
- Include common merchant/platform/item words only when they are strongly related.
- Aliases must be lowercase words or short phrases.
- No emoji, no symbols, no hashtags, no amounts, no full sentences.
- Avoid overly broad aliases such as uang, bayar, transaksi, masuk, keluar, biaya, income, expense.
- Do not include aliases that would usually belong to the opposite transaction type.
""".strip()

    # Low temperature keeps alias suggestions stable and conservative.
    response_text = generate_text_with_gemini(prompt, temperature=0.2)
    # Prefer JSON parsing because it is less ambiguous than comma parsing.
    data = _extract_json_object(response_text)
    aliases = data.get("aliases") if isinstance(data, dict) else None

    # JSON aliases are returned as raw candidates for resolver normalization.
    if isinstance(aliases, list):
        return [str(item).strip() for item in aliases if str(item or "").strip()]

    # Fallback parser handles non-JSON model output without failing the wizard.
    return [
        # Run this statement as part of the current workflow.
        part.strip()
        for part in re.split(r"[,;\n]+", response_text)
        # Handle the case where part.strip().
        if part.strip()
    # Close the structure that was opened above.
    ]
