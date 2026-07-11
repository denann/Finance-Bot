"""Minimal Telegram objects for callback and handler tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


@dataclass
class FakeMessage:
    """Capture replies without contacting Telegram."""

    text: str = ""
    message_id: int = 1
    replies: list[dict[str, Any]] = field(default_factory=list)

    async def reply_text(self, text: str, **kwargs: Any) -> "FakeMessage":
        """Record a text response in memory."""

        self.replies.append({"text": text, **kwargs})
        return self


@dataclass
class FakeCallbackQuery:
    """Capture callback edits and answers in memory."""

    data: str
    message: FakeMessage = field(default_factory=FakeMessage)
    from_user_id: int = 1
    edits: list[dict[str, Any]] = field(default_factory=list)
    answers: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.from_user = SimpleNamespace(id=self.from_user_id)

    async def answer(self, text: str | None = None, **kwargs: Any) -> None:
        """Record a callback answer."""

        self.answers.append({"text": text, **kwargs})

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        """Record an edited callback message."""

        self.edits.append({"text": text, **kwargs})


@dataclass
class FakeUpdate:
    """Provide the small Update surface used by local tests."""

    message: FakeMessage | None = None
    callback_query: FakeCallbackQuery | None = None
    user_id: int = 1

    @property
    def effective_user(self) -> Any:
        """Return a Telegram-like user object."""

        return SimpleNamespace(id=self.user_id)


@dataclass
class FakeContext:
    """Store Telegram context dictionaries without PTB runtime state."""

    user_data: dict[str, Any] = field(default_factory=dict)
    bot_data: dict[str, Any] = field(default_factory=dict)
    args: list[str] = field(default_factory=list)
