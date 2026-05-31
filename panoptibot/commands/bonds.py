from __future__ import annotations

import asyncio
import discord
from discord import app_commands

from panoptibot.bonds.lm_labels import audit_bond_label, generate_bond_label
from panoptibot.bonds.scorer import get_shared_terms, load_user_phrase_counts, score_pairs
from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_command_access
from panoptibot.visualization.plots import plot_bonds_graph

_MAX_LM_PAIRS = 12
_LOOKBACK_DAYS = 365


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(name="bonds", description="Show social bond graph for this server.")
    async def bonds(interaction: discord.Interaction) -> None:
        if not await enforce_command_access(
            interaction, services.settings, services.rate_limiter
        ):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        edges = await services.graph.fetch_bonds_edges(_LOOKBACK_DAYS, limit=500)
        if not edges:
            await interaction.followup.send(
                "Not enough interaction data yet.", ephemeral=True
            )
            return

        user_phrase_counts = await asyncio.to_thread(
            load_user_phrase_counts, services.settings.phrases_dir, 30
        )
        pairs = score_pairs(edges, user_phrase_counts, services.settings.bonds_min_weight)
        if not pairs:
            await interaction.followup.send(
                "Not enough mutual interactions to build bond graph.", ephemeral=True
            )
            return

        display_names: dict[str, str] = {}
        if interaction.guild:
            for uid in {p.user_a for p in pairs} | {p.user_b for p in pairs}:
                member = interaction.guild.get_member(int(uid))
                display_names[uid] = member.display_name if member else uid

        top_pairs = pairs[:_MAX_LM_PAIRS]
        pair_labels: dict[tuple[str, str], str] = {}

        for pair in top_pairs:
            name_a = display_names.get(pair.user_a, pair.user_a)
            name_b = display_names.get(pair.user_b, pair.user_b)
            shared_terms = get_shared_terms(user_phrase_counts, pair.user_a, pair.user_b)
            label, shared_note, arc_note = await asyncio.to_thread(
                generate_bond_label,
                settings=services.settings,
                pair=pair,
                name_a=name_a,
                name_b=name_b,
                shared_terms=shared_terms,
            )
            pair_labels[(pair.user_a, pair.user_b)] = label
            await asyncio.to_thread(
                audit_bond_label,
                bonds_dir=services.settings.bonds_dir,
                user_a=pair.user_a,
                user_b=pair.user_b,
                label=label,
                shared_note=shared_note,
                arc_note=arc_note,
                model_name=services.settings.lm_studio_model,
            )

        pair_dicts = [
            {
                "user_a": p.user_a,
                "user_b": p.user_b,
                "weight_a_to_b": p.weight_a_to_b,
                "weight_b_to_a": p.weight_b_to_a,
            }
            for p in top_pairs
        ]
        chart_path = plot_bonds_graph(pair_dicts, display_names, pair_labels)
        try:
            lines = [f"Bond graph — top {len(top_pairs)} pairs by closeness:"]
            for pair in top_pairs[:5]:
                name_a = display_names.get(pair.user_a, pair.user_a)
                name_b = display_names.get(pair.user_b, pair.user_b)
                label = pair_labels.get((pair.user_a, pair.user_b), "unknown")
                lines.append(
                    f"- {name_a} ↔ {name_b}  score={pair.closeness_score:.2f}  [{label}]"
                )
            await interaction.followup.send(
                "\n".join(lines),
                files=[discord.File(chart_path)],
                ephemeral=True,
            )
        finally:
            chart_path.unlink(missing_ok=True)
