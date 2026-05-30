from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
import json

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None

from panoptibot.bot.config import Settings
from panoptibot.ml.feature_engineering import (
    FeatureRow,
    calculate_rarity_score,
    normalize_time_of_day,
)


def _loads(line: bytes) -> dict[str, Any]:
    if orjson is not None:
        return orjson.loads(line)
    return json.loads(line.decode("utf-8"))


def _read_event_logs(events_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(events_dir.glob("*.jsonl")):
        with path.open("rb") as handle:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if raw_line:
                    records.append(_loads(raw_line))
    return records


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def bootstrap_rows() -> list[FeatureRow]:
    positives = [
        FeatureRow(
            group_id="bootstrap:1",
            label=1,
            features={
                "message_length": 60,
                "reaction_count": 4,
                "reply_count": 2,
                "emoji_count": 1,
                "sticker_present": 0,
                "attachment_present": 0,
                "interaction_frequency_between_users": 5,
                "prior_reply_count_between_users": 2,
                "prior_reaction_count_between_users": 3,
                "message_age_seconds": 180,
                "time_of_day": 0.5,
                "activity_spike_indicator": 1,
                "emoji_rarity_score": 0.2,
                "sticker_rarity_score": 0.0,
                "trending_emoji_score": 2.0,
            },
            metadata={"message_id": "positive-1", "user_id": "user-1"},
        ),
        FeatureRow(
            group_id="bootstrap:2",
            label=1,
            features={
                "message_length": 45,
                "reaction_count": 3,
                "reply_count": 1,
                "emoji_count": 2,
                "sticker_present": 0,
                "attachment_present": 1,
                "interaction_frequency_between_users": 4,
                "prior_reply_count_between_users": 1,
                "prior_reaction_count_between_users": 2,
                "message_age_seconds": 120,
                "time_of_day": 0.65,
                "activity_spike_indicator": 1,
                "emoji_rarity_score": 0.25,
                "sticker_rarity_score": 0.0,
                "trending_emoji_score": 1.5,
            },
            metadata={"message_id": "positive-2", "user_id": "user-2"},
        ),
    ]
    negatives = [
        FeatureRow(
            group_id="bootstrap:1",
            label=0,
            features={
                "message_length": 10,
                "reaction_count": 0,
                "reply_count": 0,
                "emoji_count": 0,
                "sticker_present": 0,
                "attachment_present": 0,
                "interaction_frequency_between_users": 0,
                "prior_reply_count_between_users": 0,
                "prior_reaction_count_between_users": 0,
                "message_age_seconds": 4000,
                "time_of_day": 0.1,
                "activity_spike_indicator": 0,
                "emoji_rarity_score": 0.0,
                "sticker_rarity_score": 0.0,
                "trending_emoji_score": 0.0,
            },
            metadata={"message_id": "negative-1", "user_id": "user-1"},
        ),
        FeatureRow(
            group_id="bootstrap:2",
            label=0,
            features={
                "message_length": 15,
                "reaction_count": 0,
                "reply_count": 0,
                "emoji_count": 0,
                "sticker_present": 0,
                "attachment_present": 0,
                "interaction_frequency_between_users": 0,
                "prior_reply_count_between_users": 0,
                "prior_reaction_count_between_users": 0,
                "message_age_seconds": 5000,
                "time_of_day": 0.2,
                "activity_spike_indicator": 0,
                "emoji_rarity_score": 0.0,
                "sticker_rarity_score": 0.0,
                "trending_emoji_score": 0.0,
            },
            metadata={"message_id": "negative-2", "user_id": "user-2"},
        ),
    ]
    return positives + negatives


def build_training_rows(settings: Settings) -> list[FeatureRow]:
    records = _read_event_logs(settings.logs_dir / "events")
    if not records:
        return bootstrap_rows()

    cutoff = datetime.now(UTC) - timedelta(days=settings.training_lookback_days)
    messages: dict[str, dict[str, Any]] = {}
    positives_by_user_session: dict[tuple[str, str], set[str]] = defaultdict(set)
    reactions_between_users: Counter[tuple[str, str]] = Counter()
    replies_between_users: Counter[tuple[str, str]] = Counter()
    interactions_between_users: Counter[tuple[str, str]] = Counter()
    emoji_usage: Counter[str] = Counter()
    sticker_usage: Counter[str] = Counter()
    message_reaction_counts: Counter[str] = Counter()
    message_reply_counts: Counter[str] = Counter()
    active_reactions: set[tuple[str, str]] = set()
    rows: list[FeatureRow] = []

    for record in sorted(records, key=lambda item: item.get("timestamp", "")):
        timestamp = _parse_timestamp(record["timestamp"])
        if timestamp < cutoff:
            continue
        event_name = str(record.get("event", ""))
        if event_name == "message_create":
            messages[str(record["message_id"])] = record
            for emoji in record.get("emoji_list", []):
                emoji_usage[str(emoji)] += 1
            for sticker in record.get("sticker_list", []):
                sticker_usage[str(sticker)] += 1
            reply_to = record.get("reply_to_message_id")
            if reply_to and str(reply_to) in messages:
                target = messages[str(reply_to)]
                pair = (str(record["user_id"]), str(target["user_id"]))
                replies_between_users[pair] += 1
                interactions_between_users[pair] += 1
                message_reply_counts[str(reply_to)] += 1
                positives_by_user_session[
                    (str(record["user_id"]), str(record.get("session_id") or "unknown"))
                ].add(str(reply_to))
            for mentioned_user_id in record.get("mention_ids", []):
                positives_by_user_session[
                    (str(mentioned_user_id), str(record.get("session_id") or "unknown"))
                ].add(str(record["message_id"]))
        elif event_name == "reaction_add":
            target = messages.get(str(record["message_id"]))
            if target is None:
                continue
            reaction_key = (str(record["user_id"]), str(record["message_id"]))
            if reaction_key in active_reactions:
                continue
            active_reactions.add(reaction_key)
            message_reaction_counts[str(record["message_id"])] += 1
            pair = (str(record["user_id"]), str(target["user_id"]))
            reactions_between_users[pair] += 1
            interactions_between_users[pair] += 1
            positives_by_user_session[
                (str(record["user_id"]), str(record.get("session_id") or "unknown"))
            ].add(str(record["message_id"]))
        elif event_name == "reaction_remove":
            reaction_key = (str(record["user_id"]), str(record["message_id"]))
            if reaction_key not in active_reactions:
                continue
            active_reactions.remove(reaction_key)
            message_reaction_counts[str(record["message_id"])] = max(
                message_reaction_counts[str(record["message_id"])] - 1,
                0,
            )

    ordered_messages = sorted(
        messages.values(), key=lambda item: item.get("timestamp", "")
    )
    total_emoji = sum(emoji_usage.values())
    total_stickers = sum(sticker_usage.values())

    for (
        user_id,
        session_id,
    ), positive_message_ids in positives_by_user_session.items():
        if not positive_message_ids:
            continue
        session_time = next(
            (
                _parse_timestamp(message["timestamp"])
                for message in ordered_messages
                if str(message.get("session_id") or "unknown") == session_id
            ),
            datetime.now(UTC),
        )
        positive_set = set(positive_message_ids)
        candidates = [
            message
            for message in ordered_messages
            if str(message["user_id"]) != user_id
            and str(message["message_id"]) not in positive_set
            and _parse_timestamp(message["timestamp"]) <= session_time
            and session_time - _parse_timestamp(message["timestamp"])
            <= timedelta(hours=24)
        ]

        sample_negatives = candidates[-max(3, len(positive_set)) :]
        for message_id in positive_set:
            message = messages.get(message_id)
            if message is None:
                continue
            rows.append(
                _build_row(
                    message,
                    user_id,
                    session_id,
                    1,
                    session_time,
                    interactions_between_users,
                    replies_between_users,
                    reactions_between_users,
                    message_reaction_counts,
                    message_reply_counts,
                    emoji_usage,
                    sticker_usage,
                    total_emoji,
                    total_stickers,
                    ordered_messages,
                )
            )
        for message in sample_negatives:
            rows.append(
                _build_row(
                    message,
                    user_id,
                    session_id,
                    0,
                    session_time,
                    interactions_between_users,
                    replies_between_users,
                    reactions_between_users,
                    message_reaction_counts,
                    message_reply_counts,
                    emoji_usage,
                    sticker_usage,
                    total_emoji,
                    total_stickers,
                    ordered_messages,
                )
            )

    return rows or bootstrap_rows()


def _build_row(
    message: dict[str, Any],
    user_id: str,
    session_id: str,
    label: int,
    session_time: datetime,
    interactions_between_users: Counter[tuple[str, str]],
    replies_between_users: Counter[tuple[str, str]],
    reactions_between_users: Counter[tuple[str, str]],
    message_reaction_counts: Counter[str],
    message_reply_counts: Counter[str],
    emoji_usage: Counter[str],
    sticker_usage: Counter[str],
    total_emoji: int,
    total_stickers: int,
    ordered_messages: list[dict[str, Any]],
) -> FeatureRow:
    created_at = _parse_timestamp(message["timestamp"])
    author_id = str(message["user_id"])
    pair = (user_id, author_id)
    recent_window_start = created_at - timedelta(minutes=10)
    recent_messages = [
        item
        for item in ordered_messages
        if recent_window_start <= _parse_timestamp(item["timestamp"]) <= created_at
    ]
    emoji_list = [str(emoji) for emoji in message.get("emoji_list", [])]
    sticker_list = [str(sticker) for sticker in message.get("sticker_list", [])]
    emoji_rarity = sum(
        calculate_rarity_score(emoji_usage[emoji], total_emoji) for emoji in emoji_list
    )
    sticker_rarity = sum(
        calculate_rarity_score(sticker_usage[sticker], total_stickers)
        for sticker in sticker_list
    )
    trending_emoji_score = float(sum(emoji_usage[emoji] for emoji in emoji_list))
    features = {
        "message_length": float(message.get("content_length", 0)),
        "reaction_count": float(message_reaction_counts[str(message["message_id"])]),
        "reply_count": float(message_reply_counts[str(message["message_id"])]),
        "emoji_count": float(len(emoji_list)),
        "sticker_present": float(bool(sticker_list)),
        "attachment_present": float(bool(message.get("attachment_present"))),
        "interaction_frequency_between_users": float(interactions_between_users[pair]),
        "prior_reply_count_between_users": float(replies_between_users[pair]),
        "prior_reaction_count_between_users": float(reactions_between_users[pair]),
        "message_age_seconds": max((session_time - created_at).total_seconds(), 0.0),
        "time_of_day": normalize_time_of_day(created_at),
        "activity_spike_indicator": float(len(recent_messages) >= 5),
        "emoji_rarity_score": round(emoji_rarity, 6),
        "sticker_rarity_score": round(sticker_rarity, 6),
        "trending_emoji_score": trending_emoji_score,
        "mentioned_viewer": float(user_id in [str(item) for item in message.get("mention_ids", [])]),
        "question_to_viewer": float("?" in str(message.get("content", ""))),
        "topic_burst_score": float(len(recent_messages) >= 5),
        "conversation_centrality": float(message_reply_counts[str(message["message_id"])]),
        "viewer_channel_affinity": float(interactions_between_users[pair]),
        "author_bridge_score": float(
            replies_between_users[pair] + reactions_between_users[pair]
        ),
    }
    return FeatureRow(
        group_id=session_id,
        label=label,
        features=features,
        metadata={
            "message_id": str(message["message_id"]),
            "candidate_user_id": user_id,
            "author_id": author_id,
            "channel_id": str(message.get("channel_id", "")),
        },
    )


def rows_as_dicts(rows: list[FeatureRow]) -> list[dict[str, Any]]:
    return [asdict(row) for row in rows]
