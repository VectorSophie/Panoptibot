from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
import traceback

import discord

from panoptibot.bot.config import load_settings
from panoptibot.bot.context import ServiceContainer
from panoptibot.bot.logger import JsonlLogger, cleanup_old_logs
from panoptibot.bot.rate_limit import SlidingWindowRateLimiter
from panoptibot.bot.session_tracker import SessionTracker
from panoptibot.commands import debug as debug_command
from panoptibot.commands import emoji_culture as emoji_culture_command
from panoptibot.commands import graph as graph_command
from panoptibot.commands import health as health_command
from panoptibot.commands import influence as influence_command
from panoptibot.commands import stats as stats_command
from panoptibot.commands import summary as summary_command
from panoptibot.commands import catchup as catchup_command
from panoptibot.commands import copycat as copycat_command
from panoptibot.commands import culture as culture_command
from panoptibot.events.member_events import (
    handle_member_join,
    handle_member_remove,
    handle_presence_update,
)
from panoptibot.events.message_events import (
    handle_message_create,
    handle_message_delete,
    handle_message_edit,
    handle_raw_message_delete,
)
from panoptibot.events.reaction_events import (
    handle_reaction_add,
    handle_reaction_remove,
)
from panoptibot.graph.neo4j_client import Neo4jClient
from panoptibot.copycat.store import CopycatStore
from panoptibot.ml.recommender import MessageRecommender
from panoptibot.ml.trainer import train_and_save_model


class PanoptibotClient(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        intents.reactions = True
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        settings = load_settings()
        logger = JsonlLogger(service_name="panoptibot", base_dir=settings.logs_dir)
        self.services = ServiceContainer(
            settings=settings,
            logger=logger,
            graph=Neo4jClient(settings),
            recommender=MessageRecommender(settings),
            rate_limiter=SlidingWindowRateLimiter(
                limit=settings.command_rate_limit_count,
                window_seconds=settings.command_rate_limit_window,
            ),
            session_tracker=SessionTracker(idle_seconds=settings.session_idle_seconds),
            copycat_store=CopycatStore(settings.copycat_dir),
        )
        self._periodic_task: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        await self.services.graph.ensure_schema()
        summary_command.register(self.tree, self.services)
        stats_command.register(self.tree, self.services)
        influence_command.register(self.tree, self.services)
        emoji_culture_command.register(self.tree, self.services)
        copycat_command.register(self.tree, self.services)
        catchup_command.register(self.tree, self.services)
        culture_command.register(self.tree, self.services)
        graph_command.register(self.tree, self.services)
        health_command.register(self.tree, self.services)
        debug_command.register(self.tree, self.services)
        if self.services.settings.guild_id is not None:
            guild = discord.Object(id=self.services.settings.guild_id)
            existing_commands = list(self.tree.get_commands())
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            for command in existing_commands:
                self.tree.add_command(command)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        self._periodic_task = asyncio.create_task(self._run_periodic_jobs())

    async def close(self) -> None:
        if self._periodic_task is not None:
            self._periodic_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._periodic_task
        await self.services.graph.close()
        await super().close()

    async def on_ready(self) -> None:
        self.services.logger.event(
            "bot_ready",
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "user_id": str(self.user.id if self.user else ""),
                "channel_id": "",
                "message_id": "",
                "content_length": 0,
                "emoji_list": [],
                "sticker_list": [],
                "attachment_metadata": [],
            },
        )

    async def on_message(self, message: discord.Message) -> None:
        await handle_message_create(message, self.services)

    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        await handle_message_edit(before, after, self.services)

    async def on_message_delete(self, message: discord.Message) -> None:
        await handle_message_delete(message, self.services)

    async def on_raw_message_delete(
        self, payload: discord.RawMessageDeleteEvent
    ) -> None:
        await handle_raw_message_delete(payload, self.services)

    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.abc.User
    ) -> None:
        await handle_reaction_add(reaction, user, self.services)

    async def on_reaction_remove(
        self, reaction: discord.Reaction, user: discord.abc.User
    ) -> None:
        await handle_reaction_remove(reaction, user, self.services)

    async def on_member_join(self, member: discord.Member) -> None:
        await handle_member_join(member, self.services)

    async def on_member_remove(self, member: discord.Member) -> None:
        await handle_member_remove(member, self.services)

    async def on_presence_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        await handle_presence_update(before, after, self.services)

    async def on_error(
        self, event_method: str, *args: object, **kwargs: object
    ) -> None:
        self.services.logger.error(
            "discord_event_error",
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "event_method": event_method,
                "args_count": len(args),
                "kwargs_keys": sorted(kwargs.keys()),
                "traceback": traceback.format_exc(),
            },
        )

    async def _run_periodic_jobs(self) -> None:
        while True:
            await asyncio.sleep(24 * 60 * 60)
            cleanup_old_logs(
                self.services.settings.logs_dir,
                self.services.settings.log_retention_days,
            )
            try:
                await asyncio.to_thread(train_and_save_model, self.services.settings)
                self.services.recommender.reload()
            except Exception as exc:  # pragma: no cover
                self.services.logger.error(
                    "daily_training_failed",
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )


def run() -> None:
    client = PanoptibotClient()
    client.run(client.services.settings.discord_token, log_handler=None)


if __name__ == "__main__":
    run()
