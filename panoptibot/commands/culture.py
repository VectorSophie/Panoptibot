from __future__ import annotations

import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_user_command_access
from panoptibot.culture.memory import bridge_users, culture_memory_lines


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    group = app_commands.Group(
        name="culture", description="Explore community culture memory."
    )

    @group.command(name="memory", description="Show recent culture-memory motifs.")
    async def culture_memory(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        emoji_rows = await services.graph.fetch_emoji_counts(14, limit=5)
        edge_rows = await services.graph.fetch_interaction_edges(14, limit=100)
        lines = culture_memory_lines(
            emoji_rows=emoji_rows,
            bridge_rows=bridge_users(edge_rows, limit=5),
        )
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    @group.command(name="emoji", description="Show recently prominent emojis.")
    async def culture_emoji(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        rows = await services.graph.fetch_emoji_counts(14, limit=10)
        if not rows:
            await interaction.response.send_message(
                "No emoji patterns found yet.", ephemeral=True
            )
            return
        lines = ["Emoji culture, last 14 days"]
        lines.extend(
            f"- {row.get('emoji')}: {row.get('usage_count')} uses" for row in rows
        )
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @group.command(name="bridges", description="Show bridge user candidates.")
    async def culture_bridges(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        rows = await services.graph.fetch_interaction_edges(14, limit=100)
        bridges = bridge_users(rows, limit=10)
        if not bridges:
            await interaction.response.send_message(
                "No bridge candidates found yet.", ephemeral=True
            )
            return
        lines = ["Bridge user candidates, last 14 days"]
        lines.extend(f"- <@{user_id}> score={score:.1f}" for user_id, score in bridges)
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    tree.add_command(group)
