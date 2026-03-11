from __future__ import annotations


def summarize_emoji_distribution(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "No emoji usage recorded in the selected period."
    return "\n".join(f"{row['emoji']}: {row['usage_count']}" for row in rows)
