from __future__ import annotations

from pathlib import Path
import io
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
    labels = [str(row.get("emoji", "")) for row in ordered] or ["none"]
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
        graph.add_edge(
            str(edge["source_user"]),
            str(edge["target_user"]),
            weight=max(_as_int(edge.get("weight")), 1),
        )
    if not graph.nodes:
        graph.add_node("no-data")
    node_count = max(len(graph.nodes), 1)
    pos = nx.spring_layout(graph, seed=42, k=1.1 / (node_count**0.5), iterations=100)
    weights = [graph[u][v].get("weight", 1) for u, v in graph.edges] or [1]
    fig, ax = plt.subplots(figsize=(10, 10))
    nx.draw_networkx_nodes(graph, pos, node_size=900, node_color="#8ecae6", ax=ax)
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
        nx.draw_networkx_edges(
            graph,
            pos,
            width=weights,
            arrowstyle="->",
            arrowsize=14,
            edge_color="#023047",
            ax=ax,
        )
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    path = _temp_png_path("panoptibot-graph-")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path
