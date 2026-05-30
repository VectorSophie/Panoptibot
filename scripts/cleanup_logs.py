from panoptibot.bot.config import load_settings
from panoptibot.bot.logger import cleanup_old_logs
from panoptibot.copycat.store import CopycatStore


def main() -> None:
    settings = load_settings(
        require_discord_token=False, require_admin_channel=False, require_neo4j=False
    )
    removed = cleanup_old_logs(settings.logs_dir, settings.log_retention_days)
    copycat_removed = CopycatStore(settings.copycat_dir).cleanup_history()
    print(f"removed_files={removed}")
    print(f"removed_copycat_history_records={copycat_removed}")


if __name__ == "__main__":
    main()
