from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import logging

from catboost import CatBoostRanker, Pool

from panoptibot.bot.config import Settings
from panoptibot.ml.feature_engineering import (
    FEATURE_NAMES,
    build_feature_vector,
    calculate_rarity_score,
    normalize_time_of_day,
)


@dataclass(slots=True)
class RankedMessage:
    message_id: str
    channel_id: str
    author_id: str
    score: float
    created_at: str
    reaction_count: int
    reply_count: int


class MessageRecommender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: CatBoostRanker | None = None
        self._logger = logging.getLogger("panoptibot.recommender")
        self._load_model_if_present()

    def _load_model_if_present(self) -> None:
        model_path: Path = self.settings.model_path
        if model_path.exists() and model_path.stat().st_size > 0:
            try:
                model = CatBoostRanker()
                model.load_model(model_path)
                self._model = model
            except Exception as exc:  # pragma: no cover
                self._model = None
                self._logger.warning("Failed to load model %s: %s", model_path, exc)

    def reload(self) -> None:
        self._model = None
        self._load_model_if_present()

    def rank(
        self, user_id: int, candidates: list[dict[str, Any]]
    ) -> list[RankedMessage]:
        if not candidates:
            return []
        enriched_features = [
            self._candidate_features(user_id, candidate, candidates)
            for candidate in candidates
        ]
        if self._model is not None:
            pool = Pool(
                data=[build_feature_vector(item) for item in enriched_features],
                feature_names=FEATURE_NAMES,
            )
            scores = list(self._model.predict(pool))
        else:
            scores = [
                (item["reaction_count"] * 2.0)
                + (item["reply_count"] * 2.5)
                + (item["emoji_count"] * 0.4)
                + (item["interaction_frequency_between_users"] * 0.8)
                - (item["message_age_seconds"] / 3600.0)
                + (item["trending_emoji_score"] * 0.1)
                for item in enriched_features
            ]
        ranked = [
            RankedMessage(
                message_id=str(candidate["message_id"]),
                channel_id=str(candidate["channel_id"]),
                author_id=str(candidate["author_id"]),
                score=float(score),
                created_at=str(candidate["created_at"]),
                reaction_count=int(candidate.get("reaction_count", 0)),
                reply_count=int(candidate.get("reply_count", 0)),
            )
            for candidate, score in zip(candidates, scores, strict=True)
        ]
        return sorted(ranked, key=lambda item: item.score, reverse=True)

    def _candidate_features(
        self,
        user_id: int,
        candidate: dict[str, Any],
        all_candidates: list[dict[str, Any]],
    ) -> dict[str, float]:
        created_at = datetime.fromisoformat(
            str(candidate["created_at"]).replace("Z", "+00:00")
        ).astimezone(UTC)
        now = datetime.now(UTC)
        mentioned_user_ids = [str(item) for item in candidate.get("mention_ids", [])]
        total_mentions = max(
            sum(len(row.get("mention_ids", [])) for row in all_candidates), 1
        )
        mention_boost = 1.0 if str(user_id) in mentioned_user_ids else 0.0
        emoji_count = int(candidate.get("emoji_count", 0) or 0)
        interaction_frequency = float(
            candidate.get("interaction_frequency_between_users", 0.0) or 0.0
        )
        prior_reply_count = float(
            candidate.get("prior_reply_count_between_users", 0.0) or 0.0
        )
        prior_reaction_count = float(
            candidate.get("prior_reaction_count_between_users", 0.0) or 0.0
        )
        return {
            "message_length": float(candidate.get("message_length", 0)),
            "reaction_count": float(candidate.get("reaction_count", 0)),
            "reply_count": float(candidate.get("reply_count", 0)),
            "emoji_count": float(emoji_count),
            "sticker_present": float(bool(candidate.get("sticker_present"))),
            "attachment_present": float(bool(candidate.get("attachment_present"))),
            "interaction_frequency_between_users": interaction_frequency,
            "prior_reply_count_between_users": prior_reply_count,
            "prior_reaction_count_between_users": prior_reaction_count,
            "message_age_seconds": max((now - created_at).total_seconds(), 0.0),
            "time_of_day": normalize_time_of_day(created_at),
            "activity_spike_indicator": float(
                candidate.get("reaction_count", 0) >= 3
                or candidate.get("reply_count", 0) >= 2
            ),
            "emoji_rarity_score": calculate_rarity_score(
                max(emoji_count, 1),
                max(len(all_candidates), 1),
            ),
            "sticker_rarity_score": float(
                1.0 if candidate.get("sticker_present") else 0.0
            ),
            "trending_emoji_score": float(emoji_count + mention_boost) / total_mentions,
        }
