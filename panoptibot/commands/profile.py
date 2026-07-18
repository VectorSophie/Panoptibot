from __future__ import annotations

import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.embeds import create_embed, EmbedColor
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

        # Format profile as embed
        display_name = resolve_user_name(user_id, guild)
        embed = create_embed(
            title=f"Profile: {display_name}",
            description=f"Activity summary for the last {days} days",
            color=EmbedColor.INFO,
        )

        # Activity stats
        embed.add_field(
            name="📊 Activity",
            value=f"Messages: **{stats['total_messages']}**\nAvg length: **{stats['avg_content_length']:.0f}** chars",
            inline=False,
        )

        # Top channels
        if stats['top_channels']:
            channel_lines = [
                f"{resolve_channel_name(ch['channel_id'], guild)}: {ch['count']}"
                for ch in stats['top_channels'][:5]
            ]
            embed.add_field(
                name="📍 Most Active Channels",
                value="\n".join(channel_lines) or "None",
                inline=False,
            )

        # Top emojis
        if stats['top_emojis']:
            emoji_display = " ".join(
                f"{e['emoji']}×{e['count']}" for e in stats['top_emojis'][:10]
            )
            embed.add_field(name="😀 Top Emojis", value=emoji_display or "None", inline=False)

        # Interaction partners
        if stats['top_interactions']:
            partner_lines = [
                f"{resolve_user_name(p['partner_id'], guild)}: {p['weight']}"
                for p in stats['top_interactions'][:5]
            ]
            embed.add_field(
                name="👥 Top Interactions",
                value="\n".join(partner_lines) or "None",
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)
