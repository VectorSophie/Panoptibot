from __future__ import annotations

import discord
from discord import app_commands

from panoptibot.bot.context import ServiceContainer


def register(
    tree: app_commands.CommandTree[discord.Client], services: ServiceContainer
) -> None:
    @tree.command(name="help", description="Show available commands and usage info.")
    @app_commands.describe(command="Specific command to get help for (optional)")
    async def help_command(
        interaction: discord.Interaction, command: str | None = None
    ) -> None:
        if command:
            # Detailed help for specific command
            help_text = _get_command_help(command)
            if help_text:
                await interaction.response.send_message(help_text, ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Command `{command}` not found. Use `/help` to see all commands.",
                    ephemeral=True,
                )
        else:
            # List all commands
            await interaction.response.send_message(_get_all_commands(), ephemeral=True)


def _get_all_commands() -> str:
    """Return list of all available commands."""
    admin_commands = """**Admin Commands** (require admin permission + admin channel):
• `/summary [days:1-30]` - Ranked catch-up messages
• `/stats [days:1-90]` - Server activity statistics
• `/influence [days:1-90]` - User influence rankings
• `/emoji_culture` - Emoji usage and culture analysis
• `/graph` - Interaction network visualization
• `/bonds` - User relationship graph with AI labels
• `/health` - Bot and system health check
• `/debug` - Internal metrics (admin only)

**Command Aliases**:
• `/s` = `/summary`
• `/i` = `/influence`"""

    user_commands = """
**User Commands** (available to all members):
• `/catchup me [days:1-30]` - Personalized catch-up bullets
• `/copycat on/off/status` - Away-mode auto-reply system
• `/culture memory/emoji/bridges/lore` - Server culture insights
• `/profile [@user]` - User statistics and activity
• `/help [command]` - This help message

**Tips**:
- Most commands have a `days:` parameter to adjust lookback window
- Use `/help <command>` for detailed info (e.g., `/help summary`)
- All responses are ephemeral (only you can see them)
"""

    return admin_commands + user_commands


def _get_command_help(command: str) -> str | None:
    """Return detailed help for a specific command."""
    help_docs = {
        "summary": """**`/summary [days:1-30]`**
Ranks the most important missed messages for catch-up.

**Parameters**:
• `days` - How many days to look back (default: 1)

**Example**:
`/summary days:3` - Show important messages from last 3 days

**How it works**:
Uses ML ranking based on reactions, replies, and your interaction history.""",
        "s": "Alias for `/summary`. See `/help summary` for details.",
        "catchup": """**`/catchup me [days:1-30]`**
Shows personalized social bullet points from recent activity.

**Parameters**:
• `days` - How many days to look back (default: 1)

**Example**:
`/catchup me days:7` - Catch up on the last week

**Features**:
• Resolves user and channel names
• Shows clickable message links
• Highlights important conversations""",
        "stats": """**`/stats [days:1-90]`**
Shows server activity statistics, top users, and emoji culture.

**Parameters**:
• `days` - How many days to analyze (default: 30)

**Example**:
`/stats days:7` - Last week's statistics

**Includes**:
• Total messages and active users
• Top 5 most active users
• Emoji distribution chart""",
        "influence": """**`/influence [days:1-90]`**
Analyzes user influence using PageRank and centrality.

**Parameters**:
• `days` - How many days to analyze (default: 30)

**Example**:
`/influence days:14` - Two weeks of influence data

**Metrics**:
• PageRank score (network influence)
• Reply influence (who gets most replies)
• Reaction influence (who gets most reactions)
• Centrality (connection strength)""",
        "i": "Alias for `/influence`. See `/help influence` for details.",
        "copycat": """**`/copycat on/off/status`**
Away-mode auto-reply system.

**Subcommands**:
• `on duration:120 status_note:"text"` - Activate copycat mode
• `off` - Deactivate copycat mode
• `status` - Check current status
• `channel_add` - Allow copycat in current channel
• `channel_remove` - Disable copycat in current channel
• `history_enable` - Enable message history learning
• `history_disable` - Disable history learning

**Note**: Requires LM Studio for AI replies, otherwise uses generic away messages.""",
        "culture": """**`/culture memory/emoji/bridges/lore`**
Analyze server culture and social patterns.

**Subcommands**:
• `memory` - Activity patterns and trends
• `emoji` - Emoji usage statistics
• `bridges` - Users connecting different groups
• `lore` - Trending phrases and vocabulary (needs 7+ days data)

**Example**:
`/culture memory` - See server activity patterns""",
        "health": """**`/health`**
Check bot and system health status.

**Shows**:
• Bot uptime
• Neo4j connection status
• Model loading status
• Recent errors (if any)""",
        "profile": """**`/profile [@user]`**
Show detailed user statistics and activity.

**Parameters**:
• `@user` - User to view profile for (default: yourself)

**Example**:
`/profile @Sophie` - View Sophie's profile

**Includes**:
• Total messages sent
• Most active channels
• Top emojis used
• Interaction partners
• Activity heatmap""",
    }

    return help_docs.get(command.lower())
