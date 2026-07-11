"""Security policy and read-only helpers for optional web diagnostics."""

from __future__ import annotations

from enum import Enum
from hmac import compare_digest
from typing import Callable, Mapping


class DiagnosticAccess(str, Enum):
    """Represent whether the legacy Sheets diagnostic may be executed."""

    DISABLED = "disabled"
    FORBIDDEN = "forbidden"
    AUTHORIZED = "authorized"


def evaluate_diagnostic_access(environ: Mapping[str, str], provided_secret: str | None) -> DiagnosticAccess:
    """Evaluate the default-off admin policy without touching Google Sheets.

    Args:
        environ: Environment-like mapping containing the feature flag and
            diagnostic secret.
        provided_secret: Secret supplied by the HTTP caller.

    Returns:
        ``DISABLED`` when the route is not explicitly enabled, ``FORBIDDEN``
        for missing or invalid credentials, otherwise ``AUTHORIZED``.

    Side effects:
        None. In particular, this function never reads spreadsheet metadata or
        invokes schema setup.
    """

    enabled = str(environ.get("ENABLE_TEST_SHEETS_ROUTE", "false")).strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return DiagnosticAccess.DISABLED

    expected = str(environ.get("DIAGNOSTIC_ADMIN_SECRET", "")).strip()
    supplied = str(provided_secret or "").strip()
    if not expected or not supplied or not compare_digest(expected, supplied):
        return DiagnosticAccess.FORBIDDEN

    return DiagnosticAccess.AUTHORIZED


def run_read_only_sheets_diagnostic(probe: Callable[[], object]) -> dict[str, str]:
    """Run one caller-provided connectivity probe and redact its metadata.

    Args:
        probe: Zero-argument callable that performs a bounded, read-only Sheets
            connectivity check. It must not create or repair schema.

    Returns:
        Generic connectivity status without spreadsheet names, worksheet
        titles, credentials, schema actions, or exception details.

    Raises:
        Any probe exception so the HTTP boundary can translate it into a
        generic service-unavailable response.
    """

    probe()
    return {"status": "connected"}
