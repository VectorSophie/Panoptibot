from __future__ import annotations

from datetime import UTC, datetime
import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_command_access


def _format_message_reference(
    guild_id: int | None, channel_id: str, message_id: str
) -> str:
    if guild_id is None:
        return f"`{message_id}`"
    url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
    return f"<{url}>"


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(
        name="summary", description="Rank important missed messages for catch-up."
    )
    @app_commands.describe(days="Number of days to look back (default: 1)")
    async def summary(interaction: discord.Interaction, days: int = 1) -> None:
        if not await enforce_command_access(
            interaction, services.settings, services.rate_limiter
        ):
            return
        try:
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
                limit=40,
            )
            ranked = services.recommender.rank(interaction.user.id, candidates)[:5]
            if not ranked:
                await interaction.followup.send(
                    "No recent candidate messages were found.", ephemeral=True
                )
                return
            lines = [
                f"Missed message candidates scanned: {len(candidates)}",
                "Ranked catch-up messages:",
            ]
            guild_id = interaction.guild_id
            for item in ranked:
                message_ref = _format_message_reference(
                    guild_id, item.channel_id, item.message_id
                )
                lines.append(
                    f"- message {message_ref} in <#{item.channel_id}> by <@{item.author_id}> "
                    f"score={item.score:.2f} reactions={item.reaction_count} replies={item.reply_count}"
                )
            thread_lines = [
                f"- thread candidate {_format_message_reference(guild_id, item.channel_id, item.message_id)} in <#{item.channel_id}>"
                for item in ranked
                if item.reply_count > 0
            ]
            if thread_lines:
                lines.append("Threads of interest:")
                lines.extend(thread_lines[:3])
            await interaction.followup.send("\n".join(lines), ephemeral=True)
        except Exception as exc:
            services.logger.error(
                "summary_failed",
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "user_id": str(interaction.user.id),
                    "error": str(exc),
                },
            )
            message = "Summary failed. Check logs/errors for details."
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
