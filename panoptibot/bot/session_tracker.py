from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(slots=True)
class SessionState:
    session_id: str
    started_at: datetime
    last_seen_at: datetime
    status: str


class SessionTracker:
    def __init__(self, idle_seconds: int) -> None:
        self.idle_seconds = idle_seconds
        self._sessions: dict[int, SessionState] = {}

    def touch(
        self, user_id: int, status: str = "active", now: datetime | None = None
    ) -> tuple[str, bool]:
        current_time = now or datetime.now(UTC)
        existing = self._sessions.get(user_id)
        expired = existing is None or current_time - existing.last_seen_at > timedelta(
            seconds=self.idle_seconds
        )
        if expired:
            session_id = f"{user_id}:{int(current_time.timestamp())}"
            state = SessionState(
                session_id=session_id,
                started_at=current_time,
                last_seen_at=current_time,
                status=status,
            )
            self._sessions[user_id] = state
            return session_id, True
        assert existing is not None
        existing.last_seen_at = current_time
        existing.status = status
        return existing.session_id, False

    def end(self, user_id: int, now: datetime | None = None) -> SessionState | None:
        state = self._sessions.get(user_id)
        if state is None:
            return None
        state.last_seen_at = now or datetime.now(UTC)
        return self._sessions.pop(user_id, None)
