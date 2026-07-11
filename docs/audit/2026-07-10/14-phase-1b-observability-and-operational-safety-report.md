# Phase 1B Observability and Operational Safety Report

- Date completed: 2026-07-11
- Baseline branch: `codex/check-worktree-access`
- External services: not called
- Live AI evaluation: `NOT_RUN`

## Scope completed

- Retained explicit accounts in new debt and receivable cashflow parsing, including `dari DANA`.
- Verified the existing budget mutation flow uses an immutable preview and writes only after confirmation.
- Centralized finance dates on an explicit `Asia/Jakarta` business clock while retaining UTC for logs and pending-action TTL.
- Added structured redacted application events, correlation IDs, aggregate counters, and duration metrics without raw finance input.
- Added Gemini timeout, output token limit, output character cap, provider usage capture when available, and bounded telemetry.
- Added generic readiness state and `/ready` while preserving the existing `/health` liveness response.
- Enforced the current single-instance scheduler policy and added collision-safe temporary export files.
- Documented operational environment variables and Python 3.12 as the CI-supported runtime.

## Safety contracts

| Area | Contract |
| :--- | :--- |
| Logging | No message text, prompt, finance payload, credential, or raw exception is emitted by the new observability layer. |
| Gemini | Calls have configured timeout/output bounds; usage is recorded only when the provider returns numeric metadata. |
| Readiness | Configuration, Sheets/schema startup, Telegram, and enabled scheduler states determine HTTP 200 versus 503. |
| Scheduler | More than one application instance is rejected while the built-in scheduler is enabled. |
| Exports | Each export receives a unique temporary path and cleanup remains in `finally`. |
| Business dates | Finance logic uses `APP_TIMEZONE`; operational timestamps and action expiry use UTC. |

## Audit finding status

| Finding | Phase 1B status | Remaining verification |
| :--- | :--- | :--- |
| F-012 Gemini bounds and usage observability | Implemented offline | Confirm provider-specific timeout and usage metadata in opt-in staging. |
| F-014 formal regression suite | Closed in Phase 1A; extended | Keep default offline CI green. |
| F-017 pending TTL | Closed in Phase 0 | Persistence across process restarts remains a future architecture decision. |
| F-018 explicit business timezone | Implemented | Exercise month/day rollover in staging. |
| F-020 readiness and single-instance contract | Implemented | Validate deployment probes and scheduler ownership in the real host. |
| F-023 reproducible configuration | Partially closed | Environment examples and Python runtime are explicit; a fully locked transitive dependency artifact is still not provided. |

## Owner decisions closed

- Debt/receivable inputs with an explicit valid account retain that account, so `Budi minjem 50k dari DANA` is ready for final preview.
- Budget writes require preview and explicit confirmation. Read-only budget commands do not require confirmation.

## Verification

The first full Phase 1B run reported `1 failed, 160 passed`. The failure occurred before the observability handler executed: Windows `ProactorEventLoop` initialized its internal socket pair through a local `127.0.0.1` connection, and the original raw socket guard rejected every connection indiscriminately. This was a test-infrastructure false positive, not an application network call.

The guard now permits only explicit operating-system loopback addresses (`localhost`, IPv4 loopback, and IPv6 loopback) at the raw socket fallback. Non-loopback sockets remain rejected, while Telegram, Gemini, gspread, HTTPX, Requests, credentials, and live-evaluation boundaries remain independently blocked. Regression tests make sure a localhost URL cannot bypass those higher-level guards.

| Command | Result |
| :--- | :--- |
| Pre-change baseline `python -m pytest -q tests` | 143 passed in 3.23 seconds. |
| Targeted debt/multi regression after the parser fix | 57 passed in 2.74 seconds. |
| First full Phase 1B run | 1 failed, 160 passed; Windows asyncio loopback false positive. |
| Final `python -m pytest -q` | 170 passed in 2.76 seconds. |
| `python -m pytest -q tests/integration/test_handler_observability.py` | 1 passed in 0.80 seconds. |
| `python -m pytest -q -k external` | 12 passed, 158 deselected in 1.28 seconds. |
| `python -m compileall -q app evals main.py tests` | Pass. |
| `git diff --check` | Pass; line-ending notices are informational. |
| Debug-matrix recount | 168 total: 60 offline, 16 fake-state, 5 live AI, 77 staging, 0 ambiguous, and 10 obsolete. |

No production credentials or real external network calls were used. Pytest emitted one cache warning because `.pytest_cache` could not be recreated in the worktree; it did not affect test collection or results.

## Staging checklist

1. Confirm `/health` remains 200 while `/ready` changes from 503 to 200 only after dependencies are ready.
2. Run one debt/receivable DANA preview, cancel it, then repeat and save it; confirm the DANA balance delta exactly once.
3. Run budget preview, Batal, and Simpan against a dummy sheet; confirm no write occurs before Simpan.
4. Trigger one scheduled export and one manual export close together; confirm distinct files and cleanup.
5. Run an opt-in Gemini request; verify timeout behavior and that logs contain metadata but no prompt or finance text.

No commit or push was performed by this implementation task.
