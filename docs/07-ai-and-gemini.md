# AI and Gemini

## Feature Boundary

Gemini supports transaction fallback parsing, intent routing, receipt/image parsing, category alias suggestions, and `/ask`, `/insight`, `/audit`, and `/coach`. Deterministic Python logic still owns routing, finance calculations, period selection, aggregate preparation, validation, clarification, previews, and every write decision.

Gemini never writes directly to Google Sheets and does not bypass account selection or confirmation.

## Model Configuration

| Setting | Purpose |
| :--- | :--- |
| `GEMINI_MODEL` | General text fallback |
| `GEMINI_TEXT_MODEL` | Transaction parser |
| `GEMINI_INTENT_MODEL` | Intent router |
| `GEMINI_IMAGE_MODEL` | Receipt/image parser |
| `GEMINI_INSIGHT_MODEL` | Finance answers and insight |

The deployed model values come from environment configuration. Phase 4 does not change model selection, temperature, prompt meaning, structured output, or answer format.

## Prompt Versions and Call Budgets

Stable metadata versions distinguish transaction parser, intent router, finance ask/insight/audit/coach, image receipt, and category alias prompts. Prompt text itself is not logged.

| Request type | Budget |
| :--- | :--- |
| Regex/local success | 0 calls |
| Text parser/router path | At most 1 primary call per Telegram update |
| Multi-input unresolved items | At most 1 batch call, not one call per line |
| Explicit AI feature | At most 1 generation call after deterministic context preparation |
| Image receipt | Normally 1 call |
| Recognized image invocation-format compatibility error | At most 2 total calls |
| Auth, permission, quota, timeout, network, provider, safety, malformed output, unknown error | No second image call |

When the request budget is exhausted, the caller clarifies or returns a bounded unavailable/deterministic response. It does not silently create a transaction.

## Input, Output, and Context Bounds

- `GEMINI_MAX_INPUT_CHARS=100000` by default.
- `GEMINI_MAX_OUTPUT_TOKENS=2048` by default.
- `GEMINI_MAX_OUTPUT_CHARS=50000` by default.
- `AI_CONTEXT_RECORD_LIMIT=40` relevant transactions by default.
- `GEMINI_TIMEOUT_SECONDS=30` and `GEMINI_CONCURRENCY=1` by default.

Totals, category rankings, budget status, anomalies, net worth, and projections are calculated locally first. AI receives aggregates and a bounded relevant subset with metadata for considered/selected records, truncation, date range, and aggregation level. It does not receive an entire raw history merely because it exists.

## Usage and Metrics

Structured events attribute feature, model, call count, input/output characters, duration, outcome, prompt version, attempt, and compatibility source/target. Input/output token values are recorded only when numeric provider usage metadata exists; absence is recorded as unavailable. Currency prices are not hard-coded.

## Privacy and Redaction

Do not log or use metric labels containing prompts, raw user text, finance descriptions, account/person names, transaction IDs, receipt bytes, credentials, service-account data, or spreadsheet access details. Correlation IDs are opaque. Sanitization is defense in depth; operators must still use dummy data for staging and review logs.

## Evaluation and Fallback

Default pytest uses fakes and an external-call guard. Live Gemini evaluation is disabled unless explicitly enabled and provided a key; see `evals/README.md`. Offline golden contracts verify schemas and context preparation, not narrative quality. If Gemini is unavailable, supported flows use deterministic fallback or clarification without weakening write safety.

| Documentation update | Status |
| :--- | :--- |
| Models and prompt meaning | Unchanged |
| Call/context/output bounds | Documented from config |
| Usage and privacy semantics | Documented |
| Live evaluation | Explicit opt-in only |
