# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                          # install dependencies
uv run panoptibot                # run the bot
uv run panoptibot-init-db        # initialize Neo4j schema (run once before first start)
uv run panoptibot-train          # train the CatBoost ranker model
uv run panoptibot-cleanup        # prune old JSONL logs and Copycat history
uv run panoptibot-doctor         # verify directories and config before deployment

# tests and compile checks
python -m unittest discover -s tests
python -m unittest tests/test_rate_limit.py   # single test file
python -m compileall panoptibot scripts
```

The project uses `uv` as the package manager. All entry points are defined in `pyproject.toml` under `[project.scripts]`.

## Architecture

**Data flow:** Discord events → event handlers (`panoptibot/events/`) → `Neo4jClient` (graph writes) + `JsonlLogger` (JSONL append) → slash commands query Neo4j, run ML ranking, return ephemeral Discord replies.

**ServiceContainer** (`panoptibot/bot/context.py`) is the single dependency injection object passed to every command and event handler. It holds: `Settings`, `JsonlLogger`, `Neo4jClient`, `MessageRecommender`, `SlidingWindowRateLimiter`, `SessionTracker`, and `CopycatStore`.

**Settings** (`panoptibot/bot/config.py`) reads all configuration from environment variables via `.env`. `PANOPTIBOT_HOME` controls where logs, models, and Copycat data are written (defaults to project root).

### Key subsystems

- **Graph** (`panoptibot/graph/`): `Neo4jClient` wraps the Neo4j bolt driver with async-to-thread execution and retryable writes. All Cypher queries are in `graph_queries.py`. The graph models: `User`, `Message`, `Channel`, `Session` nodes; `SENT`, `REPLIED_TO`, `REACTED_TO`, `INTERACTED_WITH`, `IN_CHANNEL`, `ACTIVE_IN` relationships.

- **ML** (`panoptibot/ml/`): `CatBoostRanker` trained daily on JSONL `ml_feedback` logs. Feature vector is 21 named features defined in `feature_engineering.py`. `MessageRecommender` loads the `.cbm` model file and scores candidates for `/summary`.

- **Copycat** (`panoptibot/copycat/`): Away-proxy feature. `CopycatStore` persists per-user sessions and profiles as JSON files. `lm_studio.py` calls a local LM Studio OpenAI-compatible endpoint. `core.py` contains guardrails (blocked text markers, `never_say` list, `refusal_mode`). All LLM decisions are audit-logged via `store.audit_reply()`.

- **Logging** (`panoptibot/bot/logger.py`): `JsonlLogger` appends to daily JSONL files under `logs/events/`, `logs/errors/`, and `logs/ml_feedback/`. Uses `orjson` when available.

- **Security** (`panoptibot/bot/security.py`): `enforce_command_access` gates analytics/admin commands to users with Discord `administrator` permission inside `ADMIN_CHANNEL_ID`. `enforce_user_command_access` gates self-service commands (Copycat, catchup) to non-bot server members. Both functions check the sliding-window rate limiter.

### Text extraction (`panoptibot/text/`)

- `extractor.py` — pure functions: `classify_archetype(content, has_attachment)` → one of `art_post / art_commentary / discussion / question / reaction`; `caps_ratio(content)`; `punctuation_density(content)`; `extract_terms(content)` → tokens + bigrams with stop-word filtering and Discord markup stripping. Called on every inbound message.
- `phrase_logger.py` — `PhraseLogger` appends term lists to `logs/phrases/YYYY-MM-DD.jsonl`. Wired into `ServiceContainer` and called from `message_events.py`. The existing `cleanup_old_logs` recurse covers this directory automatically.

### Adding a new slash command

1. Create `panoptibot/commands/my_command.py` with a `register(tree, services)` function.
2. Import and call `register` inside `PanoptibotClient.setup_hook()` in `panoptibot/bot/main.py`.
3. Use `enforce_command_access` (admin) or `enforce_user_command_access` (member) at the top of the handler.

## Environment

Required: `DISCORD_TOKEN`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `ADMIN_CHANNEL_ID`.

Set `GUILD_ID` during development to speed up slash command registration to a single server.

Copycat LLM calls go to `LM_STUDIO_BASE_URL` (default `http://127.0.0.1:1234`). In Docker, set `LM_STUDIO_BASE_URL=http://host.docker.internal:1234` to reach a host-side LM Studio instance.

## Required Discord intents

`MESSAGE CONTENT`, `SERVER MEMBERS`, and `PRESENCE` privileged intents must be enabled in the Discord Developer Portal before first start.
