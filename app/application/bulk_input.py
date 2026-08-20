"""Pure item-level state model for multi-input clarification."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from app.application.results import ClarificationRequired, PreviewReady, immutable_payload


class BulkItemStatus(str, Enum):
    """Lifecycle state for one item in a multi-input session."""

    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    REJECTED = "rejected"
    RESOLVED = "resolved"
    REMOVED = "removed"


@dataclass(frozen=True, slots=True)
class BulkItem:
    """Stable, ordered state for one user-supplied bulk item."""

    item_id: str
    original_index: int
    raw_input: str
    status: BulkItemStatus
    kind: str = "failed"
    parsed_payload: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    missing_fields: tuple[str, ...] = ()
    clarification_reason: str = ""
    validation_errors: tuple[str, ...] = ()
    resolved_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BulkSession:
    """Immutable state for one ordered multi-input clarification session."""

    session_id: str
    items: tuple[BulkItem, ...]
    awaiting_item_id: str = ""
    awaiting_mode: str = ""
    cancelled: bool = False


class StaleBulkSession(ValueError):
    """Raised when a callback targets an old session or another item."""


def make_bulk_item(
    *,
    item_id: str,
    original_index: int,
    raw_input: str,
    legacy_item: Mapping[str, Any],
    invalid_date: bool = False,
    safety_requires_clarification: bool = False,
    needs_account: bool = False,
    needs_split_decision: bool = False,
) -> BulkItem:
    """Classify one parser result without Telegram or persistence dependencies."""

    kind = str(legacy_item.get("kind") or "failed")
    parsed = deepcopy(dict(legacy_item.get("parsed") or {}))
    payload = MappingProxyType(parsed)

    if invalid_date:
        return BulkItem(
            item_id=item_id,
            original_index=original_index,
            raw_input=raw_input,
            status=BulkItemStatus.REJECTED,
            kind=kind,
            parsed_payload=payload,
            clarification_reason="invalid_date",
            validation_errors=("Tanggal tidak valid.",),
        )
    if kind == "failed":
        return BulkItem(
            item_id=item_id,
            original_index=original_index,
            raw_input=raw_input,
            status=BulkItemStatus.REJECTED,
            kind=kind,
            parsed_payload=payload,
            clarification_reason="parse_failed",
            validation_errors=("Input belum dapat dipahami dengan aman.",),
        )
    if kind == "missing_amount" or float(parsed.get("amount") or 0) <= 0:
        return BulkItem(
            item_id=item_id,
            original_index=original_index,
            raw_input=raw_input,
            status=BulkItemStatus.NEEDS_CLARIFICATION,
            kind=kind,
            parsed_payload=payload,
            missing_fields=("amount",),
            clarification_reason="missing_amount",
        )
    if safety_requires_clarification:
        return BulkItem(
            item_id=item_id,
            original_index=original_index,
            raw_input=raw_input,
            status=BulkItemStatus.NEEDS_CLARIFICATION,
            kind=kind,
            parsed_payload=payload,
            clarification_reason="ambiguous_parse",
        )
    if needs_account:
        return BulkItem(
            item_id=item_id,
            original_index=original_index,
            raw_input=raw_input,
            status=BulkItemStatus.NEEDS_CLARIFICATION,
            kind=kind,
            parsed_payload=payload,
            missing_fields=("account",),
            clarification_reason="missing_account",
        )
    if needs_split_decision:
        return BulkItem(
            item_id=item_id,
            original_index=original_index,
            raw_input=raw_input,
            status=BulkItemStatus.NEEDS_CLARIFICATION,
            kind=kind,
            parsed_payload=payload,
            missing_fields=("split_decision",),
            clarification_reason="split_decision",
        )
    return BulkItem(
        item_id=item_id,
        original_index=original_index,
        raw_input=raw_input,
        status=BulkItemStatus.READY,
        kind=kind,
        parsed_payload=payload,
    )


def create_bulk_session(items: list[BulkItem], session_id: str | None = None) -> BulkSession:
    """Create one ordered session from independently classified items."""

    ordered = tuple(sorted(items, key=lambda item: item.original_index))
    return BulkSession(session_id=session_id or uuid4().hex[:10], items=ordered)


def current_issue(session: BulkSession) -> BulkItem | None:
    """Return the first unresolved item in original input order."""

    for item in session.items:
        if item.status in {BulkItemStatus.NEEDS_CLARIFICATION, BulkItemStatus.REJECTED}:
            return item
    return None


def result_for_session(session: BulkSession):
    """Return clarification or immutable final-preview state for a session."""

    issue = current_issue(session)
    if issue is not None:
        mode = {
            "missing_amount": "amount",
            "missing_account": "account",
            "split_decision": "split",
            "semantic_split_payer": "semantic_split_payer",
            "semantic_split_allocation": "semantic_split_allocation",
            "semantic_split_custom": "semantic_split_custom_text",
            "semantic_split_status": "semantic_split_status",
        }.get(issue.clarification_reason, "rewrite_or_remove")
        waiting = replace(session, awaiting_item_id=issue.item_id, awaiting_mode=mode)
        return ClarificationRequired(
            message=issue.clarification_reason,
            reason=issue.clarification_reason,
            missing_fields=issue.missing_fields,
            payload=immutable_payload({"session": waiting, "item": issue}),
        )

    mixed_items = [
        {
            "kind": item.kind,
            "parsed": deepcopy(dict(item.parsed_payload)),
            "raw": item.raw_input,
            "item_id": item.item_id,
            "original_index": item.original_index,
        }
        for item in session.items
        if item.status != BulkItemStatus.REMOVED
    ]
    ready = replace(session, awaiting_item_id="", awaiting_mode="")
    return PreviewReady(
        message="bulk_preview_ready",
        payload=immutable_payload({"session": ready, "mixed_items": mixed_items}),
    )


def assert_current_target(session: BulkSession, session_id: str, item_id: str = "") -> None:
    """Reject stale callback targets before they can change session state."""

    if session.cancelled or session.session_id != session_id:
        raise StaleBulkSession("Sesi bulk sudah tidak aktif.")
    if item_id and session.awaiting_item_id != item_id:
        raise StaleBulkSession("Item klarifikasi sudah berubah.")


def replace_bulk_item(session: BulkSession, replacement: BulkItem) -> BulkSession:
    """Replace only the targeted item while retaining identity and order."""

    replaced = False
    items: list[BulkItem] = []
    for item in session.items:
        if item.item_id == replacement.item_id:
            items.append(replacement)
            replaced = True
        else:
            items.append(item)
    if not replaced:
        raise StaleBulkSession("Item bulk tidak ditemukan.")
    return replace(session, items=tuple(items), awaiting_item_id="", awaiting_mode="")


def resolve_bulk_item(
    session: BulkSession,
    item_id: str,
    *,
    parsed_payload: Mapping[str, Any],
    kind: str | None = None,
    resolved_field: str,
) -> BulkSession:
    """Resolve one field on one item and preserve all unrelated items."""

    target = next((item for item in session.items if item.item_id == item_id), None)
    if target is None:
        raise StaleBulkSession("Item bulk tidak ditemukan.")
    replacement = replace(
        target,
        kind=kind or target.kind,
        parsed_payload=MappingProxyType(deepcopy(dict(parsed_payload))),
        status=BulkItemStatus.RESOLVED,
        missing_fields=(),
        clarification_reason="",
        validation_errors=(),
        resolved_fields=tuple(dict.fromkeys((*target.resolved_fields, resolved_field))),
    )
    return replace_bulk_item(session, replacement)


def remove_bulk_item(session: BulkSession, item_id: str) -> BulkSession:
    """Mark one rejected item removed after an explicit owner decision."""

    target = next((item for item in session.items if item.item_id == item_id), None)
    if target is None:
        raise StaleBulkSession("Item bulk tidak ditemukan.")
    replacement = replace(
        target,
        status=BulkItemStatus.REMOVED,
        missing_fields=(),
        clarification_reason="",
        validation_errors=(),
    )
    return replace_bulk_item(session, replacement)


def await_rewrite(session: BulkSession, item_id: str) -> BulkSession:
    """Mark the current item as waiting for replacement text."""

    if session.awaiting_item_id != item_id:
        raise StaleBulkSession("Item klarifikasi sudah berubah.")
    return replace(session, awaiting_mode="rewrite_text")


def cancel_bulk_session(session: BulkSession) -> BulkSession:
    """Invalidate the entire session without producing a mutation payload."""

    return replace(session, cancelled=True, awaiting_item_id="", awaiting_mode="")

