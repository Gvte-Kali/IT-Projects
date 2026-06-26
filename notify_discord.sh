#!/bin/bash
# =============================================================================
# SecurepathVPN — notify_discord.sh
# Generic script to send Discord notifications.
# Usage: ./notify_discord.sh "WEBHOOK_URL" "MESSAGE_JSON"
# =============================================================================

DISCORD_WEBHOOK="$1"
MESSAGE="$2"

if [ -z "$DISCORD_WEBHOOK" ]; then
    echo "Error: Discord webhook URL is required."
    exit 1
fi

if [ -z "$MESSAGE" ]; then
    echo "Error: Message is required."
    exit 1
fi

curl -X POST -H "Content-Type: application/json" -d "$MESSAGE" "$DISCORD_WEBHOOK" > /dev/null 2>&1