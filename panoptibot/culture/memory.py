from __future__ import annotations

from collections import Counter
from typing import Any


def bridge_users(rows: list[dict[str, Any]], limit: int) -> list[tuple[str, float]]:
    scores: Counter[str] = Counter()
    for row in rows:
        weight = float(row.get("weight", 0.0) or 0.0)
        scores[str(row.get("source_user", ""))] += weight
        scores[str(row.get("target_user", ""))] += weight
    return [
        (user_id, float(score))
        for user_id, score in scores.most_common(limit)
        if user_id
    ]


def culture_memory_lines(
    *,
    emoji_rows: list[dict[str, Any]],
    bridge_rows: list[tuple[str, float]],
) -> list[str]:
    lines = ["Culture memory, recent activity"]
    if emoji_rows:
        top_emoji = emoji_rows[0]
        lines.append(
            f"- Emoji showing up most: {top_emoji.get('emoji')} ({top_emoji.get('usage_count')} uses)"
        )
    if bridge_rows:
        user_id, _score = bridge_rows[0]
        lines.append(f"- Bridge user candidate: <@{user_id}> connects active conversations")
    if len(lines) == 1:
        lines.append("- No strong culture-memory patterns found yet")
    return lines
