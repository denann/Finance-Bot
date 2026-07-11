"""In-memory immutable action snapshots for one-shot Telegram confirmations."""

from __future__ import annotations

import copy
import secrets
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, MutableMapping


ACTION_STORE_KEY = "_pending_actions"
DEFAULT_ACTION_TTL_SECONDS = 15 * 60
MAX_ACTIONS_PER_USER = 50


class PendingActionError(RuntimeError):
    """Describe why a pending action cannot transition or be consumed."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ActionRequestContext:
    """Hold request-local values used while building an inline keyboard."""

    user_data: MutableMapping[str, Any]
    owner_user_id: int
    preview_message_id: int | None = None


_request_context: ContextVar[ActionRequestContext | None] = ContextVar(
    "pending_action_request_context",
    default=None,
)


def utc_now() -> datetime:
    """Return the current aware UTC time for lifecycle comparisons."""

    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    """Serialize an aware datetime with an explicit timezone offset."""

    return value.astimezone(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    """Parse stored lifecycle timestamps without raising on missing values."""

    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _store(user_data: MutableMapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the per-user in-memory action store, creating it if needed."""

    store = user_data.get(ACTION_STORE_KEY)
    if not isinstance(store, dict):
        store = {}
        user_data[ACTION_STORE_KEY] = store
    return store


def cleanup_actions(user_data: MutableMapping[str, Any], *, now: datetime | None = None) -> None:
    """Mark expired pending actions and cap retained terminal history."""

    current = now or utc_now()
    store = _store(user_data)
    for action in store.values():
        expires_at = _parse_iso(action.get("expires_at"))
        if action.get("status") == "pending" and expires_at and current >= expires_at:
            action["status"] = "expired"

    if len(store) <= MAX_ACTIONS_PER_USER:
        return

    ordered = sorted(store.values(), key=lambda item: str(item.get("created_at") or ""))
    removable = [item for item in ordered if item.get("status") != "pending"]
    for item in removable[: max(0, len(store) - MAX_ACTIONS_PER_USER)]:
        store.pop(str(item.get("action_id")), None)


def create_pending_action(
    user_data: MutableMapping[str, Any],
    *,
    owner_user_id: int,
    flow_type: str,
    payload: dict[str, Any],
    preview_message_id: int | None = None,
    ttl_seconds: int = DEFAULT_ACTION_TTL_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create an immutable payload snapshot addressed by a short opaque ID.

    Args:
        user_data: PTB per-user state where the in-memory store is retained.
        owner_user_id: Telegram user allowed to consume the action.
        flow_type: Stable flow identifier used to route confirmation.
        payload: Exact action data represented by the rendered preview.
        preview_message_id: Telegram message ID when already known.
        ttl_seconds: Positive lifetime for the confirmation.
        now: Injectable UTC timestamp used by deterministic tests.

    Returns:
        Defensive copy of the stored action record.

    Side effects:
        Adds one in-memory record. It never writes Google Sheets or any other
        persistent store.
    """

    if not isinstance(owner_user_id, int) or owner_user_id <= 0:
        raise ValueError("owner_user_id harus berupa Telegram user ID yang valid.")
    if not str(flow_type or "").strip():
        raise ValueError("flow_type tidak boleh kosong.")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds harus lebih dari 0.")

    current = now or utc_now()
    cleanup_actions(user_data, now=current)
    action_id = "a_" + secrets.token_urlsafe(9).rstrip("=")
    record = {
        "action_id": action_id,
        "owner_user_id": owner_user_id,
        "flow_type": str(flow_type).strip(),
        "payload": copy.deepcopy(payload),
        "preview_message_id": preview_message_id,
        "created_at": _iso(current),
        "expires_at": _iso(current + timedelta(seconds=ttl_seconds)),
        "consumed_at": None,
        "status": "pending",
    }
    _store(user_data)[action_id] = record
    return copy.deepcopy(record)


def get_pending_action(user_data: MutableMapping[str, Any], action_id: str) -> dict[str, Any] | None:
    """Return a defensive copy of one action without changing its status."""

    record = _store(user_data).get(str(action_id or ""))
    return copy.deepcopy(record) if isinstance(record, dict) else None


def bind_action_message(user_data: MutableMapping[str, Any], action_id: str, message_id: int | None) -> None:
    """Bind a newly sent preview message ID while the action is still pending."""

    if not message_id:
        return
    record = _store(user_data).get(action_id)
    if record and record.get("status") == "pending":
        record["preview_message_id"] = int(message_id)


def consume_pending_action(
    user_data: MutableMapping[str, Any],
    action_id: str,
    *,
    owner_user_id: int,
    message_id: int | None = None,
    expected_flow: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate and atomically transition one in-memory action to consumed.

    The synchronous compare-and-transition is sufficient for the project's
    approved single-process event-loop model. The payload remains stored after
    consumption so commit failures can be investigated without reading a newer
    mutable slot.
    """

    current = now or utc_now()
    store = _store(user_data)
    record = store.get(str(action_id or ""))
    if not record:
        raise PendingActionError("not_found", "Preview sudah kedaluwarsa atau hilang setelah restart.")
    if int(record.get("owner_user_id") or 0) != int(owner_user_id or 0):
        raise PendingActionError("wrong_owner", "Preview ini bukan milik pengguna tersebut.")

    expires_at = _parse_iso(record.get("expires_at"))
    if record.get("status") == "pending" and expires_at and current >= expires_at:
        record["status"] = "expired"
    if record.get("status") != "pending":
        raise PendingActionError(str(record.get("status") or "invalid"), "Preview sudah dipakai, dibatalkan, atau kedaluwarsa.")

    expected_message_id = record.get("preview_message_id")
    if expected_message_id and int(message_id or 0) != int(expected_message_id):
        raise PendingActionError("wrong_message", "Tombol tidak berasal dari pesan preview yang sesuai.")
    if expected_flow and str(record.get("flow_type")) != str(expected_flow):
        raise PendingActionError("wrong_flow", "Jenis preview tidak sesuai dengan callback.")

    record["status"] = "consumed"
    record["consumed_at"] = _iso(current)
    return copy.deepcopy(record)


def cancel_pending_action(
    user_data: MutableMapping[str, Any],
    action_id: str,
    *,
    owner_user_id: int,
    message_id: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Cancel one pending action without modifying its financial payload."""

    current = now or utc_now()
    store = _store(user_data)
    record = store.get(str(action_id or ""))
    if not record:
        raise PendingActionError("not_found", "Preview sudah kedaluwarsa atau hilang setelah restart.")
    if int(record.get("owner_user_id") or 0) != int(owner_user_id or 0):
        raise PendingActionError("wrong_owner", "Preview ini bukan milik pengguna tersebut.")
    expires_at = _parse_iso(record.get("expires_at"))
    if record.get("status") == "pending" and expires_at and current >= expires_at:
        record["status"] = "expired"
    if record.get("status") != "pending":
        raise PendingActionError(str(record.get("status") or "invalid"), "Preview sudah dipakai, dibatalkan, atau kedaluwarsa.")
    expected_message_id = record.get("preview_message_id")
    if expected_message_id and int(message_id or 0) != int(expected_message_id):
        raise PendingActionError("wrong_message", "Tombol tidak berasal dari pesan preview yang sesuai.")
    record["status"] = "canceled"
    return copy.deepcopy(record)


def snapshot_pending_state(user_data: MutableMapping[str, Any]) -> dict[str, Any]:
    """Copy mutable pending flow values while excluding the action store."""

    snapshot: dict[str, Any] = {}
    for key, value in user_data.items():
        if key == ACTION_STORE_KEY:
            continue
        if key.startswith("pending_") or key in {"mixed_review_preview_sent"}:
            snapshot[key] = copy.deepcopy(value)
    return snapshot


def restore_pending_state(user_data: MutableMapping[str, Any], snapshot: dict[str, Any]) -> None:
    """Replace mutable pending values with the exact confirmed snapshot."""

    for key in list(user_data):
        if key != ACTION_STORE_KEY and (key.startswith("pending_") or key == "mixed_review_preview_sent"):
            user_data.pop(key, None)
    for key, value in snapshot.items():
        user_data[key] = copy.deepcopy(value)


@contextmanager
def pending_action_request_context(
    user_data: MutableMapping[str, Any],
    owner_user_id: int,
    preview_message_id: int | None = None,
) -> Iterator[None]:
    """Bind request-local state so existing keyboard builders can snapshot it."""

    token = _request_context.set(ActionRequestContext(user_data, owner_user_id, preview_message_id))
    try:
        yield
    finally:
        _request_context.reset(token)


def create_bound_preview_action(flow_type: str, legacy_target: str) -> dict[str, Any] | None:
    """Create an action from the currently bound Telegram handler context."""

    bound = _request_context.get()
    if bound is None:
        return None
    return create_pending_action(
        bound.user_data,
        owner_user_id=bound.owner_user_id,
        flow_type=flow_type,
        payload={
            "legacy_target": legacy_target,
            "user_state": snapshot_pending_state(bound.user_data),
        },
        preview_message_id=bound.preview_message_id,
    )


def bind_current_action_message(reply_markup: Any, message_id: int | None) -> None:
    """Bind message IDs for action callbacks found in a sent keyboard."""

    bound = _request_context.get()
    if bound is None or not message_id or reply_markup is None:
        return
    keyboard = getattr(reply_markup, "inline_keyboard", None) or []
    for row in keyboard:
        for button in row:
            callback_data = str(getattr(button, "callback_data", "") or "")
            if callback_data.startswith("confirm:a_") or callback_data.startswith("cancel:a_"):
                action_id = callback_data.split(":", 1)[1]
                bind_action_message(bound.user_data, action_id, int(message_id))
