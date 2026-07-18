from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from discord import Guild


@lru_cache(maxsize=512)
def resolve_user_name(user_id: str, guild: Guild | None) -> str:
    """Resolve Discord user ID to display name. Returns @ID if resolution fails."""
    if not guild:
        return f"@{user_id}"

    try:
        # Try from cache first
        member = guild.get_member(int(user_id))
        if member:
            return f"@{member.display_name}"
    except (ValueError, AttributeError):
        pass

    return f"@{user_id}"


async def resolve_user_name_async(user_id: str, guild: Guild | None) -> str:
    """Async version - fetches from API if not cached."""
    if not guild:
        return f"@{user_id}"

    try:
        # Try cache first
        member = guild.get_member(int(user_id))
        if member:
            return f"@{member.display_name}"

        # Fetch from API if not cached
        member = await guild.fetch_member(int(user_id))
        return f"@{member.display_name}"
    except (discord.NotFound, discord.HTTPException, ValueError, AttributeError):
        return f"@{user_id}"


@lru_cache(maxsize=256)
def resolve_channel_name(channel_id: str, guild: Guild | None) -> str:
    """Resolve Discord channel ID to name. Returns #ID if resolution fails."""
    if not guild:
        return f"#{channel_id}"

    try:
        channel = guild.get_channel(int(channel_id))
        if channel and hasattr(channel, 'name'):
            return f"#{channel.name}"
    except (ValueError, AttributeError):
        pass

    return f"#{channel_id}"


def clear_resolver_cache() -> None:
    """Clear cached resolutions - call when guild state changes significantly."""
    resolve_user_name.cache_clear()
    resolve_channel_name.cache_clear()
