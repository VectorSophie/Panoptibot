from __future__ import annotations

import re


CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:(\w+):(\d+)>")


def format_emoji_label(emoji_value: object) -> str:
    value = str(emoji_value or "")
    match = CUSTOM_EMOJI_PATTERN.fullmatch(value)
    if match is None:
        return value
    return f":{match.group(1)}:"


def summarize_emoji_distribution(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "No emoji usage recorded in the selected period."
    return "\n".join(
        f"{format_emoji_label(row.get('emoji'))}: {row.get('usage_count')}"
        for row in rows
    )
