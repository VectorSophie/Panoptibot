from __future__ import annotations

from datetime import UTC, datetime

import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_command_access


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(name="debug", description="Show internal analytics and model status.")
    async def debug(interaction: discord.Interaction) -> None:
        if not await enforce_command_access(
            interaction, services.settings, services.rate_limiter
        ):
            return
        sessions = len(services.session_tracker._sessions)
        model_exists = services.settings.model_path.exists()
        stats_row = await services.graph.fetch_activity_stats(
            services.settings.training_lookback_days
        )
        await interaction.response.send_message(
            "\n".join(
                [
                    f"timestamp: {datetime.now(UTC).isoformat()}",
                    f"active_sessions_cached: {sessions}",
                    f"model_loaded: {model_exists}",
                    f"total_messages: {stats_row.get('total_messages', 0)}",
                    f"active_users: {stats_row.get('active_users', 0)}",
                ]
            ),
            ephemeral=True,
        )
