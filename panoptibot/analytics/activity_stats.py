from __future__ import annotations


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        return int(value)
    return 0


def summarize_activity(
    stats: dict[str, object], top_users: list[dict[str, object]]
) -> str:
    total_messages = _as_int(stats.get("total_messages"))
    active_users = _as_int(stats.get("active_users"))
    total_content_length = _as_int(stats.get("total_content_length"))
    avg_length = (
        round(total_content_length / total_messages, 2) if total_messages else 0.0
    )
    leaders = (
        ", ".join(f"<@{row['user_id']}> ({row['message_count']})" for row in top_users)
        or "none"
    )
    return (
        f"Messages: {total_messages}\n"
        f"Active users: {active_users}\n"
        f"Average message length: {avg_length}\n"
        f"Top users: {leaders}"
    )
