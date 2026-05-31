from __future__ import annotations

from pathlib import Path
import io
import math
import tempfile
from typing import Any, Mapping, Sequence, cast

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from numpy.typing import NDArray
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image
from panoptibot.analytics.emoji_stats import format_emoji_label


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    return 0


def _temp_png_path(prefix: str) -> Path:
    with tempfile.NamedTemporaryFile(
        prefix=prefix, suffix=".png", delete=False
    ) as handle:
        return Path(handle.name)


def _to_image(data: bytes | Image.Image) -> Image.Image:
    if isinstance(data, Image.Image):
        return data
    return Image.open(io.BytesIO(data)).convert("RGBA")


def plot_emoji_distribution(
    rows: list[dict[str, object]],
    title: str = "Emoji Culture Distribution",
    emoji_images: Sequence[bytes | Image.Image | None] | None = None,
) -> Path:
    ordered = sorted(
        rows, key=lambda row: _as_int(row.get("usage_count")), reverse=True
    )
    labels = [format_emoji_label(row.get("emoji", "")) for row in ordered] or ["none"]
    values = [_as_int(row.get("usage_count")) for row in ordered] or [0]
    fig_height = max(4, min(12, 0.5 * len(labels) + 2))
    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.barh(labels, values, color="#1f77b4")
    ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel("Uses")
    ax.set_ylabel("Emoji")
    if emoji_images:
        max_value = max(values) if values else 1
        for index, image in enumerate(emoji_images[: len(labels)]):
            if image is None:
                continue
            emoji_image = _to_image(image)
            image_array: NDArray[Any] = cast(NDArray[Any], np.asarray(emoji_image))
            image_box = OffsetImage(image_array, zoom=0.35)
            annotation = AnnotationBbox(
                image_box,
                (max_value * -0.06, index),
                frameon=False,
                box_alignment=(0.5, 0.5),
            )
            ax.add_artist(annotation)
        ax.set_xlim(left=max_value * -0.12)
    fig.tight_layout()
    path = _temp_png_path("panoptibot-emoji-")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_activity_timeline(
    points: list[tuple[str, int]], title: str = "Activity Timeline"
) -> Path:
    labels = [point[0] for point in points] or ["none"]
    values = [point[1] for point in points] or [0]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(labels, values, marker="o", color="#ff7f0e")
    ax.set_title(title)
    ax.set_ylabel("Messages")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    path = _temp_png_path("panoptibot-activity-")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_interaction_graph(
    edges: list[dict[str, object]],
    title: str = "Interaction Graph",
    label_map: Mapping[str, str] | None = None,
    node_images: Mapping[str, bytes | Image.Image] | None = None,
) -> Path:
    graph = nx.DiGraph()
    for edge in edges:
        source_user = str(edge["source_user"])
        target_user = str(edge["target_user"])
        if source_user == target_user:
            continue
        graph.add_edge(
            source_user, target_user, weight=max(_as_int(edge.get("weight")), 1)
        )
    if not graph.nodes:
        graph.add_node("no-data")

    influence = {node: 0.0 for node in graph.nodes}
    for u, v, d in graph.edges(data=True):
        w = float(d.get("weight", 1.0))
        influence[u] += w
        influence[v] += w

    components = [
        sorted(component) for component in nx.weakly_connected_components(graph)
    ]
    components.sort(key=len, reverse=True)
    component_count = max(len(components), 1)
    center_ring_radius = 4.0 if component_count > 1 else 0.0
    pos: dict[str, tuple[float, float]] = {}

    for index, component_nodes in enumerate(components):
        if component_count == 1:
            center_x, center_y = 0.0, 0.0
        else:
            angle = (2 * math.pi * index) / component_count
            center_x = center_ring_radius * math.cos(angle)
            center_y = center_ring_radius * math.sin(angle)

        comp_top_node = max(component_nodes, key=lambda n: influence[n])
        pos[comp_top_node] = (center_x, center_y)

        others = [n for n in component_nodes if n != comp_top_node]
        if not others:
            continue

        # Hub-and-spoke layout: radial distance depends on component size
        local_radius = 1.1 + 0.25 * math.sqrt(max(len(others), 1))
        local_layout = nx.circular_layout(graph.subgraph(others).to_undirected())
        for node in others:
            node_pos = cast(NDArray[Any], local_layout[node])
            pos[node] = (
                center_x + float(node_pos[0]) * local_radius,
                center_y + float(node_pos[1]) * local_radius,
            )

    edge_weights = [graph[u][v].get("weight", 1) for u, v in graph.edges] or [1]
    max_edge_weight = max(edge_weights)
    fig, ax = plt.subplots(figsize=(10, 10))
    nx.draw_networkx_nodes(graph, pos, node_size=900, node_color="#8ecae6", ax=ax)
    node_has_images = bool(node_images)
    if node_images:
        for node in graph.nodes:
            image_data = node_images.get(str(node))
            if not image_data:
                continue
            avatar_image = _to_image(image_data)
            image_array = cast(NDArray[Any], np.asarray(avatar_image))
            image_box = OffsetImage(image_array, zoom=0.55)
            position = pos[node]
            xy = (float(position[0]), float(position[1]))
            annotation = AnnotationBbox(
                image_box,
                xy,
                frameon=True,
                bboxprops={"edgecolor": "#1f2937", "linewidth": 1.0},
            )
            ax.add_artist(annotation)
    else:
        labels = (
            {node: str(node) for node in graph.nodes}
            if label_map is None
            else {node: label_map.get(str(node), str(node)) for node in graph.nodes}
        )
        nx.draw_networkx_labels(
            graph,
            pos,
            labels=labels,
            font_size=8,
            bbox={"facecolor": "white", "edgecolor": "#1f2937", "alpha": 0.6},
            ax=ax,
        )
    if graph.edges:
        weights_list = [float(graph[u][v].get("weight", 1.0)) for u, v in graph.edges]
        # Filter labels by percentile to prevent unreadable overlaps in dense graphs
        weight_threshold = (
            np.percentile(weights_list, 40) if len(weights_list) > 40 else 0
        )

        for source_user, target_user in graph.edges:
            weight = float(graph[source_user][target_user].get("weight", 1.0))
            width = 1.0 + (3.0 * (weight / max_edge_weight))

            is_mutual = graph.has_edge(target_user, source_user)
            if is_mutual:
                curve = 0.22 if source_user < target_user else -0.22
            else:
                curve = 0.12

            source_x, source_y = pos[source_user]
            target_x, target_y = pos[target_user]

            # Label positioning offset (30% along edge) to avoid hub congestion
            lx = source_x + (target_x - source_x) * 0.3
            ly = source_y + (target_y - source_y) * 0.3

            dx = target_x - source_x
            dy = target_y - source_y
            length = math.hypot(dx, dy) or 1.0
            normal_x = -dy / length
            normal_y = dx / length
            label_x = lx + normal_x * (curve * 0.7)
            label_y = ly + normal_y * (curve * 0.7)

            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=[(source_user, target_user)],
                width=width,
                arrowstyle="-|>",
                arrowsize=20,
                edge_color="#023047",
                connectionstyle=f"arc3,rad={curve}",
                min_source_margin=24 if node_has_images else 12,
                min_target_margin=28 if node_has_images else 14,
                ax=ax,
            )

            if weight >= weight_threshold:
                ax.text(
                    label_x,
                    label_y,
                    str(int(weight)),
                    fontsize=7,
                    color="#111827",
                    ha="center",
                    va="center",
                    bbox={
                        "facecolor": "white",
                        "edgecolor": "#9ca3af",
                        "alpha": 0.9,
                        "boxstyle": "round,pad=0.15",
                    },
                )

    edge_weights = [graph[u][v].get("weight", 1) for u, v in graph.edges] or [1]
    max_edge_weight = max(edge_weights)
    fig, ax = plt.subplots(figsize=(10, 10))
    nx.draw_networkx_nodes(graph, pos, node_size=900, node_color="#8ecae6", ax=ax)
    node_has_images = bool(node_images)
    if node_images:
        for node in graph.nodes:
            image_data = node_images.get(str(node))
            if not image_data:
                continue
            avatar_image = _to_image(image_data)
            image_array = cast(NDArray[Any], np.asarray(avatar_image))
            image_box = OffsetImage(image_array, zoom=0.55)
            position = pos[node]
            xy = (float(position[0]), float(position[1]))
            annotation = AnnotationBbox(
                image_box,
                xy,
                frameon=True,
                bboxprops={"edgecolor": "#1f2937", "linewidth": 1.0},
            )
            ax.add_artist(annotation)
    else:
        labels = (
            {node: str(node) for node in graph.nodes}
            if label_map is None
            else {node: label_map.get(str(node), str(node)) for node in graph.nodes}
        )
        nx.draw_networkx_labels(
            graph,
            pos,
            labels=labels,
            font_size=8,
            bbox={"facecolor": "white", "edgecolor": "#1f2937", "alpha": 0.6},
            ax=ax,
        )
    if graph.edges:
        # Only show labels for top weight edges if the graph is dense
        weights_list = [float(graph[u][v].get("weight", 1.0)) for u, v in graph.edges]
        weight_threshold = (
            np.percentile(weights_list, 40) if len(weights_list) > 40 else 0
        )

        for source_user, target_user in graph.edges:
            weight = float(graph[source_user][target_user].get("weight", 1.0))
            width = 1.0 + (3.0 * (weight / max_edge_weight))

            # Use distinct curvature for mutual vs single edges
            is_mutual = graph.has_edge(target_user, source_user)
            if is_mutual:
                curve = 0.22 if source_user < target_user else -0.22
            else:
                curve = 0.12

            source_x, source_y = pos[source_user]
            target_x, target_y = pos[target_user]

            # Position label at 30% along the edge to avoid central hub clutter
            lx = source_x + (target_x - source_x) * 0.3
            ly = source_y + (target_y - source_y) * 0.3

            # Apply normal offset for curved edges
            dx = target_x - source_x
            dy = target_y - source_y
            length = math.hypot(dx, dy) or 1.0
            normal_x = -dy / length
            normal_y = dx / length
            label_x = lx + normal_x * (curve * 0.7)
            label_y = ly + normal_y * (curve * 0.7)

            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=[(source_user, target_user)],
                width=width,
                arrowstyle="-|>",
                arrowsize=20,
                edge_color="#023047",
                connectionstyle=f"arc3,rad={curve}",
                min_source_margin=24 if node_has_images else 12,
                min_target_margin=28 if node_has_images else 14,
                ax=ax,
            )

            # Only draw weight label if significant or graph is sparse
            if weight >= weight_threshold:
                ax.text(
                    label_x,
                    label_y,
                    str(int(weight)),
                    fontsize=7,
                    color="#111827",
                    ha="center",
                    va="center",
                    bbox={
                        "facecolor": "white",
                        "edgecolor": "#9ca3af",
                        "alpha": 0.9,
                        "boxstyle": "round,pad=0.15",
                    },
                )

    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    path = _temp_png_path("panoptibot-graph-")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


_BOND_LABEL_COLORS: dict[str, str] = {
    "art mutual": "#52b788",
    "hype partners": "#52b788",
    "close allies": "#52b788",
    "co-conspirators": "#52b788",
    "theory partners": "#52b788",
    "lore debate duo": "#f4a261",
    "debate duo": "#f4a261",
    "one-sided appreciation": "#90e0ef",
    "one-sided": "#90e0ef",
    "warm but drifting": "#adb5bd",
    "cordial lurkers": "#adb5bd",
    "cordial": "#adb5bd",
    "quiet fans": "#adb5bd",
}


def _bond_edge_color(label: str) -> str:
    normalized = label.lower()
    for key, color in _BOND_LABEL_COLORS.items():
        if key in normalized:
            return color
    if any(w in normalized for w in ("mutual", "close", "hype", "duo", "partner", "allies")):
        return "#52b788"
    if any(w in normalized for w in ("one-sided", "sided")):
        return "#90e0ef"
    if any(w in normalized for w in ("drifting", "cordial", "quiet", "lurk")):
        return "#adb5bd"
    return "#dee2e6"


def plot_bonds_graph(
    pairs: list[dict[str, Any]],
    display_names: dict[str, str],
    pair_labels: dict[tuple[str, str], str],
) -> Path:
    """pairs entries: user_a, user_b, weight_a_to_b, weight_b_to_a"""
    graph = nx.DiGraph()
    for pair in pairs:
        a, b = str(pair["user_a"]), str(pair["user_b"])
        if pair.get("weight_a_to_b", 0) > 0:
            graph.add_edge(a, b, weight=float(pair["weight_a_to_b"]))
        if pair.get("weight_b_to_a", 0) > 0:
            graph.add_edge(b, a, weight=float(pair["weight_b_to_a"]))

    if not graph.nodes:
        graph.add_node("no-data")

    centrality: dict[str, float] = {node: 0.0 for node in graph.nodes}
    for u, v, d in graph.edges(data=True):
        w = float(d.get("weight", 1.0))
        centrality[u] += w
        centrality[v] += w

    max_centrality = max(centrality.values()) or 1.0
    node_sizes = [400 + 1200 * (centrality.get(n, 0.0) / max_centrality) for n in graph.nodes]
    node_labels = {n: display_names.get(str(n), str(n)) for n in graph.nodes}

    pos = nx.spring_layout(graph, k=2.5, seed=42)
    max_weight = max((float(d.get("weight", 1)) for _, _, d in graph.edges(data=True)), default=1.0)

    fig, ax = plt.subplots(figsize=(10, 10))
    nx.draw_networkx_nodes(graph, pos, node_size=node_sizes, node_color="#8ecae6", ax=ax)
    nx.draw_networkx_labels(
        graph, pos, labels=node_labels, font_size=8,
        bbox={"facecolor": "white", "edgecolor": "#1f2937", "alpha": 0.75},
        ax=ax,
    )

    drawn_pair_labels: set[frozenset[str]] = set()
    for a, b in graph.edges:
        weight = float(graph[a][b].get("weight", 1.0))
        width = 1.0 + 3.0 * (weight / max_weight)
        is_mutual = graph.has_edge(b, a)
        curve = (0.25 if a < b else -0.25) if is_mutual else 0.12

        label = pair_labels.get((a, b)) or pair_labels.get((b, a)) or "unknown"
        edge_color = _bond_edge_color(label)

        nx.draw_networkx_edges(
            graph, pos,
            edgelist=[(a, b)],
            width=width,
            arrowstyle="-|>",
            arrowsize=18,
            edge_color=edge_color,
            connectionstyle=f"arc3,rad={curve}",
            min_source_margin=18,
            min_target_margin=22,
            ax=ax,
        )

        pair_key = frozenset({a, b})
        if pair_key not in drawn_pair_labels:
            drawn_pair_labels.add(pair_key)
            src_x, src_y = pos[a]
            tgt_x, tgt_y = pos[b]
            mid_x = (src_x + tgt_x) / 2
            mid_y = (src_y + tgt_y) / 2
            ax.text(
                mid_x, mid_y, label,
                fontsize=6, color="#111827", ha="center", va="center",
                bbox={"facecolor": "white", "edgecolor": edge_color, "alpha": 0.9, "boxstyle": "round,pad=0.2"},
            )

    ax.set_title("Bond Graph", fontsize=14)
    ax.axis("off")
    fig.tight_layout()
    path = _temp_png_path("panoptibot-bonds-")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path
