from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    discord_token: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    admin_channel_id: int
    guild_id: int | None
    project_root: Path
    logs_dir: Path
    models_dir: Path
    model_path: Path
    graph_name: str
    data_dir: Path
    log_retention_days: int
    command_rate_limit_count: int
    command_rate_limit_window: int
    summary_lookback_hours: int
    training_lookback_days: int
    session_idle_seconds: int


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _optional_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def load_settings(
    *,
    require_discord_token: bool = True,
    require_neo4j: bool = True,
    require_admin_channel: bool = True,
) -> Settings:
    load_dotenv()
    project_root = Path(__file__).resolve().parents[2]
    data_dir = (
        Path(os.getenv("PANOPTIBOT_HOME", str(project_root))).expanduser().resolve()
    )
    logs_dir = (
        Path(os.getenv("LOGS_DIR", str(data_dir / "logs"))).expanduser().resolve()
    )
    models_dir = (
        Path(os.getenv("MODELS_DIR", str(data_dir / "models"))).expanduser().resolve()
    )
    model_path_value = Path(
        os.getenv("MODEL_PATH", str(models_dir / "panoptibot_ranker.cbm"))
    ).expanduser()
    model_path = (
        model_path_value
        if model_path_value.is_absolute()
        else (data_dir / model_path_value).resolve()
    )

    settings = Settings(
        discord_token=_required("DISCORD_TOKEN")
        if require_discord_token
        else _optional("DISCORD_TOKEN"),
        neo4j_uri=_required("NEO4J_URI")
        if require_neo4j
        else _optional("NEO4J_URI", "bolt://127.0.0.1:7687"),
        neo4j_user=_required("NEO4J_USER")
        if require_neo4j
        else _optional("NEO4J_USER", "neo4j"),
        neo4j_password=_required("NEO4J_PASSWORD")
        if require_neo4j
        else _optional("NEO4J_PASSWORD"),
        admin_channel_id=int(_required("ADMIN_CHANNEL_ID"))
        if require_admin_channel
        else _optional_int("ADMIN_CHANNEL_ID", 0),
        guild_id=_optional_int("GUILD_ID", 0) or None,
        project_root=project_root,
        logs_dir=logs_dir,
        models_dir=models_dir,
        model_path=model_path,
        graph_name=os.getenv("GRAPH_NAME", "panoptibot"),
        data_dir=data_dir,
        log_retention_days=int(os.getenv("LOG_RETENTION_DAYS", "30")),
        command_rate_limit_count=int(os.getenv("COMMAND_RATE_LIMIT_COUNT", "4")),
        command_rate_limit_window=int(os.getenv("COMMAND_RATE_LIMIT_WINDOW", "60")),
        summary_lookback_hours=int(os.getenv("SUMMARY_LOOKBACK_HOURS", "24")),
        training_lookback_days=int(os.getenv("TRAINING_LOOKBACK_DAYS", "30")),
        session_idle_seconds=int(os.getenv("SESSION_IDLE_SECONDS", "3600")),
    )

    for directory in (
        settings.logs_dir / "events",
        settings.logs_dir / "errors",
        settings.logs_dir / "ml_feedback",
        settings.models_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    return settings
