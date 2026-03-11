from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import log1p


FEATURE_NAMES = [
    "message_length",
    "reaction_count",
    "reply_count",
    "emoji_count",
    "sticker_present",
    "attachment_present",
    "interaction_frequency_between_users",
    "prior_reply_count_between_users",
    "prior_reaction_count_between_users",
    "message_age_seconds",
    "time_of_day",
    "activity_spike_indicator",
    "emoji_rarity_score",
    "sticker_rarity_score",
    "trending_emoji_score",
]


@dataclass(slots=True)
class FeatureRow:
    group_id: str
    label: int
    features: dict[str, float]
    metadata: dict[str, object]


def calculate_rarity_score(usage_count: int, total_count: int) -> float:
    if total_count <= 0 or usage_count <= 0:
        return 0.0
    return round(log1p(total_count / usage_count), 6)


def build_feature_vector(features: Mapping[str, float | int]) -> list[float]:
    return [float(features.get(name, 0.0)) for name in FEATURE_NAMES]


def normalize_time_of_day(timestamp: datetime) -> float:
    return round(
        (timestamp.hour * 3600 + timestamp.minute * 60 + timestamp.second) / 86400.0, 6
    )
