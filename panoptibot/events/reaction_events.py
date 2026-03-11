from __future__ import annotations

from datetime import UTC, datetime
import traceback

import discord

from panoptibot.bot.context import ServiceContainer
from panoptibot.graph.graph_builder import build_reaction_record


async def handle_reaction_add(
    reaction: discord.Reaction, user: discord.abc.User, services: ServiceContainer
) -> None:
    if user.bot:
        return
    session_id, is_new = services.session_tracker.touch(user.id, now=datetime.now(UTC))
    try:
        if is_new:
            now = datetime.now(UTC).isoformat()
            await services.graph.upsert_session_state(
                user.id, session_id, "active", now, now
            )
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "reaction_session_update_failed",
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "user_id": str(user.id),
                "message_id": str(reaction.message.id),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
    payload = build_reaction_record(reaction, user, session_id)
    services.logger.event("reaction_add", payload)
    try:
        await services.graph.upsert_reaction(payload, removed=False)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "reaction_add_failed",
            {
                "timestamp": payload["timestamp"],
                "user_id": payload["user_id"],
                "message_id": payload["message_id"],
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )


async def handle_reaction_remove(
    reaction: discord.Reaction, user: discord.abc.User, services: ServiceContainer
) -> None:
    if user.bot:
        return
    session_id, _ = services.session_tracker.touch(user.id, now=datetime.now(UTC))
    payload = build_reaction_record(reaction, user, session_id)
    services.logger.event("reaction_remove", payload)
    try:
        await services.graph.upsert_reaction(payload, removed=True)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "reaction_remove_failed",
            {
                "timestamp": payload["timestamp"],
                "user_id": payload["user_id"],
                "message_id": payload["message_id"],
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
