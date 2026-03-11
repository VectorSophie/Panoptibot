from __future__ import annotations

from datetime import UTC, datetime
import traceback

import discord

from panoptibot.bot.context import ServiceContainer


async def handle_member_join(
    member: discord.Member, services: ServiceContainer
) -> None:
    if member.bot:
        return
    timestamp = datetime.now(UTC).isoformat()
    services.logger.event(
        "member_join",
        {
            "timestamp": timestamp,
            "user_id": str(member.id),
            "channel_id": "",
            "message_id": "",
            "content_length": 0,
            "emoji_list": [],
            "sticker_list": [],
            "attachment_metadata": [],
        },
    )
    try:
        await services.graph.upsert_member_event(member.id, "member_join", timestamp)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "member_join_failed",
            {
                "timestamp": timestamp,
                "user_id": str(member.id),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )


async def handle_member_remove(
    member: discord.Member, services: ServiceContainer
) -> None:
    if member.bot:
        return
    timestamp = datetime.now(UTC).isoformat()
    services.logger.event(
        "member_leave",
        {
            "timestamp": timestamp,
            "user_id": str(member.id),
            "channel_id": "",
            "message_id": "",
            "content_length": 0,
            "emoji_list": [],
            "sticker_list": [],
            "attachment_metadata": [],
        },
    )
    ended = services.session_tracker.end(member.id)
    try:
        if ended is not None:
            await services.graph.upsert_session_state(
                user_id=member.id,
                session_id=ended.session_id,
                status="offline",
                started_at=ended.started_at.isoformat(),
                last_seen_at=ended.last_seen_at.isoformat(),
            )
        await services.graph.upsert_member_event(member.id, "member_leave", timestamp)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "member_leave_failed",
            {
                "timestamp": timestamp,
                "user_id": str(member.id),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )


async def handle_presence_update(
    before: discord.Member, after: discord.Member, services: ServiceContainer
) -> None:
    if after.bot:
        return
    status = str(after.status)
    now = datetime.now(UTC)
    session_id, is_new = services.session_tracker.touch(
        after.id, status=status, now=now
    )
    if is_new or str(before.status) != status:
        services.logger.event(
            "presence_update",
            {
                "timestamp": now.isoformat(),
                "user_id": str(after.id),
                "channel_id": "",
                "message_id": "",
                "content_length": 0,
                "emoji_list": [],
                "sticker_list": [],
                "attachment_metadata": [],
                "status": status,
                "session_id": session_id,
            },
        )
        try:
            await services.graph.upsert_session_state(
                user_id=after.id,
                session_id=session_id,
                status=status,
                started_at=now.isoformat(),
                last_seen_at=now.isoformat(),
            )
        except Exception as exc:  # pragma: no cover
            services.logger.error(
                "presence_update_failed",
                {
                    "timestamp": now.isoformat(),
                    "user_id": str(after.id),
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
