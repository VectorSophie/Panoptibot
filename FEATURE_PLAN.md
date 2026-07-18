# Panoptibot Feature Plan & QOL Improvements

## 🎯 High Priority - User Experience

### 1. Global ID Resolution System
**Problem**: Raw IDs shown everywhere (`@148086746346501328`, `#1234567890`)
**Solution**: Create a centralized resolver utility

**Files to update**:
- `panoptibot/bot/resolver.py` (NEW) - Centralized Discord ID → Name resolver
- `panoptibot/commands/summary.py` - Use resolver for user/channel names
- `panoptibot/commands/stats.py` - Use resolver for top users
- `panoptibot/commands/influence.py` - Use resolver for influence rankings
- `panoptibot/commands/emoji_culture.py` - Use resolver for emoji per user
- `panoptibot/commands/bonds.py` - Use resolver for relationship names
- `panoptibot/commands/catchup.py` - Already partially done, integrate with global system

**Benefits**:
- Consistent readable names across all commands
- Fallback to IDs if fetch fails
- Cache results to avoid repeated API calls

---

### 2. Rich Discord Embeds
**Problem**: Plain text responses are hard to read
**Solution**: Use Discord embeds with colors, fields, and formatting

**Files to update**:
- `panoptibot/bot/embeds.py` (NEW) - Embed builder utilities
- All command files - Replace text responses with embeds

**Example improvements**:
- `/summary` - Embed with message preview, author avatar, timestamps
- `/stats` - Embed with bar charts using Unicode blocks
- `/influence` - Embed with color-coded rankings (gold/silver/bronze)
- `/catchup me` - Embed with clean bullet formatting

---

### 3. Message Preview System
**Problem**: Links don't show what the message was about
**Solution**: Fetch and show message content preview

**Files to update**:
- `panoptibot/bot/message_preview.py` (NEW) - Fetch message content
- `panoptibot/commands/summary.py` - Show first 100 chars of message
- `panoptibot/commands/catchup.py` - Show message preview in bullets

**Format**:
```
• @Sophie said something in #general - "Hey everyone, check out..."
  https://discord.com/channels/...
```

---

## 🚀 Medium Priority - Features

### 4. Time-based Analytics
**Problem**: No way to see activity trends over time
**Solution**: Add time-based queries and visualizations

**New commands**:
- `/trends daily` - Activity over last 7 days
- `/trends weekly` - Activity over last 4 weeks
- `/trends hourly` - Most active hours of the day

**Implementation**:
- `panoptibot/graph/graph_queries.py` - Add time-bucketing queries
- `panoptibot/analytics/trends.py` (NEW) - Trend calculation logic
- `panoptibot/visualization/plots.py` - Line chart generation
- `panoptibot/commands/trends.py` (NEW) - Command handler

---

### 5. User Profile Command
**Problem**: No way for users to see their own stats
**Solution**: Add `/profile` command for self-service analytics

**Command**: `/profile [@user]`
**Shows**:
- Total messages sent
- Most active channels
- Top emojis used
- Most interactions with (top 5 users)
- Activity heatmap (day of week × hour)
- Join date and tenure

**Implementation**:
- `panoptibot/graph/graph_queries.py` - User stats queries
- `panoptibot/commands/profile.py` (NEW) - Command handler
- Use rich embeds with user's avatar and color

---

### 6. Search & Filter Commands
**Problem**: Hard to find specific past events
**Solution**: Add search capabilities

**New commands**:
- `/search user:@name keyword:"text" days:7` - Search messages
- `/search reactions:emoji days:30` - Find messages with specific reactions
- `/search from:@user to:@user` - Find conversations between users

**Implementation**:
- `panoptibot/graph/graph_queries.py` - Full-text search queries
- `panoptibot/commands/search.py` (NEW) - Command handler
- Pagination support for results

---

### 7. Notification/Alert System
**Problem**: No way to know when interesting things happen
**Solution**: Opt-in notifications for activity

**Features**:
- `/alerts subscribe mentions` - DM when mentioned while away
- `/alerts subscribe keywords "keyword1,keyword2"` - DM on keyword
- `/alerts subscribe user:@name` - DM when specific user is active
- `/alerts unsubscribe all`

**Implementation**:
- `panoptibot/alerts/` (NEW) - Alert system
- Store preferences in SQLite or JSON files
- Background task checks conditions and sends DMs

---

## 🔧 Medium Priority - Performance & Quality

### 8. Caching Layer
**Problem**: Repeated Discord API calls slow down commands
**Solution**: Add in-memory caching with TTL

**Implementation**:
- `panoptibot/bot/cache.py` (NEW) - LRU cache with TTL
- Cache user objects (5 min TTL)
- Cache channel objects (10 min TTL)
- Cache guild data (15 min TTL)

---

### 9. Pagination for Long Results
**Problem**: Commands like `/influence` truncate results
**Solution**: Add pagination with buttons

**Implementation**:
- `panoptibot/bot/pagination.py` (NEW) - Discord button pagination
- Apply to `/influence`, `/stats`, `/search`, `/emoji_culture`
- Show "◀️ Previous | Page 1/5 | Next ▶️"

---

### 10. Better Error Handling
**Problem**: Generic error messages don't help users
**Solution**: User-friendly error messages with suggestions

**Examples**:
- Neo4j down: "Database temporarily unavailable. Try again in a moment."
- Rate limited: "You're using commands too quickly. Please wait 30 seconds."
- No data: "No data found for the last 24 hours. Try increasing the lookback period."

**Implementation**:
- `panoptibot/bot/errors.py` (NEW) - Error message templates
- Update all command error handling

---

## 🎨 Low Priority - Polish

### 11. Command Aliases
**Problem**: Commands are verbose
**Solution**: Add shortcuts

**Examples**:
- `/s` → `/summary`
- `/i` → `/influence`
- `/c me` → `/catchup me`
- `/p @user` → `/profile @user`

---

### 12. Help Command Improvements
**Problem**: `/help` doesn't exist, users have to guess commands
**Solution**: Add comprehensive help

**Command**: `/help [command]`
- `/help` - List all commands with descriptions
- `/help summary` - Detailed help for specific command
- Show examples and parameters

---

### 13. Server Insights Dashboard
**Problem**: Admins want overview at a glance
**Solution**: `/dashboard` mega-command

**Shows**:
- Server health (Neo4j status, bot uptime, last error)
- Top stats (messages today, active users, trending emoji)
- Quick links to detailed commands
- System status (model loaded, copycat sessions active)

---

### 14. Export Data
**Problem**: No way to get raw data out
**Solution**: Add export commands (admin only)

**Commands**:
- `/export messages days:30` - Export JSONL
- `/export graph` - Export Neo4j relationships as CSV
- `/export analytics` - Export aggregated stats as JSON

---

### 15. Customizable Lookback Windows
**Problem**: Hardcoded 24h lookback in many commands
**Solution**: Add optional `days:` parameter

**Apply to**:
- `/summary days:3`
- `/catchup me days:7`
- `/stats days:14`
- `/influence days:30`

---

## 🧪 Experimental - Advanced Features

### 16. Sentiment Analysis
**Problem**: No insight into conversation tone
**Solution**: Classify message sentiment (positive/neutral/negative)

**Uses**:
- Show in `/profile` - User's average sentiment
- `/sentiment channel:#name` - Channel mood over time
- Alert if channel sentiment drops sharply

**Implementation**:
- Use lightweight local model or rule-based classifier
- Store sentiment score on Message nodes

---

### 17. Topic Detection
**Problem**: Hard to know what discussions happened
**Solution**: Extract topics from conversations

**Features**:
- `/topics days:7` - Top discussion topics
- `/topics channel:#name` - Topics in specific channel
- Cluster related messages

**Implementation**:
- Use TF-IDF or topic modeling
- Store in `logs/topics/`

---

### 18. Smart Summaries with LLM
**Problem**: `/summary` just ranks messages, doesn't summarize them
**Solution**: Use LM Studio to generate actual summaries

**Command**: `/summary smart days:1`
**Shows**: AI-generated prose summary of what happened

**Implementation**:
- Fetch top 20 messages
- Send to LM Studio with prompt
- Return 200-word summary

---

### 19. Automatic Roles Based on Activity
**Problem**: Manual role management is tedious
**Solution**: Suggest role assignments based on behavior

**Features**:
- `/roles suggest` - Show recommended role assignments
- Detect: Most Active, Helper (lots of replies), Emoji King, etc.
- Admin can approve/apply suggestions

---

### 20. Integration Webhooks
**Problem**: No way to connect external tools
**Solution**: Add webhook system

**Features**:
- `/webhook create url:https://... on:new_user`
- Trigger webhooks on events (new user, milestone messages, etc.)
- Send JSON payloads

---

## 📋 Implementation Priority

### Phase 1 (1-2 days): Core UX
1. Global ID Resolution System (#1)
2. Message Preview System (#3)
3. Better Error Handling (#10)

### Phase 2 (2-3 days): Polish
4. Rich Discord Embeds (#2)
5. Pagination (#9)
6. Caching Layer (#8)

### Phase 3 (3-5 days): New Features
7. User Profile Command (#5)
8. Time-based Analytics (#4)
9. Customizable Lookback Windows (#15)

### Phase 4 (Ongoing): Advanced
10. Search & Filter (#6)
11. Notification System (#7)
12. Smart Summaries (#18)

---

## 🎯 Quick Wins (Can do today)

1. **Catchup improvements** (Already planned)
2. **Add command aliases** - 30 min work
3. **Better error messages** - 1 hour
4. **Help command** - 1-2 hours
5. **Customizable lookback** - Add `days` parameter to existing commands - 1 hour

---

## Notes

- Keep LM Studio optional - all features should work without it
- Maintain backward compatibility with existing commands
- Test each feature thoroughly before deployment
- Update CLAUDE.md after adding new features
- Consider rate limiting on new expensive commands
