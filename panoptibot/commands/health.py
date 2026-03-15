from __future__ import annotations

from datetime import UTC, datetime
import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_command_access


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(name="health", description="Show bot and data store health.")
    async def health(interaction: discord.Interaction) -> None:
        if not await enforce_command_access(
            interaction, services.settings, services.rate_limiter
        ):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        neo4j_ok = await services.graph.check_connection()
        model_path = services.settings.model_path
        model_exists = model_path.exists()
        model_updated_at = None
        if model_exists:
            model_updated_at = datetime.fromtimestamp(
                model_path.stat().st_mtime, tz=UTC
            ).isoformat()
        lines = [
            f"timestamp: {datetime.now(UTC).isoformat()}",
            f"neo4j: {'ok' if neo4j_ok else 'degraded'}",
            f"model_exists: {model_exists}",
        ]
        if model_updated_at:
            lines.append(f"model_updated_at: {model_updated_at}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)
