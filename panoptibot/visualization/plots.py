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
        local_radius = 0.9 + 0.22 * math.sqrt(max(len(component_nodes), 1))
        if len(component_nodes) == 1:
            pos[component_nodes[0]] = (center_x, center_y)
            continue
        local_layout = nx.circular_layout(
            graph.subgraph(component_nodes).to_undirected()
        )
        for node in component_nodes:
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
        for source_user, target_user in graph.edges:
            weight = float(graph[source_user][target_user].get("weight", 1.0))
            width = 1.0 + (3.0 * (weight / max_edge_weight))
            if graph.has_edge(target_user, source_user):
                curve = 0.25 if source_user < target_user else -0.25
            else:
                curve = 0.08
            source_x, source_y = pos[source_user]
            target_x, target_y = pos[target_user]
            mid_x = (source_x + target_x) / 2.0
            mid_y = (source_y + target_y) / 2.0
            dx = target_x - source_x
            dy = target_y - source_y
            length = math.hypot(dx, dy) or 1.0
            normal_x = -dy / length
            normal_y = dx / length
            label_x = mid_x + normal_x * (curve * 0.9)
            label_y = mid_y + normal_y * (curve * 0.9)
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=[(source_user, target_user)],
                width=width,
                arrowstyle="-|>",
                arrowsize=24,
                edge_color="#023047",
                connectionstyle=f"arc3,rad={curve}",
                min_source_margin=22 if node_has_images else 10,
                min_target_margin=26 if node_has_images else 12,
                ax=ax,
            )
            ax.text(
                label_x,
                label_y,
                str(int(weight)),
                fontsize=8,
                color="#111827",
                ha="center",
                va="center",
                bbox={
                    "facecolor": "white",
                    "edgecolor": "#9ca3af",
                    "alpha": 0.85,
                    "boxstyle": "round,pad=0.2",
                },
            )
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    path = _temp_png_path("panoptibot-graph-")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path
