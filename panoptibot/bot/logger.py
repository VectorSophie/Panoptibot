from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import json

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None


def _serialize(record: dict[str, object]) -> bytes:
    if orjson is not None:
        return orjson.dumps(record)
    return json.dumps(record, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


@dataclass(slots=True)
class JsonlLogger:
    service_name: str
    base_dir: Path

    def _write(self, category: str, record: dict[str, object]) -> None:
        day_stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        target = self.base_dir / category / f"{day_stamp}.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        line = _serialize(record) + b"\n"
        with target.open("ab") as handle:
            handle.write(line)

    def event(self, event_name: str, payload: dict[str, object]) -> None:
        record = {
            "service": self.service_name,
            "event": event_name,
            **payload,
        }
        self._write("events", record)

    def error(self, event_name: str, payload: dict[str, object]) -> None:
        record = {
            "service": self.service_name,
            "event": event_name,
            **payload,
        }
        self._write("errors", record)

    def ml_feedback(self, payload: dict[str, object]) -> None:
        record = {
            "service": self.service_name,
            "event": "ml_feedback",
            **payload,
        }
        self._write("ml_feedback", record)


def cleanup_old_logs(logs_dir: Path, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    removed = 0
    for path in logs_dir.rglob("*.jsonl"):
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        if modified < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed
