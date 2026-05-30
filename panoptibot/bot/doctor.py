from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DoctorResult:
    name: str
    ok: bool
    detail: str


def check_writable_directory(name: str, path: Path) -> DoctorResult:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".panoptibot-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return DoctorResult(name, False, str(exc))
    return DoctorResult(name, True, str(path))
