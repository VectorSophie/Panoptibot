from __future__ import annotations

import io
import discord
from discord import app_commands
from PIL import Image

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_command_access
from panoptibot.visualization.plots import plot_interaction_graph


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(name="graph", description="Generate an interaction network PNG.")
    async def graph(interaction: discord.Interaction) -> None:
        if not await enforce_command_access(
            interaction, services.settings, services.rate_limiter
        ):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        edges = await services.graph.fetch_interaction_edges(
            services.settings.training_lookback_days
        )
        user_ids = sorted(
            {str(edge["source_user"]) for edge in edges}
            | {str(edge["target_user"]) for edge in edges}
        )
        node_images: dict[str, Image.Image] = {}
        if interaction.guild:
            for user_id in user_ids:
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
        label_map = {user_id: f"U{index + 1}" for index, user_id in enumerate(user_ids)}
        mapping_lines = [
            f"{label_map[user_id]} = <@{user_id}>" for user_id in user_ids[:15]
        ]
        if len(user_ids) > 15:
            mapping_lines.append(f"...and {len(user_ids) - 15} more")
        image_path = plot_interaction_graph(
            edges,
            label_map=label_map,
            node_images=node_images if node_images else None,
        )
        try:
            message = "Interaction graph generated."
            if mapping_lines:
                message = "\n".join([message, "Label map:", *mapping_lines])
            await interaction.followup.send(
                message, file=discord.File(image_path), ephemeral=True
            )
        finally:
            image_path.unlink(missing_ok=True)
