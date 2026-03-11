from __future__ import annotations

from datetime import UTC, datetime
import re

import discord


CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
UNICODE_EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def attachment_metadata(message: discord.Message) -> list[str]:
    return [
        f"{attachment.filename}|{attachment.size}|{attachment.content_type or ''}"
        for attachment in message.attachments
    ]


def extract_emojis(message: discord.Message) -> list[str]:
    content = message.content or ""
    return CUSTOM_EMOJI_PATTERN.findall(content) + UNICODE_EMOJI_PATTERN.findall(
        content
    )


def extract_stickers(message: discord.Message) -> list[str]:
    return [sticker.name for sticker in message.stickers]


def mention_ids(message: discord.Message) -> list[int]:
    return [member.id for member in message.mentions]


def build_message_record(
    message: discord.Message, session_id: str
) -> dict[str, object]:
    return {
        "timestamp": message.created_at.replace(tzinfo=UTC).isoformat(),
        "user_id": str(message.author.id),
        "channel_id": str(message.channel.id),
        "message_id": str(message.id),
        "content_length": len(message.content or ""),
        "emoji_list": extract_emojis(message),
        "sticker_list": extract_stickers(message),
        "attachment_metadata": attachment_metadata(message),
        "attachment_present": bool(message.attachments),
        "mention_ids": mention_ids(message),
        "reply_to_message_id": str(message.reference.message_id)
        if message.reference and message.reference.message_id
        else None,
        "session_id": session_id,
    }


def build_reaction_record(
    reaction: discord.Reaction, user: discord.abc.User, session_id: str
) -> dict[str, object]:
    return {
        "timestamp": iso_now(),
        "user_id": str(user.id),
        "channel_id": str(reaction.message.channel.id),
        "message_id": str(reaction.message.id),
        "emoji_list": [str(reaction.emoji)],
        "sticker_list": [],
        "attachment_metadata": [],
        "content_length": len(reaction.message.content or ""),
        "session_id": session_id,
    }
