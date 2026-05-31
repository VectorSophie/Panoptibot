# Panoptibot Migration Guide

Covers upgrading from any prior version to the current codebase. If you are already on
the Copycat/Catch-Up iteration (`6a592f7`), skip to [Next-Phase changes](#next-phase-text-culture--bonds).

---

## What Changed

### Copycat / Catch-Up / Culture iteration

- New self-service commands: `/copycat`, `/catchup me`, `/culture memory/emoji/bridges`.
- Local Copycat data directory for profiles, sessions, opted-in style history, and audit logs.
- LM Studio integration via its OpenAI-compatible local server for Copycat auto-replies.
- Docker Compose deployment path with Neo4j and Panoptibot services.
- `uv run panoptibot-doctor` preflight check.

### Next-phase: Text Culture + Bonds

- Every incoming message is now tagged with a content archetype (`art_post`, `art_commentary`,
  `discussion`, `question`, `reaction`) and measured for tone proxies (`caps_ratio`,
  `punctuation_density`). These are stored on `Message` nodes in Neo4j.
- Phrase JSONL (`logs/phrases/`) accumulates word frequency for lore tracking and bond scoring.
- New commands: `/culture lore`, `/bonds`.
- Upgraded commands: `/culture memory` (adds content-type breakdown, tone note, trending phrase),
  `/influence` (adds archetype breakdown per user).
- New Neo4j field on `INTERACTED_WITH` edges: `first_seen_at` (set lazily on next interaction,
  `null` on existing edges — no migration required).
- New directories auto-created on startup: `bonds/` and `bonds/audit/`.

---

## 1. Back Up

Stop the bot before touching anything:

```bash
sudo systemctl stop panoptibot.service
# or, for Docker:
docker compose down
```

Snapshot runtime data:

```bash
sudo tar -czf ~/panoptibot-backup-$(date +%F).tar.gz /opt/panoptibot
```

If Neo4j is running outside Docker, export or snapshot its database using your normal method.

---

## 2. Pull and Sync

```bash
cd /opt/panoptibot
git pull
uv sync
```

Verify nothing is broken:

```bash
uv run python -m unittest discover -s tests
uv run python -m compileall panoptibot scripts
```

---

## 3. Update `.env`

Add any variables you have not already set. All variables below the `# NEW` comments are
additions from their respective iteration. Existing values should be kept as-is.

```env
# Core — required, already set
DISCORD_TOKEN=
NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=
ADMIN_CHANNEL_ID=
GUILD_ID=

# Paths — already set
PANOPTIBOT_HOME=/opt/panoptibot
LOGS_DIR=/opt/panoptibot/logs
MODELS_DIR=/opt/panoptibot/models
MODEL_PATH=/opt/panoptibot/models/panoptibot_ranker.cbm

# NEW (Copycat iteration)
COPYCAT_DIR=/opt/panoptibot/copycat
COPYCAT_DEFAULT_DURATION_MINUTES=120
COPYCAT_COOLDOWN_SECONDS=90
COPYCAT_HISTORY_RETENTION_DAYS=30
LM_STUDIO_BASE_URL=http://127.0.0.1:1234
LM_STUDIO_MODEL=local-model
LM_STUDIO_TIMEOUT_SECONDS=8
LM_STUDIO_MAX_TOKENS=80
LM_STUDIO_TEMPERATURE=0.4

# NEW (Next-phase iteration)
BONDS_DIR=/opt/panoptibot/bonds
BONDS_MIN_WEIGHT=5
```

`BONDS_MIN_WEIGHT` controls how many combined interactions a pair needs before appearing in
`/bonds`. Raise it on busier servers to filter weak ties.

---

## 4. Runtime Directories

For systemd deployments, create any directories that do not already exist:

```bash
sudo mkdir -p /opt/panoptibot/copycat
sudo mkdir -p /opt/panoptibot/logs /opt/panoptibot/models
sudo chown -R "$USER":"$USER" /opt/panoptibot/copycat /opt/panoptibot/logs /opt/panoptibot/models
```

`bonds/` and `logs/phrases/` are created automatically by the bot on startup — no manual step needed.

Run the preflight check:

```bash
uv run panoptibot-doctor
```

Expected: `logs_dir`, `models_dir`, and `copycat_dir` all marked `ok`.

---

## 5. LM Studio Setup

Copycat auto-replies and `/bonds` relationship labels both use a local LM Studio model.

1. Open LM Studio on the host machine.
2. Download and load the model you want to use.
3. Start the local server and enable the OpenAI-compatible API.
4. Confirm it is listening on `127.0.0.1:1234` (or update `LM_STUDIO_BASE_URL` in `.env`).
5. Set `LM_STUDIO_MODEL` to the model identifier LM Studio exposes.

If LM Studio is not running, Copycat falls back to a deterministic local reply and `/bonds`
renders the graph with `"unknown"` labels. Neither command hard-fails.

For Docker with LM Studio on the host desktop, use:

```env
LM_STUDIO_BASE_URL=http://host.docker.internal:1234
```

---

## 6. Deploy

### systemd

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

### Docker

```bash
docker compose up -d --build
docker compose exec panoptibot uv run panoptibot-doctor
docker compose exec panoptibot uv run panoptibot-init-db
```

Do not run the systemd bot and the Docker bot simultaneously with the same Discord token.

---

## 7. Slash Command Sync

Commands are synced automatically on startup. With `GUILD_ID` set, new commands appear in
the server within seconds of the bot reconnecting. Without it, global sync can take up to an
hour.

Confirm the bot is up with `/health` — if it responds, commands are live.

**Full current command list:**

| Command | Access |
|---|---|
| `/summary` | Admin + admin channel |
| `/stats` | Admin + admin channel |
| `/influence` | Admin + admin channel |
| `/emoji_culture` | Admin + admin channel |
| `/graph` | Admin + admin channel |
| `/bonds` | Admin + admin channel |
| `/health` | Admin + admin channel |
| `/debug` | Admin + admin channel |
| `/catchup me` | Any server member |
| `/copycat on/off/status` | Any server member |
| `/culture memory/emoji/bridges/lore` | Any server member |

---

## 8. First Discord Setup (Copycat)

From a normal member account:

```text
/copycat on duration:120 status_note:"away for a bit"
/copycat channel_add
/copycat history_enable retention_days:30
/copycat status
```

Copycat auto-replies only when the session is active, the channel was allowlisted with
`/copycat channel_add`, and someone mentions the owner. Replies are always visibly attributed
as Panoptibot speaking for an away user.

---

## 9. Cold-Start Notes

- **`/culture lore`** needs ~7 days of phrase data before results are meaningful. It returns
  "Not enough phrase data yet" until then — expected behaviour.
- **`/influence` archetype rows** only populate for messages received after the restart. Users
  with no new messages since the update will show no archetype breakdown.
- **`/bonds` arc notes** require `INTERACTED_WITH.first_seen_at` to be present on an edge,
  which happens only after each pair's next interaction post-update. Arc notes are silently
  skipped for pairs that have not interacted since the update.

---

## 10. Cleanup

Run manually or keep the systemd cleanup timer enabled:

```bash
uv run panoptibot-cleanup
```

Prunes JSONL logs (including `logs/phrases/`) older than `LOG_RETENTION_DAYS` and opted-in
Copycat history according to each user's retention setting.

---

## 11. Rollback

```bash
# systemd
sudo systemctl stop panoptibot.service
git log --oneline -5
git checkout <previous-commit>
uv sync
sudo systemctl start panoptibot.service

# Docker
docker compose down
git checkout <previous-commit>
docker compose up -d --build
```

All new Neo4j fields (`archetype`, `caps_ratio`, `punctuation_density`, `first_seen_at`) are
additive and silently ignored by older code. The `bonds/` and `logs/phrases/` directories are
also harmless to leave in place. No database changes need to be reversed.

To discard Copycat data entirely:

```bash
rm -rf /opt/panoptibot/copycat
```
