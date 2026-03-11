from __future__ import annotations

import discord

from panoptibot.bot.config import Settings
from panoptibot.bot.rate_limit import SlidingWindowRateLimiter


async def enforce_command_access(
    interaction: discord.Interaction,
    settings: Settings,
    limiter: SlidingWindowRateLimiter,
) -> bool:
    if interaction.user is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "This command must be used inside a server.", ephemeral=True
        )
        return False
    if interaction.user.bot:
        await interaction.response.send_message(
            "Bots cannot invoke Panoptibot commands.", ephemeral=True
        )
        return False
    if interaction.channel_id != settings.admin_channel_id:
        await interaction.response.send_message(
            "Use this command in the configured admin channel.", ephemeral=True
        )
        return False
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Administrator permission is required.", ephemeral=True
        )
        return False
    key = f"{interaction.user.id}:{interaction.command.name if interaction.command else 'command'}"
    if not limiter.allow(key):
        await interaction.response.send_message(
            "Rate limit exceeded. Please wait and try again.", ephemeral=True
        )
        return False
    return True
