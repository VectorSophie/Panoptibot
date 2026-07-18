from __future__ import annotations

import discord


def create_embed(
    title: str,
    description: str | None = None,
    color: int = 0x5865F2,
    fields: list[tuple[str, str, bool]] | None = None,
) -> discord.Embed:
    """Create a Discord embed with consistent styling."""
    embed = discord.Embed(title=title, description=description, color=color)

    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

    return embed


# Color scheme for different types of embeds
class EmbedColor:
    INFO = 0x5865F2  # Blurple
    SUCCESS = 0x57F287  # Green
    WARNING = 0xFEE75C  # Yellow
    ERROR = 0xED4245  # Red
    GOLD = 0xFFD700  # Gold for #1
    SILVER = 0xC0C0C0  # Silver for #2
    BRONZE = 0xCD7F32  # Bronze for #3


def medal_for_rank(rank: int) -> str:
    """Return medal emoji for rank position."""
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
