from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Any, LiteralString, cast

from neo4j import (
    GraphDatabase,
    NotificationDisabledClassification,
    NotificationMinimumSeverity,
    Query,
)
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from panoptibot.bot.config import Settings
from panoptibot.graph import graph_queries


RetryableErrors = (ServiceUnavailable, SessionExpired)


class Neo4jClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            warn_notification_severity=NotificationMinimumSeverity.OFF,
        )

    async def close(self) -> None:
        await asyncio.to_thread(self.driver.close)

    async def ensure_schema(self) -> None:
        statements = [
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (m:Message) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT channel_id_unique IF NOT EXISTS FOR (c:Channel) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE",
            "CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.id)",
            "CREATE INDEX message_id_index IF NOT EXISTS FOR (m:Message) ON (m.id)",
            "CREATE INDEX channel_id_index IF NOT EXISTS FOR (c:Channel) ON (c.id)",
        ]
        for statement in statements:
            await self._execute_write(lambda tx, stmt=statement: tx.run(stmt).consume())

    async def upsert_message(self, payload: dict[str, Any]) -> None:
        def _query(tx: Any) -> None:
            tx.run(
                """
                MERGE (u:User {id: $user_id})
                MERGE (c:Channel {id: $channel_id})
                MERGE (s:Session {id: $session_id})
                  ON CREATE SET s.started_at = $timestamp
                SET s.last_seen_at = $timestamp
                MERGE (m:Message {id: $message_id})
                  ON CREATE SET m.created_at = $timestamp
                SET m.content_length = $content_length,
                    m.emoji_list = $emoji_list,
                    m.emoji_count = size($emoji_list),
                    m.sticker_list = $sticker_list,
                    m.sticker_present = size($sticker_list) > 0,
                    m.attachment_metadata = $attachment_metadata,
                    m.attachment_present = $attachment_present,
                    m.mention_ids = $mention_ids,
                    m.deleted = coalesce(m.deleted, false),
                    m.updated_at = $timestamp
                MERGE (u)-[:SENT]->(m)
                MERGE (m)-[:IN_CHANNEL]->(c)
                MERGE (u)-[:ACTIVE_IN]->(s)
                """,
                **payload,
            ).consume()
            if payload.get("reply_to_message_id"):
                tx.run(
                    """
                    MATCH (m:Message {id: $message_id})
                    MERGE (target:Message {id: $reply_to_message_id})
                    MERGE (m)-[:REPLIED_TO]->(target)
                    """,
                    message_id=payload["message_id"],
                    reply_to_message_id=payload["reply_to_message_id"],
                ).consume()
                self._sync_interaction(
                    tx,
                    payload["user_id"],
                    self._lookup_message_author(
                        tx, str(payload["reply_to_message_id"])
                    ),
                    payload["timestamp"],
                )
            for mentioned_user_id in payload.get("mention_ids", []):
                tx.run(
                    """
                    MATCH (m:Message {id: $message_id})
                    MERGE (u:User {id: $mentioned_user_id})
                    MERGE (m)-[:MENTIONED]->(u)
                    """,
                    message_id=payload["message_id"],
                    mentioned_user_id=str(mentioned_user_id),
                ).consume()
                self._sync_interaction(
                    tx,
                    payload["user_id"],
                    str(mentioned_user_id),
                    payload["timestamp"],
                )

        await self._execute_write(_query)

    async def mark_message_deleted(self, message_id: int, timestamp: str) -> None:
        await self._execute_write(
            lambda tx: tx.run(
                "MATCH (m:Message {id: $message_id}) SET m.deleted = true, m.deleted_at = $timestamp",
                message_id=str(message_id),
                timestamp=timestamp,
            ).consume()
        )

    async def upsert_reaction(self, payload: dict[str, Any], removed: bool) -> None:
        def _query(tx: Any) -> None:
            tx.run(
                """
                MERGE (u:User {id: $user_id})
                MERGE (s:Session {id: $session_id})
                  ON CREATE SET s.started_at = $timestamp
                SET s.last_seen_at = $timestamp
                MERGE (m:Message {id: $message_id})
                MERGE (u)-[:ACTIVE_IN]->(s)
                MERGE (u)-[r:REACTED_TO]->(m)
                SET r.last_seen_at = $timestamp,
                    r.emoji = coalesce($emoji_list[0], ''),
                    r.removed_at = CASE WHEN $removed THEN $timestamp ELSE NULL END
                """,
                removed=removed,
                **payload,
            ).consume()
            self._sync_interaction(
                tx,
                payload["user_id"],
                self._lookup_message_author(tx, str(payload["message_id"])),
                payload["timestamp"],
            )

        await self._execute_write(_query)

    async def upsert_member_event(
        self, user_id: int, event_name: str, timestamp: str
    ) -> None:
        await self._execute_write(
            lambda tx: tx.run(
                "MERGE (u:User {id: $user_id}) SET u.last_member_event = $event_name, u.last_member_event_at = $timestamp",
                user_id=str(user_id),
                event_name=event_name,
                timestamp=timestamp,
            ).consume()
        )

    async def upsert_session_state(
        self,
        user_id: int,
        session_id: str,
        status: str,
        started_at: str,
        last_seen_at: str,
    ) -> None:
        await self._execute_write(
            lambda tx: tx.run(
                """
                MERGE (u:User {id: $user_id})
                MERGE (s:Session {id: $session_id})
                SET s.status = $status,
                    s.started_at = coalesce(s.started_at, $started_at),
                    s.last_seen_at = $last_seen_at
                MERGE (u)-[:ACTIVE_IN]->(s)
                """,
                user_id=str(user_id),
                session_id=session_id,
                status=status,
                started_at=started_at,
                last_seen_at=last_seen_at,
            ).consume()
        )

    async def fetch_summary_candidates(
        self, user_id: int, lookback_hours: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        return await self._execute_read(
            graph_queries.SUMMARY_CANDIDATES_QUERY,
            user_id=str(user_id),
            cutoff=graph_queries.recent_cutoff(lookback_hours),
            limit=limit,
        )

    async def fetch_activity_stats(self, lookback_days: int) -> dict[str, Any]:
        rows = await self._execute_read(
            graph_queries.ACTIVITY_STATS_QUERY,
            cutoff=(datetime.now(UTC) - timedelta(days=lookback_days)).isoformat(),
        )
        return (
            rows[0]
            if rows
            else {"total_messages": 0, "active_users": 0, "total_content_length": 0}
        )

    async def fetch_top_users(
        self, lookback_days: int, limit: int = 5
    ) -> list[dict[str, Any]]:
        return await self._execute_read(
            graph_queries.TOP_USERS_QUERY,
            cutoff=(datetime.now(UTC) - timedelta(days=lookback_days)).isoformat(),
            limit=limit,
        )

    async def fetch_emoji_counts(
        self, lookback_days: int, limit: int = 10
    ) -> list[dict[str, Any]]:
        return await self._execute_read(
            graph_queries.EMOJI_COUNTS_QUERY,
            cutoff=(datetime.now(UTC) - timedelta(days=lookback_days)).isoformat(),
            limit=limit,
        )

    async def fetch_interaction_edges(
        self, lookback_days: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        return await self._execute_read(
            graph_queries.INTERACTION_GRAPH_QUERY,
            cutoff=(datetime.now(UTC) - timedelta(days=lookback_days)).isoformat(),
            limit=limit,
        )

    async def fetch_reaction_edges(
        self, lookback_days: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        return await self._execute_read(
            graph_queries.REACTION_NETWORK_QUERY,
            cutoff=(datetime.now(UTC) - timedelta(days=lookback_days)).isoformat(),
            limit=limit,
        )

    async def fetch_reply_influence(
        self, lookback_days: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        return await self._execute_read(
            graph_queries.REPLY_INFLUENCE_QUERY,
            cutoff=(datetime.now(UTC) - timedelta(days=lookback_days)).isoformat(),
            limit=limit,
        )

    async def fetch_reaction_influence(
        self, lookback_days: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        return await self._execute_read(
            graph_queries.REACTION_INFLUENCE_QUERY,
            cutoff=(datetime.now(UTC) - timedelta(days=lookback_days)).isoformat(),
            limit=limit,
        )

    async def fetch_emoji_per_user(
        self, lookback_days: int, limit: int = 20, per_user: int = 3
    ) -> list[dict[str, Any]]:
        return await self._execute_read(
            graph_queries.EMOJI_PER_USER_QUERY,
            cutoff=(datetime.now(UTC) - timedelta(days=lookback_days)).isoformat(),
            limit=limit,
            per_user=per_user,
        )

    async def check_connection(self) -> bool:
        try:
            rows = await self._execute_read("RETURN 1 AS ok")
        except Exception:
            return False
        if not rows:
            return False
        return rows[0].get("ok") == 1

    async def _execute_read(
        self, query: str, **parameters: Any
    ) -> list[dict[str, Any]]:
        def _runner() -> list[dict[str, Any]]:
            with self.driver.session(
                database=None,
                notifications_disabled_classifications={
                    NotificationDisabledClassification.UNRECOGNIZED
                },
            ) as session:
                result = session.run(Query(cast(LiteralString, query)), **parameters)
                return [record.data() for record in result]

        return await asyncio.to_thread(_runner)

    def _lookup_message_author(self, tx: Any, message_id: str) -> str | None:
        record = tx.run(
            """
            MATCH (author:User)-[:SENT]->(:Message {id: $message_id})
            RETURN author.id AS author_id
            LIMIT 1
            """,
            message_id=message_id,
        ).single()
        if record is None:
            return None
        author_id = record.get("author_id")
        return str(author_id) if author_id is not None else None

    def _sync_interaction(
        self,
        tx: Any,
        source_user_id: str,
        target_user_id: str | None,
        timestamp: str,
    ) -> None:
        if target_user_id is None or source_user_id == target_user_id:
            return
        tx.run(
            """
            MATCH (source:User {id: $source_user_id})
            MATCH (target:User {id: $target_user_id})
            OPTIONAL MATCH (source)-[:SENT]->(reply_message:Message)-[:REPLIED_TO]->(:Message)<-[:SENT]-(target)
            WITH source, target, count(DISTINCT reply_message) AS reply_count
            OPTIONAL MATCH (source)-[reaction:REACTED_TO]->(:Message)<-[:SENT]-(target)
            WHERE reaction.removed_at IS NULL
            WITH source, target, reply_count, count(DISTINCT reaction) AS reaction_count
            OPTIONAL MATCH (source)-[:SENT]->(mention_message:Message)-[:MENTIONED]->(target)
            WITH source, target, reply_count, reaction_count, count(DISTINCT mention_message) AS mention_count
            WITH source, target, reply_count + reaction_count + mention_count AS total_weight
            OPTIONAL MATCH (source)-[existing:INTERACTED_WITH]->(target)
            FOREACH (_ IN CASE WHEN total_weight = 0 AND existing IS NOT NULL THEN [1] ELSE [] END |
              DELETE existing
            )
            FOREACH (_ IN CASE WHEN total_weight > 0 THEN [1] ELSE [] END |
              MERGE (source)-[rel:INTERACTED_WITH]->(target)
              SET rel.weight = total_weight,
                  rel.last_seen_at = $timestamp
            )
            """,
            source_user_id=source_user_id,
            target_user_id=target_user_id,
            timestamp=timestamp,
        ).consume()

    async def _execute_write(self, callback: Callable[[Any], Any]) -> None:
        def _runner() -> None:
            delay = 0.5
            for attempt in range(3):
                try:
                    with self.driver.session(
                        database=None,
                        notifications_disabled_classifications={
                            NotificationDisabledClassification.UNRECOGNIZED
                        },
                    ) as session:
                        session.execute_write(callback)
                    return
                except RetryableErrors:
                    if attempt == 2:
                        raise
                    sleep(delay)
                    delay *= 2
                except Neo4jError as exc:
                    if not exc.is_retryable() or attempt == 2:
                        raise
                    sleep(delay)
                    delay *= 2

        await asyncio.to_thread(_runner)
