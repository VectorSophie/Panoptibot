# Panoptibot

![Panoptibot Logo](public/logo.png)

Panoptibot is a self-hosted Discord analytics, culture analysis, and recommendation bot built for small communities. It focuses on deterministic local execution, JSONL event logging, Neo4j graph modeling, and classical machine-learning ranking with `CatBoostRanker`.

## Highlights

- Discord event tracking for messages, reactions, members, and approximate presence sessions
- Idempotent Neo4j graph persistence with retryable writes and schema initialization
- Admin-only slash commands with channel restriction and in-memory rate limiting
- Daily offline ranking model training with `CatBoostRanker`
- PNG visualizations for activity, emoji culture, and interaction graphs
- Local-only deployment using `uv`, `systemd`, and environment-based secrets

## Requirements

- Python 3.11+
- `uv`
- Local Neo4j instance

## Environment

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

Required variables:

- `DISCORD_TOKEN`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `ADMIN_CHANNEL_ID`

Optional (recommended during development):

- `GUILD_ID` (speeds up slash command registration in a specific server)

Optional:

- `PANOPTIBOT_HOME`
- `LOGS_DIR`
- `MODELS_DIR`
- `LOG_RETENTION_DAYS`
- `COMMAND_RATE_LIMIT_COUNT`
- `COMMAND_RATE_LIMIT_WINDOW`
- `SUMMARY_LOOKBACK_HOURS`
- `TRAINING_LOOKBACK_DAYS`
- `MODEL_PATH`

## Install

```bash
uv sync
```

## Initialize Neo4j Schema

```bash
uv run panoptibot-init-db
```

## Run the Bot

```bash
uv run panoptibot
```

## Train the Ranker

```bash
uv run panoptibot-train
```

The trained model is stored at `models/panoptibot_ranker.cbm` by default.

For long-running deployments, set `PANOPTIBOT_HOME=/opt/panoptibot` so logs and models are written to stable writable directories instead of depending on the import location.

## Cleanup Old Logs

```bash
uv run panoptibot-cleanup
```

This removes JSONL logs older than 30 days by default.

## Slash Commands

- `/summary` - ranked catch-up summary for missed messages and threads of interest
- `/stats` - activity stats, emoji culture distribution, and top users
- `/influence` - PageRank, centrality, and reply/reaction influence (monthly)
- `/emoji_culture` - emoji frequency, reaction network, trending emojis, emoji per user
- `/graph` - interaction graph PNG
- `/debug` - admin-only internal metrics

All slash commands are restricted to:

- users with Discord `administrator` permission
- the configured `ADMIN_CHANNEL_ID`

## Project Layout

```text
panoptibot/
  bot/
  events/
  commands/
  analytics/
  graph/
  ml/
  visualization/
scripts/
models/
logs/
deploy/
tests/
```

## Deployment With systemd

Copy the repo to `/opt/panoptibot`, create `.env`, then install the service file:

```bash
sudo cp deploy/panoptibot.service /etc/systemd/system/panoptibot.service
sudo systemctl daemon-reload
sudo systemctl enable --now panoptibot.service
sudo systemctl status panoptibot.service
```

Enable these privileged intents for the application in the Discord Developer Portal before first start:

- `MESSAGE CONTENT INTENT`
- `SERVER MEMBERS INTENT`
- `PRESENCE INTENT`

## Neo4j Notes

- Keep Neo4j bound to localhost or a private interface
- Do not expose Neo4j ports publicly
- If using DuckDNS, expose only the bot-facing web surface you explicitly add later; Panoptibot itself does not require inbound HTTP access

## Development Verification

```bash
python -m unittest discover -s tests
python -m compileall panoptibot scripts
```
