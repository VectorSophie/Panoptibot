import asyncio

from panoptibot.bot.config import load_settings
from panoptibot.graph.neo4j_client import Neo4jClient


async def _main() -> None:
    settings = load_settings(
        require_discord_token=False, require_admin_channel=False, require_neo4j=True
    )
    client = Neo4jClient(settings)
    try:
        await client.ensure_schema()
        print("schema_initialized=true")
    finally:
        await client.close()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
