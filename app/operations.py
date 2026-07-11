"""Runtime readiness state and explicit single-instance scheduler policy."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any


def validate_instance_policy(instance_count: int, scheduler_enabled: bool) -> None:
    """Reject multi-instance scheduler deployment without distributed ownership."""

    count = int(instance_count or 0)
    if count < 1:
        raise ValueError("APP_INSTANCE_COUNT harus minimal 1.")
    if scheduler_enabled and count != 1:
        raise RuntimeError(
            "Scheduler Finance Bot hanya mendukung satu instance. "
            "Set APP_INSTANCE_COUNT=1 atau SCHEDULER_ENABLED=false."
        )


@dataclass
class RuntimeReadiness:
    """Track generic dependency readiness without retaining exception details."""

    mode: str
    scheduler_enabled: bool = True
    startup_complete: bool = False
    config_ready: bool = False
    sheets_ready: bool = False
    telegram_ready: bool = False
    scheduler_ready: bool = False

    def snapshot(self) -> dict[str, Any]:
        """Return a public, generic readiness payload."""

        scheduler_ok = self.scheduler_ready if self.scheduler_enabled else True
        ready = all(
            (
                self.startup_complete,
                self.config_ready,
                self.sheets_ready,
                self.telegram_ready,
                scheduler_ok,
            )
        )
        return {
            "status": "ready" if ready else "not_ready",
            "mode": self.mode,
            "components": {
                "config": "ready" if self.config_ready else "not_ready",
                "sheets": "ready" if self.sheets_ready else "not_ready",
                "telegram": "ready" if self.telegram_ready else "not_ready",
                "scheduler": (
                    "disabled"
                    if not self.scheduler_enabled
                    else "ready" if self.scheduler_ready else "not_ready"
                ),
            },
        }


class RuntimeStateStore:
    """Synchronize readiness updates made by startup and shutdown paths."""

    def __init__(self, mode: str, scheduler_enabled: bool = True):
        self._lock = Lock()
        self._state = RuntimeReadiness(mode=mode, scheduler_enabled=scheduler_enabled)

    def update(self, **fields: bool) -> dict[str, Any]:
        """Update known boolean fields and return the new public snapshot."""

        with self._lock:
            for key, value in fields.items():
                if not hasattr(self._state, key):
                    raise KeyError(f"Unknown readiness field: {key}")
                setattr(self._state, key, bool(value))
            return self._state.snapshot()

    def snapshot(self) -> dict[str, Any]:
        """Return the current public readiness state."""

        with self._lock:
            return self._state.snapshot()
