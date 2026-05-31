from __future__ import annotations

import discord
from discord import app_commands
import networkx as nx

from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.security import enforce_command_access


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(name="influence", description="Find top influencers this month.")
    async def influence(interaction: discord.Interaction) -> None:
        if not await enforce_command_access(
            interaction, services.settings, services.rate_limiter
        ):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        lookback_days = 30
        edges = await services.graph.fetch_interaction_edges(lookback_days)
        if not edges:
            await interaction.followup.send(
                "No interaction data available yet.", ephemeral=True
            )
            return
        graph = nx.DiGraph()
        for edge in edges:
            graph.add_edge(
                str(edge["source_user"]),
                str(edge["target_user"]),
                weight=float(edge.get("weight", 1)),
            )
        pagerank = nx.pagerank(graph, weight="weight")
        degree = nx.degree_centrality(graph.to_undirected())
        reply_rows = await services.graph.fetch_reply_influence(lookback_days)
        reaction_rows = await services.graph.fetch_reaction_influence(lookback_days)
        reply_map = {
            str(row["user_id"]): float(row.get("reply_count", 0)) for row in reply_rows
        }
        reaction_map = {
            str(row["user_id"]): float(row.get("reaction_count", 0))
            for row in reaction_rows
        }
        max_reply = max(reply_map.values()) if reply_map else 1.0
        max_reaction = max(reaction_map.values()) if reaction_map else 1.0
        max_pagerank = max(pagerank.values()) if pagerank else 1.0
        max_degree = max(degree.values()) if degree else 1.0

        scored = []
        for user_id in graph.nodes:
            score = (
                (pagerank.get(user_id, 0.0) / max_pagerank) * 0.4
                + (degree.get(user_id, 0.0) / max_degree) * 0.2
                + (reply_map.get(user_id, 0.0) / max_reply) * 0.2
                + (reaction_map.get(user_id, 0.0) / max_reaction) * 0.2
            )
            scored.append(
                (
                    user_id,
                    score,
                    pagerank.get(user_id, 0.0),
                    degree.get(user_id, 0.0),
                    reply_map.get(user_id, 0.0),
                    reaction_map.get(user_id, 0.0),
                )
            )
        scored.sort(key=lambda item: item[1], reverse=True)
        top_user_ids = [uid for uid, *_ in scored[:5]]
        archetype_rows = await services.graph.fetch_user_archetypes(lookback_days, top_user_ids)

        archetype_map: dict[str, list[tuple[str, int]]] = {}
        for row in archetype_rows:
            uid = str(row.get("user_id", ""))
            arc = str(row.get("archetype") or "unknown")
            cnt = int(row.get("count", 0))
            archetype_map.setdefault(uid, []).append((arc, cnt))

        lines = ["Top influencers this month:"]
        for index, (user_id, score, pr, deg, replies, reactions) in enumerate(
            scored[:5], start=1
        ):
            lines.append(
                " ".join(
                    [
                        f"{index}.",
                        f"<@{user_id}>",
                        f"score={score:.3f}",
                        f"pagerank={pr:.4f}",
                        f"centrality={deg:.3f}",
                        f"reply_influence={int(replies)}",
                        f"reaction_influence={int(reactions)}",
                    ]
                )
            )
            user_arcs = archetype_map.get(user_id, [])
            if user_arcs:
                total_arc = sum(c for _, c in user_arcs) or 1
                arc_summary = ", ".join(
                    f"{a.replace('_', ' ')} {round(100 * c / total_arc)}%"
                    for a, c in user_arcs[:3]
                )
                lines.append(f"   → primarily: {arc_summary}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)
