from __future__ import annotations

import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_user_command_access
from panoptibot.catchup.social import SocialFact, render_catchup_bullets
from panoptibot.commands.summary import _format_message_reference


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    group = app_commands.Group(name="catchup", description="Catch up on missed context.")

    @group.command(name="me", description="Show social bullet points from recent activity.")
    @app_commands.describe(days="Number of days to look back (default: 1)")
    async def catchup_me(interaction: discord.Interaction, days: int = 1) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        # Validate days parameter
        if days < 1 or days > 30:
            await interaction.followup.send(
                "Days must be between 1 and 30.", ephemeral=True
            )
            return
        candidates = await services.graph.fetch_summary_candidates(
            user_id=interaction.user.id,
            lookback_hours=days * 24,
            limit=20,
        )
        ranked = services.recommender.rank(interaction.user.id, candidates)[:6]

        # Resolve user IDs to display names and channel IDs to channel names
        guild = interaction.guild
        facts = []
        for item in ranked:
            # Try to get the actual Discord user's display name
            author_name = f"@{item.author_id}"
            if guild:
                try:
                    member = await guild.fetch_member(int(item.author_id))
                    author_name = f"@{member.display_name}"
                except (discord.NotFound, discord.HTTPException, ValueError):
                    pass

            # Try to get the actual channel name
            channel_name = f"#{item.channel_id}"
            if guild:
                try:
                    channel = guild.get_channel(int(item.channel_id))
                    if channel and hasattr(channel, 'name'):
                        channel_name = f"#{channel.name}"
                except (ValueError, AttributeError):
                    pass

            facts.append(SocialFact(
                subject_names=(author_name,),
                related_names=(),
                action="said_something",
                evidence_urls=(
                    _format_message_reference(
                        interaction.guild_id, item.channel_id, item.message_id
                    ),
                ),
                confidence=0.8,
                channel_name=channel_name,
            ))

        if not facts:
            await interaction.followup.send(
                "No recent catch-up bullets were found.", ephemeral=True
            )
            return
        display_name = getattr(interaction.user, "display_name", str(interaction.user.id))
        await interaction.followup.send(
            "\n".join(render_catchup_bullets(facts, viewer_name=display_name)),
            ephemeral=True,
        )

    tree.add_command(group)
