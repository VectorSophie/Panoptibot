from __future__ import annotations

import asyncio
import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_user_command_access
from panoptibot.culture.lore import trending_phrases
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
        archetype_rows = await services.graph.fetch_archetype_distribution(7)
        tone_recent = await services.graph.fetch_tone_stats(7)
        tone_baseline = await services.graph.fetch_tone_stats(30)

        lines = culture_memory_lines(
            emoji_rows=emoji_rows,
            bridge_rows=bridge_users(edge_rows, limit=5),
        )

        # Archetype summary
        if archetype_rows:
            total = sum(int(row.get("count", 0)) for row in archetype_rows)
            if total > 0:
                top = archetype_rows[0]
                archetype = str(top.get("archetype") or "unknown").replace("_", " ")
                pct = round(100 * int(top.get("count", 0)) / total)
                lines.append(f"- Content this week: {pct}% {archetype}")

        # Tone note (only if we have baseline data to compare against)
        recent_caps = tone_recent.get("avg_caps_ratio")
        baseline_caps = tone_baseline.get("avg_caps_ratio")
        recent_punct = tone_recent.get("avg_punctuation_density")
        baseline_punct = tone_baseline.get("avg_punctuation_density")
        if recent_caps and baseline_caps and baseline_caps > 0:
            if recent_caps > baseline_caps * 1.5:
                lines.append("- Elevated energy this period")
        elif recent_punct and baseline_punct and baseline_punct > 0:
            if recent_punct > baseline_punct * 1.5:
                lines.append("- High-energy replies this period")

        # Top trending phrase
        top_phrases = await asyncio.to_thread(
            trending_phrases, services.settings.phrases_dir, recent_days=7, limit=1
        )
        if top_phrases:
            term, score = top_phrases[0]
            lines.append(f"- Trending phrase: \"{term}\" (trend score {score:.1f}×)")

        await interaction.followup.send("\n".join(lines), ephemeral=True)

    @group.command(name="lore", description="Show phrases trending in the community this week.")
    async def culture_lore(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        phrases = await asyncio.to_thread(
            trending_phrases,
            services.settings.phrases_dir,
            recent_days=7,
            baseline_days=30,
            min_recent_count=3,
            limit=5,
        )
        if not phrases:
            await interaction.followup.send(
                "Not enough phrase data yet — check back after a few days of activity.",
                ephemeral=True,
            )
            return
        lines = ["Trending phrases this week:"]
        for term, score in phrases:
            lines.append(f"- **{term}** — {score:.1f}× usual rate")
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
