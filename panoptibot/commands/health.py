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
        (
            neo4j_ok,
            neo4j_latency_ms,
        ) = await services.graph.check_connection_with_latency()
        model_path = services.settings.model_path
        model_exists = model_path.exists()
        model_updated_at = None
        model_age_hours = None
        if model_exists:
            model_mtime = datetime.fromtimestamp(model_path.stat().st_mtime, tz=UTC)
            model_updated_at = model_mtime.isoformat()
            model_age_hours = (datetime.now(UTC) - model_mtime).total_seconds() / 3600.0
        sessions_cached = len(services.session_tracker._sessions)
        settings = services.settings
        lines = [
            f"timestamp: {datetime.now(UTC).isoformat()}",
            " ".join(
                [
                    f"neo4j: {'ok' if neo4j_ok else 'degraded'}",
                    f"latency_ms={neo4j_latency_ms:.1f}"
                    if neo4j_latency_ms is not None
                    else "latency_ms=unknown",
                ]
            ),
            f"model_exists: {model_exists}",
            f"sessions_cached: {sessions_cached}",
            " ".join(
                [
                    "rate_limit:",
                    f"count={settings.command_rate_limit_count}",
                    f"window_s={settings.command_rate_limit_window}",
                ]
            ),
            " ".join(
                [
                    "lookbacks:",
                    f"summary_h={settings.summary_lookback_hours}",
                    f"training_days={settings.training_lookback_days}",
                ]
            ),
            f"guild_id: {settings.guild_id}",
        ]
        if model_updated_at:
            lines.append(f"model_updated_at: {model_updated_at}")
        if model_age_hours is not None:
            lines.append(f"model_age_hours: {model_age_hours:.2f}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)
