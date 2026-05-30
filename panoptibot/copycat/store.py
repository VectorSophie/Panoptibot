from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
import json
import hashlib

from panoptibot.copycat.core import CopycatProfile, CopycatSession, should_trigger_copycat


class CopycatStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.profiles_dir = base_dir / "profiles"
        self.history_dir = base_dir / "history"
        self.sessions_dir = base_dir / "sessions"
        self.audit_dir = base_dir / "audit"
        for directory in (
            self.profiles_dir,
            self.history_dir,
            self.sessions_dir,
            self.audit_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def profile_path(self, user_id: str) -> Path:
        return self.profiles_dir / f"{user_id}.json"

    def session_path(self, user_id: str) -> Path:
        return self.sessions_dir / f"{user_id}.json"

    def load_profile(self, user_id: str, display_name: str | None = None) -> CopycatProfile:
        path = self.profile_path(user_id)
        if not path.exists():
            return CopycatProfile(user_id=user_id, display_name=display_name or user_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return CopycatProfile(
            user_id=str(data["user_id"]),
            display_name=str(data.get("display_name") or display_name or user_id),
            catchphrases=tuple(data.get("catchphrases", [])),
            tone_notes=tuple(data.get("tone_notes", [])),
            spelling_quirks=tuple(data.get("spelling_quirks", [])),
            hard_facts=tuple(data.get("hard_facts", [])),
            never_say=tuple(data.get("never_say", [])),
            refusal_mode=str(data.get("refusal_mode", "mostly_open")),
            history_enabled=bool(data.get("history_enabled", False)),
            history_retention_days=int(data.get("history_retention_days", 30)),
        )

    def save_profile(self, profile: CopycatProfile) -> None:
        self.profile_path(profile.user_id).write_text(
            json.dumps(asdict(profile), ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def update_profile(
        self,
        user_id: str,
        *,
        display_name: str,
        history_enabled: bool | None = None,
        history_retention_days: int | None = None,
    ) -> CopycatProfile:
        profile = self.load_profile(user_id, display_name)
        updated = CopycatProfile(
            user_id=user_id,
            display_name=display_name,
            catchphrases=profile.catchphrases,
            tone_notes=profile.tone_notes,
            spelling_quirks=profile.spelling_quirks,
            hard_facts=profile.hard_facts,
            never_say=profile.never_say,
            refusal_mode=profile.refusal_mode,
            history_enabled=profile.history_enabled
            if history_enabled is None
            else history_enabled,
            history_retention_days=profile.history_retention_days
            if history_retention_days is None
            else history_retention_days,
        )
        self.save_profile(updated)
        return updated

    def add_channel(self, user_id: str, channel_id: str) -> CopycatSession | None:
        session = self.load_session(user_id)
        if session is None:
            return None
        updated = CopycatSession(
            owner_user_id=session.owner_user_id,
            display_name=session.display_name,
            expires_at=session.expires_at,
            allowlisted_channel_ids=session.allowlisted_channel_ids | frozenset({channel_id}),
            active=session.active,
            status_note=session.status_note,
        )
        self.save_session(updated)
        return updated

    def enable_session(
        self,
        *,
        owner_user_id: str,
        display_name: str,
        duration_minutes: int,
        now: datetime | None = None,
        status_note: str = "",
    ) -> CopycatSession:
        current = self.load_session(owner_user_id)
        now = now or datetime.now(UTC)
        session = CopycatSession(
            owner_user_id=owner_user_id,
            display_name=display_name,
            expires_at=now + timedelta(minutes=duration_minutes),
            allowlisted_channel_ids=current.allowlisted_channel_ids
            if current is not None
            else frozenset(),
            active=True,
            status_note=status_note,
        )
        self.save_session(session)
        self.update_profile(owner_user_id, display_name=display_name)
        return session

    def disable_session(self, user_id: str) -> None:
        session = self.load_session(user_id)
        if session is None:
            return
        self.save_session(
            CopycatSession(
                owner_user_id=session.owner_user_id,
                display_name=session.display_name,
                expires_at=session.expires_at,
                allowlisted_channel_ids=session.allowlisted_channel_ids,
                active=False,
                status_note=session.status_note,
            )
        )

    def load_session(self, user_id: str) -> CopycatSession | None:
        path = self.session_path(user_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return _session_from_dict(data)

    def save_session(self, session: CopycatSession) -> None:
        data = {
            "owner_user_id": session.owner_user_id,
            "display_name": session.display_name,
            "expires_at": session.expires_at.isoformat(),
            "allowlisted_channel_ids": sorted(session.allowlisted_channel_ids),
            "active": session.active,
            "status_note": session.status_note,
        }
        self.session_path(session.owner_user_id).write_text(
            json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def find_active_session_for_mentions(
        self,
        *,
        mentioned_user_ids: set[str],
        channel_id: str,
        now: datetime | None = None,
    ) -> CopycatSession | None:
        now = now or datetime.now(UTC)
        for path in self.sessions_dir.glob("*.json"):
            session = _session_from_dict(json.loads(path.read_text(encoding="utf-8")))
            if should_trigger_copycat(
                session=session,
                mentioned_user_ids=mentioned_user_ids,
                channel_id=channel_id,
                now=now,
            ):
                return session
        return None

    def record_history_message(
        self,
        *,
        user_id: str,
        channel_id: str,
        message_id: str,
        content: str,
        timestamp: datetime,
    ) -> bool:
        profile = self.load_profile(user_id)
        if not profile.history_enabled or not content.strip():
            return False
        record = {
            "timestamp": timestamp.astimezone(UTC).isoformat(),
            "user_id": user_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "content": content,
        }
        with (self.history_dir / f"{user_id}.jsonl").open("ab") as handle:
            handle.write(json.dumps(record, ensure_ascii=True).encode("utf-8") + b"\n")
        return True

    def recent_examples(self, user_id: str, limit: int) -> list[str]:
        path = self.history_dir / f"{user_id}.jsonl"
        if not path.exists():
            return []
        examples: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                examples.append(str(data.get("content", "")))
        return [item for item in examples if item][-limit:]

    def cleanup_history(self, *, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        removed = 0
        for path in self.history_dir.glob("*.jsonl"):
            user_id = path.stem
            profile = self.load_profile(user_id)
            cutoff = now - timedelta(days=profile.history_retention_days)
            kept: list[dict[str, Any]] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                timestamp = datetime.fromisoformat(record["timestamp"]).astimezone(UTC)
                if timestamp >= cutoff:
                    kept.append(record)
                else:
                    removed += 1
            with path.open("wb") as handle:
                for record in kept:
                    handle.write(json.dumps(record, ensure_ascii=True).encode("utf-8") + b"\n")
        return removed

    def audit_reply(
        self,
        *,
        owner_user_id: str,
        trigger_user_id: str,
        channel_id: str,
        trigger_message_id: str,
        reply_message_id: str,
        model_name: str,
        decision: str,
        prompt: str,
        response: str,
        timestamp: datetime | None = None,
    ) -> None:
        timestamp = timestamp or datetime.now(UTC)
        record = {
            "timestamp": timestamp.isoformat(),
            "event": "copycat_reply",
            "owner_user_id": owner_user_id,
            "trigger_user_id": trigger_user_id,
            "channel_id": channel_id,
            "trigger_message_id": trigger_message_id,
            "reply_message_id": reply_message_id,
            "model_name": model_name,
            "decision": decision,
            "prompt_hash": "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "response_hash": "sha256:" + hashlib.sha256(response.encode("utf-8")).hexdigest(),
        }
        day_stamp = timestamp.strftime("%Y-%m-%d")
        with (self.audit_dir / f"{day_stamp}.jsonl").open("ab") as handle:
            handle.write(json.dumps(record, ensure_ascii=True).encode("utf-8") + b"\n")


def _session_from_dict(data: dict[str, Any]) -> CopycatSession:
    return CopycatSession(
        owner_user_id=str(data["owner_user_id"]),
        display_name=str(data["display_name"]),
        expires_at=datetime.fromisoformat(str(data["expires_at"])).astimezone(UTC),
        allowlisted_channel_ids=frozenset(str(item) for item in data.get("allowlisted_channel_ids", [])),
        active=bool(data.get("active", True)),
        status_note=str(data.get("status_note", "")),
    )
