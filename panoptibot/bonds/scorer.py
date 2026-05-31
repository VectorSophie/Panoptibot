from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
import json

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None


@dataclass(slots=True)
class BondPair:
    user_a: str
    user_b: str
    weight_a_to_b: float
    weight_b_to_a: float
    reciprocity: float
    shared_vocab_score: float
    closeness_score: float
    first_seen_at: str | None


def load_user_phrase_counts(
    phrases_dir: Path, lookback_days: int
) -> dict[str, Counter[str]]:
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    user_counts: dict[str, Counter[str]] = {}
    for path in sorted(phrases_dir.glob("*.jsonl")):
        for raw_line in path.read_bytes().splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            record: dict[str, Any] = orjson.loads(raw_line) if orjson else json.loads(raw_line)
            try:
                ts = datetime.fromisoformat(record["timestamp"]).astimezone(UTC)
            except (KeyError, ValueError):
                continue
            if ts < cutoff:
                continue
            uid = str(record.get("user_id", ""))
            if not uid:
                continue
            counter = user_counts.setdefault(uid, Counter())
            for term in record.get("terms", []):
                counter[str(term)] += 1
    return user_counts


def get_shared_terms(
    user_phrase_counts: dict[str, Counter[str]],
    user_a: str,
    user_b: str,
    top_n: int = 30,
) -> list[str]:
    counts_a = user_phrase_counts.get(user_a, Counter())
    counts_b = user_phrase_counts.get(user_b, Counter())
    top_a = {term for term, _ in counts_a.most_common(top_n)}
    top_b = {term for term, _ in counts_b.most_common(top_n)}
    shared = top_a & top_b
    return sorted(t for t in shared if "_" not in t)[:5]


def score_pairs(
    edges: list[dict[str, Any]],
    user_phrase_counts: dict[str, Counter[str]],
    min_weight: int,
) -> list[BondPair]:
    weight_map: dict[tuple[str, str], float] = {}
    first_seen_map: dict[tuple[str, str], str | None] = {}
    for edge in edges:
        src = str(edge.get("source_user", ""))
        dst = str(edge.get("target_user", ""))
        if not src or not dst or src == dst:
            continue
        weight_map[(src, dst)] = float(edge.get("weight", 0.0) or 0.0)
        first_seen_map[(src, dst)] = edge.get("first_seen_at") or None

    seen: set[frozenset[str]] = set()
    raw_pairs: list[BondPair] = []
    for (a, b), w_ab in weight_map.items():
        key = frozenset({a, b})
        if key in seen:
            continue
        seen.add(key)
        w_ba = weight_map.get((b, a), 0.0)
        if w_ab + w_ba < min_weight:
            continue
        reciprocity = min(w_ab, w_ba) / max(w_ab, w_ba, 1.0)
        shared_terms = get_shared_terms(user_phrase_counts, a, b)
        raw_pairs.append(BondPair(
            user_a=a,
            user_b=b,
            weight_a_to_b=w_ab,
            weight_b_to_a=w_ba,
            reciprocity=reciprocity,
            shared_vocab_score=float(len(shared_terms)),
            closeness_score=0.0,
            first_seen_at=first_seen_map.get((a, b)) or first_seen_map.get((b, a)),
        ))

    if not raw_pairs:
        return []

    max_weight = max(p.weight_a_to_b + p.weight_b_to_a for p in raw_pairs) or 1.0
    max_shared = max(p.shared_vocab_score for p in raw_pairs) or 1.0

    result: list[BondPair] = []
    for p in raw_pairs:
        norm_w = (p.weight_a_to_b + p.weight_b_to_a) / max_weight
        norm_s = p.shared_vocab_score / max_shared
        score = round(0.5 * norm_w + 0.3 * p.reciprocity + 0.2 * norm_s, 4)
        result.append(BondPair(
            user_a=p.user_a,
            user_b=p.user_b,
            weight_a_to_b=p.weight_a_to_b,
            weight_b_to_a=p.weight_b_to_a,
            reciprocity=p.reciprocity,
            shared_vocab_score=p.shared_vocab_score,
            closeness_score=score,
            first_seen_at=p.first_seen_at,
        ))

    return sorted(result, key=lambda p: p.closeness_score, reverse=True)
