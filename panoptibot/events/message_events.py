from __future__ import annotations

from datetime import UTC, datetime
import asyncio
import traceback

import discord

from panoptibot.bot.context import ServiceContainer
from panoptibot.copycat.runtime import (
    format_copycat_response,
    generate_copycat_text,
)
from panoptibot.graph.graph_builder import build_message_record


async def handle_message_create(
    message: discord.Message, services: ServiceContainer
) -> None:
    if message.author.bot or message.guild is None:
        return
    now = datetime.now(UTC)
    try:
        session_id, is_new = services.session_tracker.touch(message.author.id, now=now)
        if is_new:
            await services.graph.upsert_session_state(
                user_id=message.author.id,
                session_id=session_id,
                status="active",
                started_at=now.isoformat(),
                last_seen_at=now.isoformat(),
            )
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "session_create_failed",
            {
                "timestamp": now.isoformat(),
                "user_id": str(message.author.id),
                "message_id": str(message.id),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        session_id = f"{message.author.id}:{int(now.timestamp())}"
    payload = build_message_record(message, session_id)
    services.logger.event("message_create", payload)
    services.copycat_store.record_history_message(
        user_id=str(message.author.id),
        channel_id=str(message.channel.id),
        message_id=str(message.id),
        content=message.content or "",
        timestamp=now,
    )
    try:
        await services.graph.upsert_message(payload)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "message_create_failed",
            {
                "timestamp": now.isoformat(),
                "message_id": str(message.id),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
    await _maybe_send_copycat_reply(message, services, now)


async def _maybe_send_copycat_reply(
    message: discord.Message, services: ServiceContainer, now: datetime
) -> None:
    mentioned_user_ids = {str(member.id) for member in message.mentions}
    session = services.copycat_store.find_active_session_for_mentions(
        mentioned_user_ids=mentioned_user_ids,
        channel_id=str(message.channel.id),
        now=now,
    )
    if session is None:
        return
    profile = services.copycat_store.load_profile(
        session.owner_user_id, session.display_name
    )
    examples = services.copycat_store.recent_examples(session.owner_user_id, limit=6)
    generated_text, decision, prompt = await asyncio.to_thread(
        generate_copycat_text,
        settings=services.settings,
        profile=profile,
        session=session,
        incoming_text=message.content or "",
        style_examples=examples,
    )
    response = format_copycat_response(profile, generated_text, decision)
    try:
        reply = await message.reply(response, mention_author=False)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "copycat_reply_failed",
            {
                "timestamp": now.isoformat(),
                "owner_user_id": session.owner_user_id,
                "trigger_message_id": str(message.id),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        return
    services.copycat_store.audit_reply(
        owner_user_id=session.owner_user_id,
        trigger_user_id=str(message.author.id),
        channel_id=str(message.channel.id),
        trigger_message_id=str(message.id),
        reply_message_id=str(reply.id),
        model_name=services.settings.lm_studio_model,
        decision=decision,
        prompt=prompt,
        response=response,
        timestamp=now,
    )


async def handle_message_edit(
    before: discord.Message, after: discord.Message, services: ServiceContainer
) -> None:
    if after.author.bot or after.guild is None:
        return
    session_id, _ = services.session_tracker.touch(after.author.id)
    payload = build_message_record(after, session_id)
    payload["edited_timestamp"] = datetime.now(UTC).isoformat()
    services.logger.event("message_edit", payload)
    try:
        await services.graph.upsert_message(payload)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "message_edit_failed",
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "message_id": str(after.id),
                "error": str(exc),
            },
        )


async def handle_message_delete(
    message: discord.Message, services: ServiceContainer
) -> None:
    if message.guild is None or (message.author is not None and message.author.bot):
        return
    timestamp = datetime.now(UTC).isoformat()
    services.logger.event(
        "message_delete",
        {
            "timestamp": timestamp,
            "user_id": str(message.author.id) if message.author is not None else "",
            "channel_id": str(message.channel.id),
            "message_id": str(message.id),
            "content_length": len(message.content or ""),
            "emoji_list": [],
            "sticker_list": [],
            "attachment_metadata": [],
        },
    )
    try:
        await services.graph.mark_message_deleted(message.id, timestamp)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "message_delete_failed",
            {
                "timestamp": timestamp,
                "message_id": str(message.id),
                "error": str(exc),
            },
        )


async def handle_raw_message_delete(
    payload: discord.RawMessageDeleteEvent, services: ServiceContainer
) -> None:
    if payload.guild_id is None:
        return
    timestamp = datetime.now(UTC).isoformat()
    services.logger.event(
        "message_delete",
        {
            "timestamp": timestamp,
            "user_id": "",
            "channel_id": str(payload.channel_id),
            "message_id": str(payload.message_id),
            "content_length": 0,
            "emoji_list": [],
            "sticker_list": [],
            "attachment_metadata": [],
        },
    )
    try:
        await services.graph.mark_message_deleted(payload.message_id, timestamp)
    except Exception as exc:  # pragma: no cover
        services.logger.error(
            "raw_message_delete_failed",
            {
                "timestamp": timestamp,
                "message_id": str(payload.message_id),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
