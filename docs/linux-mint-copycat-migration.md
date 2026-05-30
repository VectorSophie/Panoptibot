# Linux Mint Migration Guide: Copycat, Catch-Up, Culture Memory, And Guardrails

This guide upgrades an existing local Panoptibot server to the Copycat/Catch-Up/Culture Memory iteration. It assumes the server already has the repo, a Discord bot token, and Neo4j or systemd deployment experience.

## What Changes

- New self-service commands: `/copycat`, `/catchup`, and `/culture`.
- New local Copycat data directory for profiles, sessions, opted-in style history, and audit logs.
- New optional LM Studio integration through its OpenAI-compatible local server.
- New Docker Compose deployment path for Linux Mint with Neo4j and Panoptibot services.
- New doctor command: `uv run panoptibot-doctor`.
- Existing metadata-only event logging remains the default for users who have not opted into Copycat history.

## 1. Back Up The Current Server

Stop the current bot before changing deployment files:

```bash
sudo systemctl stop panoptibot.service
```

Back up the current working directory and runtime data:

```bash
sudo tar -czf ~/panoptibot-backup-$(date +%F).tar.gz /opt/panoptibot
```

If Neo4j is already running outside Docker, also export or snapshot its database using the method you normally use for that installation.

## 2. Pull The New Code

```bash
cd /opt/panoptibot
git pull
uv sync
```

Run the normal verification checks:

```bash
uv run python -m unittest discover -s tests
uv run python -m compileall panoptibot scripts
```

## 3. Update `.env`

Add these values to the existing `.env`:

```env
COPYCAT_DIR=/opt/panoptibot/copycat
COPYCAT_DEFAULT_DURATION_MINUTES=120
COPYCAT_COOLDOWN_SECONDS=90
COPYCAT_HISTORY_RETENTION_DAYS=30
LM_STUDIO_BASE_URL=http://127.0.0.1:1234
LM_STUDIO_MODEL=local-model
LM_STUDIO_TIMEOUT_SECONDS=8
LM_STUDIO_MAX_TOKENS=80
LM_STUDIO_TEMPERATURE=0.4
```

Keep the existing values for:

```env
DISCORD_TOKEN=
NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=
ADMIN_CHANNEL_ID=
GUILD_ID=
PANOPTIBOT_HOME=
LOGS_DIR=
MODELS_DIR=
MODEL_PATH=
```

## 4. Create Runtime Directories

For the existing systemd-style deployment:

```bash
sudo mkdir -p /opt/panoptibot/copycat
sudo mkdir -p /opt/panoptibot/logs /opt/panoptibot/models
sudo chown -R "$USER":"$USER" /opt/panoptibot/copycat /opt/panoptibot/logs /opt/panoptibot/models
```

Run the doctor check:

```bash
uv run panoptibot-doctor
```

Expected output should mark `logs_dir`, `models_dir`, and `copycat_dir` as `ok`.

## 5. LM Studio Setup

In LM Studio on the Linux Mint desktop:

1. Download/load the local chat model you want Panoptibot to use.
2. Start the local server.
3. Enable the OpenAI-compatible API.
4. Confirm it listens on `127.0.0.1:1234`.
5. Set `LM_STUDIO_MODEL` in `.env` to the model identifier LM Studio exposes.

If LM Studio is not running, Copycat falls back to a deterministic local response instead of blocking message handling.

## 6. Existing systemd Deployment

After `.env` and directories are ready:

```bash
uv run panoptibot-init-db
sudo systemctl daemon-reload
sudo systemctl start panoptibot.service
sudo systemctl status panoptibot.service
```

Check logs if the service fails:

```bash
journalctl -u panoptibot.service -n 100 --no-pager
```

## 7. Optional Docker Compose Deployment

Use this if you want Panoptibot and Neo4j isolated in Docker:

```bash
cd /opt/panoptibot
docker compose up -d --build
docker compose exec panoptibot uv run panoptibot-doctor
docker compose exec panoptibot uv run panoptibot-init-db
```

For Docker with LM Studio running on the host desktop, use:

```env
LM_STUDIO_BASE_URL=http://host.docker.internal:1234
```

Do not run the old systemd bot and the Docker bot at the same time with the same Discord token.

## 8. First Discord Setup Steps

Use a normal member account, not a bot account:

```text
/copycat on duration:120 status_note:"away for a bit"
/copycat channel_add
/copycat history_enable retention_days:30
/copycat status
```

Copycat only auto-replies when:

- Copycat is active for the mentioned user.
- The channel was allowlisted with `/copycat channel_add`.
- Someone mentions the Copycat owner.
- The message is not authored by a bot.

Replies are always visibly attributed as Panoptibot speaking for an away user.

## 9. Catch-Up And Culture Commands

Try:

```text
/catchup me
/culture memory
/culture emoji
/culture bridges
```

`/catchup me` returns social bullet points backed by message links. `/culture` commands describe observed graph and emoji patterns without treating guesses as facts.

## 10. Cleanup And Retention

Run manually:

```bash
uv run panoptibot-cleanup
```

For systemd deployments, keep the existing cleanup timer enabled. Cleanup now prunes both old JSONL logs and opted-in Copycat history records according to profile retention settings.

## 11. Rollback

If the new iteration misbehaves:

```bash
sudo systemctl stop panoptibot.service
git log --oneline -5
git checkout <previous-good-commit>
uv sync
sudo systemctl start panoptibot.service
```

If using Docker:

```bash
docker compose down
git checkout <previous-good-commit>
docker compose up -d --build
```

The Copycat directory can be preserved for later inspection or removed if you want to discard sessions/history:

```bash
rm -rf /opt/panoptibot/copycat
```

