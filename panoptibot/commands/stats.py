from __future__ import annotations

import io
import re
import discord
from discord import app_commands
from PIL import Image

from panoptibot.analytics.activity_stats import summarize_activity
from panoptibot.analytics.emoji_stats import summarize_emoji_distribution
from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_command_access
from panoptibot.visualization.plots import plot_emoji_distribution


CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:\w+:(\d+)>")


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(
        name="stats", description="Show Panoptibot activity and culture statistics."
    )
    async def stats(interaction: discord.Interaction) -> None:
        if not await enforce_command_access(
            interaction, services.settings, services.rate_limiter
        ):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        stats_row = await services.graph.fetch_activity_stats(
            services.settings.training_lookback_days
        )
        top_users = await services.graph.fetch_top_users(
            services.settings.training_lookback_days
        )
        emoji_rows = await services.graph.fetch_emoji_counts(
            services.settings.training_lookback_days
        )
        emoji_images: list[Image.Image | None] = []
        if interaction.guild:
            emoji_map = {emoji.id: emoji for emoji in interaction.guild.emojis}
            for row in emoji_rows[:8]:
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
        message = (
            summarize_activity(stats_row, top_users)
            + "\n\nEmoji culture:\n"
            + summarize_emoji_distribution(emoji_rows[:8])
        )
        image_path = plot_emoji_distribution(emoji_rows[:8], emoji_images=emoji_images)
        try:
            await interaction.followup.send(
                message, file=discord.File(image_path), ephemeral=True
            )
        finally:
            image_path.unlink(missing_ok=True)
