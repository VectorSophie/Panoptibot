from __future__ import annotations

import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.resolver import resolve_channel_name, resolve_user_name
from panoptibot.bot.security import enforce_user_command_access


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(name="profile", description="Show user statistics and activity.")
    @app_commands.describe(
        user="User to view profile for (default: yourself)",
        days="Number of days to analyze (default: 30)",
    )
    async def profile(
        interaction: discord.Interaction,
        user: discord.User | None = None,
        days: int = 30,
    ) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        if days < 1 or days > 90:
            await interaction.followup.send(
                "Days must be between 1 and 90.", ephemeral=True
            )
            return

        target_user = user or interaction.user
        user_id = str(target_user.id)
        guild = interaction.guild

        # Fetch user stats from graph
        stats = await services.graph.fetch_user_profile_stats(user_id, days)

        if not stats:
            await interaction.followup.send(
                f"No activity data found for {resolve_user_name(user_id, guild)} in the last {days} days.",
                ephemeral=True,
            )
            return

        # Format profile
        display_name = resolve_user_name(user_id, guild)
        lines = [
            f"**Profile for {display_name}** (last {days} days)\n",
            f"📊 **Activity**",
            f"  Messages sent: {stats['total_messages']}",
            f"  Avg content length: {stats['avg_content_length']:.0f} chars",
        ]

        # Top channels
        if stats['top_channels']:
            lines.append(f"\n📍 **Most Active Channels**")
            for ch in stats['top_channels'][:5]:
                channel_name = resolve_channel_name(ch['channel_id'], guild)
                lines.append(f"  {channel_name}: {ch['count']} messages")

        # Top emojis
        if stats['top_emojis']:
            lines.append(f"\n😀 **Top Emojis**")
            emoji_line = "  " + " ".join(
                f"{e['emoji']}×{e['count']}" for e in stats['top_emojis'][:10]
            )
            lines.append(emoji_line)

        # Interaction partners
        if stats['top_interactions']:
            lines.append(f"\n👥 **Most Interactions With**")
            for partner in stats['top_interactions'][:5]:
                partner_name = resolve_user_name(partner['partner_id'], guild)
                lines.append(f"  {partner_name}: {partner['weight']} interactions")

        await interaction.followup.send("\n".join(lines), ephemeral=True)
