from panoptibot.bot.config import load_settings
from panoptibot.bot.doctor import check_writable_directory


def main() -> None:
    settings = load_settings(
        require_discord_token=False, require_admin_channel=False, require_neo4j=False
    )
    results = [
        check_writable_directory("logs_dir", settings.logs_dir),
        check_writable_directory("models_dir", settings.models_dir),
        check_writable_directory("copycat_dir", settings.copycat_dir),
    ]
    for result in results:
        print(f"{result.name}: {'ok' if result.ok else 'failed'} {result.detail}")
    if not all(result.ok for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
