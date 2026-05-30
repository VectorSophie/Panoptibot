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
    async def catchup_me(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        candidates = await services.graph.fetch_summary_candidates(
            user_id=interaction.user.id,
            lookback_hours=services.settings.summary_lookback_hours,
            limit=20,
        )
        ranked = services.recommender.rank(interaction.user.id, candidates)[:6]
        facts = [
            SocialFact(
                subject_names=(f"@{item.author_id}",),
                related_names=(),
                action="said_something",
                evidence_urls=(
                    _format_message_reference(
                        interaction.guild_id, item.channel_id, item.message_id
                    ),
                ),
                confidence=0.8,
                channel_name=item.channel_id,
            )
            for item in ranked
        ]
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
