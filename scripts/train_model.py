from panoptibot.bot.config import Settings, load_settings
from panoptibot.ml.trainer import train_and_save_model


def main() -> None:
    settings: Settings = load_settings(
        require_discord_token=False, require_admin_channel=False, require_neo4j=False
    )
    model_path = train_and_save_model(settings)
    print(f"model_saved={model_path}")


if __name__ == "__main__":
    main()
