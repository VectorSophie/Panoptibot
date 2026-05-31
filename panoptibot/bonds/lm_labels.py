from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from panoptibot.bonds.scorer import BondPair
from panoptibot.copycat.lm_studio import generate_lm_studio_reply

if TYPE_CHECKING:
    from panoptibot.bot.config import Settings


_LABEL_SYSTEM = (
    "You label relationships in a small Discord server of friends who play Limbus Company. "
    "Respond with ONLY a short label of five words or fewer. No punctuation. No explanation. "
    "Examples: art mutual, hype partners, lore debate duo, one-sided appreciation, "
    "warm but drifting, cordial lurkers, co-conspirators, quiet fans, theory partners."
)

_SHARED_SYSTEM = (
    "You write one casual sentence about shared vocabulary between two Discord friends. "
    "Respond with ONLY one sentence. No greeting. No explanation."
)

_ARC_SYSTEM = (
    "You write one casual sentence about how a Discord friendship has evolved over time. "
    "Respond with ONLY one sentence. No greeting. No explanation."
)


def _label_prompt(pair: BondPair, name_a: str, name_b: str, shared_terms: list[str]) -> str:
    lines = [
        f"{name_a} → {name_b}: {int(pair.weight_a_to_b)} interactions",
        f"{name_b} → {name_a}: {int(pair.weight_b_to_a)} interactions",
        f"Reciprocity score: {pair.reciprocity:.2f} (1.0 = perfectly mutual, 0.0 = one-sided)",
    ]
    if shared_terms:
        lines.append(f"Shared vocabulary: {', '.join(shared_terms[:3])}")
    return "\n".join(lines)


def generate_bond_label(
    *,
    settings: Settings,
    pair: BondPair,
    name_a: str,
    name_b: str,
    shared_terms: list[str],
) -> tuple[str, str, str]:
    """Returns (label, shared_note, arc_note). Each falls back gracefully on timeout."""
    label = "unknown"
    shared_note = ""
    arc_note = ""

    try:
        label = generate_lm_studio_reply(
            base_url=settings.lm_studio_base_url,
            model=settings.lm_studio_model,
            system_prompt=_LABEL_SYSTEM,
            user_prompt=_label_prompt(pair, name_a, name_b, shared_terms),
            max_tokens=12,
            temperature=settings.lm_studio_temperature,
            timeout_seconds=settings.lm_studio_timeout_seconds,
        ).strip().strip('"').lower()
    except Exception:
        pass

    if shared_terms:
        try:
            shared_note = generate_lm_studio_reply(
                base_url=settings.lm_studio_base_url,
                model=settings.lm_studio_model,
                system_prompt=_SHARED_SYSTEM,
                user_prompt=f"{name_a} and {name_b} both frequently use: {', '.join(shared_terms)}",
                max_tokens=40,
                temperature=settings.lm_studio_temperature,
                timeout_seconds=settings.lm_studio_timeout_seconds,
            ).strip()
        except Exception:
            pass

    if pair.first_seen_at:
        try:
            first = datetime.fromisoformat(pair.first_seen_at).astimezone(UTC)
            if datetime.now(UTC) - first >= timedelta(days=60):
                arc_note = generate_lm_studio_reply(
                    base_url=settings.lm_studio_base_url,
                    model=settings.lm_studio_model,
                    system_prompt=_ARC_SYSTEM,
                    user_prompt=(
                        f"{name_a} and {name_b} first interacted around {first.strftime('%B %Y')}. "
                        f"Current closeness score: {pair.closeness_score:.2f}."
                    ),
                    max_tokens=40,
                    temperature=settings.lm_studio_temperature,
                    timeout_seconds=settings.lm_studio_timeout_seconds,
                ).strip()
        except Exception:
            pass

    return label, shared_note, arc_note


def audit_bond_label(
    *,
    bonds_dir: Path,
    user_a: str,
    user_b: str,
    label: str,
    shared_note: str,
    arc_note: str,
    model_name: str,
    timestamp: datetime | None = None,
) -> None:
    ts = timestamp or datetime.now(UTC)
    record = {
        "timestamp": ts.isoformat(),
        "event": "bond_label",
        "user_a": user_a,
        "user_b": user_b,
        "label": label,
        "shared_note_hash": "sha256:" + hashlib.sha256(shared_note.encode()).hexdigest() if shared_note else "",
        "arc_note_hash": "sha256:" + hashlib.sha256(arc_note.encode()).hexdigest() if arc_note else "",
        "model_name": model_name,
    }
    day_stamp = ts.strftime("%Y-%m-%d")
    with (bonds_dir / "audit" / f"{day_stamp}.jsonl").open("ab") as handle:
        handle.write(json.dumps(record, ensure_ascii=True).encode("utf-8") + b"\n")
