from __future__ import annotations

import io
import re
import discord
from discord import app_commands
from PIL import Image

from panoptibot.analytics.emoji_stats import format_emoji_label
from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_command_access
from panoptibot.visualization.plots import (
    plot_emoji_distribution,
    plot_interaction_graph,
)


CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:\w+:(\d+)>")


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(
        name="emoji_culture",
        description="Show emoji frequency, reaction clusters, and trends.",
    )
    async def emoji_culture(interaction: discord.Interaction) -> None:
        if not await enforce_command_access(
            interaction, services.settings, services.rate_limiter
        ):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        week_days = 7
        month_days = 30
        emoji_week = await services.graph.fetch_emoji_counts(week_days, limit=20)
        emoji_month = await services.graph.fetch_emoji_counts(month_days, limit=50)
        reaction_edges = await services.graph.fetch_reaction_edges(
            month_days, limit=120
        )
        emoji_per_user = await services.graph.fetch_emoji_per_user(
            month_days, limit=10, per_user=3
        )

        emoji_month_map = {
            str(row.get("emoji", "")): float(row.get("usage_count", 0))
            for row in emoji_month
        }
        trending = []
        for row in emoji_week:
            emoji_value = str(row.get("emoji", ""))
            week_count = float(row.get("usage_count", 0))
            month_count = emoji_month_map.get(emoji_value, 0.0)
            score = week_count / max(month_count, 1.0)
            trending.append((emoji_value, week_count, month_count, score))
        trending.sort(key=lambda item: item[3], reverse=True)

        emoji_images: list[Image.Image | None] = []
        if interaction.guild:
            emoji_map = {emoji.id: emoji for emoji in interaction.guild.emojis}
            for row in emoji_week[:8]:
                emoji_value = str(row.get("emoji", ""))
                match = CUSTOM_EMOJI_PATTERN.fullmatch(emoji_value)
                if not match:
                    emoji_images.append(None)
                    continue
                emoji_id = int(match.group(1))
                emoji = emoji_map.get(emoji_id)
                if emoji is None:
                    emoji_images.append(None)
                    continue
                image_bytes = await emoji.read()
                emoji_images.append(Image.open(io.BytesIO(image_bytes)).convert("RGBA"))

        reaction_nodes = sorted(
            {str(edge["source_user"]) for edge in reaction_edges}
            | {str(edge["target_user"]) for edge in reaction_edges}
        )
        node_images: dict[str, Image.Image] = {}
        if interaction.guild:
            for user_id in reaction_nodes:
                member = interaction.guild.get_member(int(user_id))
                user = member or interaction.client.get_user(int(user_id))
                if user is None:
                    try:
                        user = await interaction.client.fetch_user(int(user_id))
                    except discord.HTTPException:
                        continue
                avatar_asset = user.display_avatar.replace(size=64)
                image_bytes = await avatar_asset.read()
                node_images[user_id] = Image.open(io.BytesIO(image_bytes)).convert(
                    "RGBA"
                )

        chart_path = plot_emoji_distribution(
            emoji_week[:8],
            title="Top Emoji This Week",
            emoji_images=emoji_images,
        )
        reaction_path = plot_interaction_graph(
            reaction_edges,
            title="Reaction Network",
            node_images=node_images if node_images else None,
        )

        lines = ["Emoji culture highlights:"]
        if emoji_week:
            top_emoji = emoji_week[0]
            lines.append(
                f"Top emoji this week: {format_emoji_label(top_emoji.get('emoji'))} ({top_emoji.get('usage_count')} messages)"
            )
        if trending:
            lines.append("Trending emojis:")
            for emoji_value, week_count, month_count, score in trending[:5]:
                lines.append(
                    f"- {format_emoji_label(emoji_value)} week={int(week_count)} msgs month={int(month_count)} msgs trend={score:.2f}"
                )
        if emoji_per_user:
            lines.append("Emoji per user:")
            for row in emoji_per_user[:5]:
                user_id = str(row.get("user_id", ""))
                entries = row.get("top_emojis", []) or []
                summary = ", ".join(
                    f"{format_emoji_label(entry.get('emoji'))} ({entry.get('usage_count')} msgs)"
                    for entry in entries
                )
                lines.append(f"- <@{user_id}>: {summary}")

        try:
            await interaction.followup.send(
                "\n".join(lines),
                files=[discord.File(chart_path), discord.File(reaction_path)],
                ephemeral=True,
            )
        finally:
            chart_path.unlink(missing_ok=True)
            reaction_path.unlink(missing_ok=True)
