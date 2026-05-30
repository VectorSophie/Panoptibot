from __future__ import annotations

from datetime import UTC, datetime

import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_user_command_access


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    group = app_commands.Group(name="copycat", description="Manage your away proxy.")

    @group.command(name="on", description="Enable Copycat for yourself.")
    async def copycat_on(
        interaction: discord.Interaction,
        duration: app_commands.Range[int, 1, 1440] | None = None,
        status_note: str = "",
    ) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        member = interaction.user
        duration_minutes = duration or services.settings.copycat_default_duration_minutes
        session = services.copycat_store.enable_session(
            owner_user_id=str(member.id),
            display_name=member.display_name,
            duration_minutes=duration_minutes,
            status_note=status_note,
        )
        await interaction.response.send_message(
            "\n".join(
                [
                    f"Copycat is on for @{member.display_name}.",
                    f"expires_at: {session.expires_at.isoformat()}",
                    "Add this channel with `/copycat channel_add` if it is not already allowlisted.",
                ]
            ),
            ephemeral=True,
        )

    @group.command(name="off", description="Disable Copycat for yourself.")
    async def copycat_off(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        services.copycat_store.disable_session(str(interaction.user.id))
        await interaction.response.send_message("Copycat is off.", ephemeral=True)

    @group.command(name="status", description="Show your Copycat status.")
    async def copycat_status(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        user_id = str(interaction.user.id)
        session = services.copycat_store.load_session(user_id)
        profile = services.copycat_store.load_profile(
            user_id, getattr(interaction.user, "display_name", user_id)
        )
        now = datetime.now(UTC)
        active = bool(session and session.active and now < session.expires_at)
        channels = (
            ", ".join(f"<#{channel_id}>" for channel_id in sorted(session.allowlisted_channel_ids))
            if session and session.allowlisted_channel_ids
            else "none"
        )
        await interaction.response.send_message(
            "\n".join(
                [
                    f"active: {active}",
                    f"history_enabled: {profile.history_enabled}",
                    f"retention_days: {profile.history_retention_days}",
                    f"allowlisted_channels: {channels}",
                ]
            ),
            ephemeral=True,
        )

    @group.command(name="channel_add", description="Allow Copycat replies in this channel.")
    async def channel_add(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        session = services.copycat_store.add_channel(
            str(interaction.user.id), str(interaction.channel_id)
        )
        if session is None:
            await interaction.response.send_message(
                "Turn Copycat on before adding channels.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Copycat can now reply in <#{interaction.channel_id}>.", ephemeral=True
        )

    @group.command(name="history_enable", description="Enable local text cache for your style.")
    async def history_enable(
        interaction: discord.Interaction,
        retention_days: app_commands.Range[int, 1, 365] | None = None,
    ) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        retention = retention_days or services.settings.copycat_history_retention_days
        services.copycat_store.update_profile(
            str(interaction.user.id),
            display_name=interaction.user.display_name,
            history_enabled=True,
            history_retention_days=retention,
        )
        await interaction.response.send_message(
            f"Copycat history cache enabled for {retention} days.", ephemeral=True
        )

    @group.command(name="history_disable", description="Disable local text cache for your style.")
    async def history_disable(interaction: discord.Interaction) -> None:
        if not await enforce_user_command_access(interaction, services.rate_limiter):
            return
        services.copycat_store.update_profile(
            str(interaction.user.id),
            display_name=interaction.user.display_name,
            history_enabled=False,
        )
        await interaction.response.send_message(
            "Copycat history cache disabled.", ephemeral=True
        )

    tree.add_command(group)
