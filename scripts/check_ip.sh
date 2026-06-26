#!/bin/bash
# =============================================================================
# SecurepathVPN — check_ip.sh
# Monitors public IP changes and sends Discord notifications.
# Called by cron every 5 minutes.
# =============================================================================

DISCORD_WEBHOOK="$1"
CURRENT_IP=$(curl -s ifconfig.me)
OLD_IP_FILE="/tmp/last_public_ip.txt"
OLD_IP=$(cat "$OLD_IP_FILE" 2>/dev/null)
HOSTNAME_STR=$(hostname 2>/dev/null || echo "unknown")

if [ "$CURRENT_IP" != "$OLD_IP" ]; then
    echo "$CURRENT_IP" > "$OLD_IP_FILE"
    MESSAGE="{\"content\":\"⚠️ **Public IP Changed** on $HOSTNAME_STR: **$CURRENT_IP** (previous: $OLD_IP)\"}"
    curl -X POST -H "Content-Type: application/json" -d "$MESSAGE" "$DISCORD_WEBHOOK" > /dev/null 2>&1
fi
