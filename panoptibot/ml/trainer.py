from __future__ import annotations

from pathlib import Path

from catboost import CatBoostRanker, Pool

from panoptibot.bot.config import Settings
from panoptibot.ml.dataset_builder import build_training_rows
from panoptibot.ml.feature_engineering import FEATURE_NAMES, build_feature_vector


def train_and_save_model(settings: Settings) -> Path:
    rows = sorted(
        build_training_rows(settings),
        key=lambda row: (
            row.group_id,
            -row.label,
            str(row.metadata.get("message_id", "")),
        ),
    )
    features = [build_feature_vector(row.features) for row in rows]
    labels = [row.label for row in rows]
    group_ids = [row.group_id for row in rows]
    pool = Pool(
        data=features, label=labels, group_id=group_ids, feature_names=FEATURE_NAMES
    )
    model = CatBoostRanker(
        loss_function="YetiRank",
        iterations=80,
        learning_rate=0.08,
        depth=6,
        random_seed=42,
        verbose=False,
    )
    model.fit(pool)
    settings.model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(settings.model_path)
    return settings.model_path
