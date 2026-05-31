from __future__ import annotations

from dataclasses import dataclass

from panoptibot.bot.config import Settings
from panoptibot.bot.logger import JsonlLogger
from panoptibot.bot.rate_limit import SlidingWindowRateLimiter
from panoptibot.bot.session_tracker import SessionTracker
from panoptibot.copycat.store import CopycatStore
from panoptibot.graph.neo4j_client import Neo4jClient
from panoptibot.ml.recommender import MessageRecommender
from panoptibot.text.phrase_logger import PhraseLogger


@dataclass(slots=True)
class ServiceContainer:
    settings: Settings
    logger: JsonlLogger
    graph: Neo4jClient
    recommender: MessageRecommender
    rate_limiter: SlidingWindowRateLimiter
    session_tracker: SessionTracker
    copycat_store: CopycatStore
    phrase_logger: PhraseLogger
