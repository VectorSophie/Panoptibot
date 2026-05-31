from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
import json

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None


def _phrase_counts_for_window(
    phrases_dir: Path, start: datetime, end: datetime
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in sorted(phrases_dir.glob("*.jsonl")):
        for raw_line in path.read_bytes().splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            record: dict[str, Any] = orjson.loads(raw_line) if orjson else json.loads(raw_line)
            try:
                ts = datetime.fromisoformat(record["timestamp"]).astimezone(UTC)
            except (KeyError, ValueError):
                continue
            if not (start <= ts < end):
                continue
            for term in record.get("terms", []):
                if "_" not in str(term):  # unigrams only for readability
                    counts[str(term)] += 1
    return counts


def trending_phrases(
    phrases_dir: Path,
    *,
    recent_days: int = 7,
    baseline_days: int = 30,
    min_recent_count: int = 3,
    limit: int = 5,
) -> list[tuple[str, float]]:
    now = datetime.now(UTC)
    recent_start = now - timedelta(days=recent_days)
    baseline_start = now - timedelta(days=baseline_days)
    baseline_span = baseline_days - recent_days

    recent = _phrase_counts_for_window(phrases_dir, recent_start, now)
    if not recent:
        return []

    baseline = _phrase_counts_for_window(phrases_dir, baseline_start, recent_start)

    results: list[tuple[str, float]] = []
    for term, recent_count in recent.items():
        if recent_count < min_recent_count:
            continue
        baseline_count = baseline.get(term, 0)
        recent_rate = recent_count / recent_days
        baseline_rate = max(baseline_count / max(baseline_span, 1), 0.1)
        trend_score = round(recent_rate / baseline_rate, 3)
        results.append((term, trend_score))

    results.sort(key=lambda item: item[1], reverse=True)
    return results[:limit]
