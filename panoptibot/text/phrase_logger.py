from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None


def _serialize(record: dict) -> bytes:  # type: ignore[type-arg]
    if orjson is not None:
        return orjson.dumps(record)
    return json.dumps(record, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class PhraseLogger:
    def __init__(self, phrases_dir: Path) -> None:
        self._phrases_dir = phrases_dir
        phrases_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        *,
        user_id: str,
        channel_id: str,
        message_id: str,
        terms: list[str],
        timestamp: str,
    ) -> None:
        if not terms:
            return
        day_stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        target = self._phrases_dir / f"{day_stamp}.jsonl"
        record = {
            "timestamp": timestamp,
            "user_id": user_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "terms": terms,
        }
        line = _serialize(record) + b"\n"
        with target.open("ab") as handle:
            handle.write(line)
