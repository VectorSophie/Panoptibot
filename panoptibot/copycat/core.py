from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CopycatProfile:
    user_id: str
    display_name: str
    catchphrases: tuple[str, ...] = ()
    tone_notes: tuple[str, ...] = ()
    spelling_quirks: tuple[str, ...] = ()
    hard_facts: tuple[str, ...] = ()
    never_say: tuple[str, ...] = ()
    refusal_mode: str = "mostly_open"
    history_enabled: bool = False
    history_retention_days: int = 30


@dataclass(frozen=True, slots=True)
class CopycatSession:
    owner_user_id: str
    display_name: str
    expires_at: datetime
    allowlisted_channel_ids: frozenset[str] = field(default_factory=frozenset)
    active: bool = True
    status_note: str = ""


BLOCKED_TEXT_MARKERS = (
    "password",
    "token",
    "secret",
    "private address",
    "credential",
    "kill yourself",
    "self harm",
)


def should_trigger_copycat(
    *,
    session: CopycatSession,
    mentioned_user_ids: set[str],
    channel_id: str,
    now: datetime,
) -> bool:
    return (
        session.active
        and now < session.expires_at
        and session.owner_user_id in mentioned_user_ids
        and channel_id in session.allowlisted_channel_ids
    )


def build_labeled_reply(profile: CopycatProfile, generated_text: str) -> str:
    text = generated_text.strip().strip('"')
    return f'@{profile.display_name} is away, but he would say: "{text}"'


def is_allowed_copycat_text(text: str, never_say: tuple[str, ...] = ()) -> bool:
    normalized = text.lower()
    blocked = BLOCKED_TEXT_MARKERS + tuple(item.lower() for item in never_say)
    return not any(marker in normalized for marker in blocked)
