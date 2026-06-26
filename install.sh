#!/usr/bin/env bash
# =============================================================================
# SecurepathVPN — install.sh
# Automated, non-interactive deployment script for Raspberry Pi VPN server.
# Uses PiVPN (OpenVPN) with Tailscale fallback, VNC, and Discord notifications.
#
# Usage: sudo ./install.sh
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Color Codes
# -----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Root Check
# -----------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERROR]${NC} This script must be run as root. Use 'sudo ./install.sh'."
    exit 1
fi

# -----------------------------------------------------------------------------
# Load Configuration
# -----------------------------------------------------------------------------
CONFIG_FILE="$(dirname "$(readlink -f "$0")")/config.txt"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo -e "${RED}[ERROR]${NC} config.txt not found. Please create it from config.txt.example."
    exit 1
fi

source "$CONFIG_FILE"

# Validate required variables
REQUIRED_VARS=("PIVPN_USER" "PIVPN_PROTO" "PIVPN_PORT" "PIVPN_DNS" "PIVPN_NET" "LAN_INTERFACE" "DISCORD_WEBHOOK")
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo -e "${RED}[ERROR]${NC} Missing required variable: $var in config.txt."
        exit 1
    fi
done

# Default values for optional variables
VPN_CLIENT_NAME="${VPN_CLIENT_NAME:-client1}"
VPN_CLIENT_PASS="${VPN_CLIENT_PASS:-}"
TAILSCALE_AUTHKEY="${TAILSCALE_AUTHKEY:-}"

# -----------------------------------------------------------------------------
# Logging Function
# -----------------------------------------------------------------------------
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# -----------------------------------------------------------------------------
# Update System
# -----------------------------------------------------------------------------
log "Updating system packages..."
apt-get update -y
apt-get upgrade -y
apt-get install -y curl git net-tools dnsutils iptables-persistent fail2ban unattended-upgrades

# -----------------------------------------------------------------------------
# Install Network Utilities
# -----------------------------------------------------------------------------
log "Installing network utilities..."
apt-get install -y nmap arp-scan tcpdump iftop iptraf-ng

# -----------------------------------------------------------------------------
# Install and Configure Tailscale
# -----------------------------------------------------------------------------
log "Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
if [[ -n "$TAILSCALE_AUTHKEY" ]]; then
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="$(hostname)" --accept-terms
else
    log_warning "No TAILSCALE_AUTHKEY provided. Tailscale will require manual login."
    tailscale up --hostname="$(hostname)" --accept-terms
fi
systemctl enable --now tailscaled

# -----------------------------------------------------------------------------
# Configure VNC and Desktop Auto-Login
# -----------------------------------------------------------------------------
log "Configuring VNC and desktop auto-login..."
if ! command -v raspi-config &> /dev/null; then
    log_error "raspi-config not found. This script is intended for Raspberry Pi OS."
    exit 1
fi

# Enable VNC
raspi-config nonint do_vnc 0

# Set boot to desktop with auto-login
raspi-config nonint do_boot_behaviour B2

# -----------------------------------------------------------------------------
# Install PiVPN (Non-Interactive)
# -----------------------------------------------------------------------------
log "Installing PiVPN..."
export PIVPN_USER="$PIVPN_USER"
export PIVPN_PROTO="$PIVPN_PROTO"
export PIVPN_PORT="$PIVPN_PORT"
export PIVPN_DNS="$PIVPN_DNS"
export PIVPN_NET="$PIVPN_NET"
export PIVPN_DEV="tun0"
export PIVPN_NAT="y"
export PIVPN_INSTALL="y"
export PIVPN_RECONF="n"

curl -sSL https://install.pivpn.io | bash

# -----------------------------------------------------------------------------
# Add First VPN Client
# -----------------------------------------------------------------------------
log "Adding first VPN client: $VPN_CLIENT_NAME"
pivpn add -n "$VPN_CLIENT_NAME" -p "$VPN_CLIENT_PASS" -d 1024

# -----------------------------------------------------------------------------
# Enable IPv4 Forwarding
# -----------------------------------------------------------------------------
log "Enabling IPv4 forwarding..."
sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
sysctl -p

# -----------------------------------------------------------------------------
# Configure NAT MASQUERADE
# -----------------------------------------------------------------------------
log "Configuring NAT MASQUERADE for $LAN_INTERFACE..."
iptables -t nat -A POSTROUTING -o "$LAN_INTERFACE" -j MASQUERADE
iptables -A FORWARD -i tun0 -o "$LAN_INTERFACE" -j ACCEPT
iptables -A FORWARD -i "$LAN_INTERFACE" -o tun0 -m state --state RELATED,ESTABLISHED -j ACCEPT
netfilter-persistent save

# -----------------------------------------------------------------------------
# Configure fail2ban
# -----------------------------------------------------------------------------
log "Configuring fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

# -----------------------------------------------------------------------------
# Configure unattended-upgrades
# -----------------------------------------------------------------------------
log "Configuring unattended-upgrades..."
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESM:${distro_codename}";
};
Unattended-Upgrade::Automatic-Reboot "true";
EOF

# -----------------------------------------------------------------------------
# Create IP Check Script
# -----------------------------------------------------------------------------
log "Creating IP monitoring script..."
cat > /usr/local/bin/check_ip.sh << 'SCRIPT'
#!/bin/bash
DISCORD_WEBHOOK="$1"
CURRENT_IP=$(curl -s ifconfig.me)
OLD_IP_FILE="/tmp/last_public_ip.txt"
OLD_IP=$(cat "$OLD_IP_FILE" 2>/dev/null)

if [ "$CURRENT_IP" != "$OLD_IP" ]; then
    echo "$CURRENT_IP" > "$OLD_IP_FILE"
    HOSTNAME=$(hostname)
    MESSAGE="{\"content\":\"⚠️ **Public IP Changed** on $HOSTNAME: **$CURRENT_IP** (previous: $OLD_IP)\"}"
    curl -X POST -H "Content-Type: application/json" -d "$MESSAGE" "$DISCORD_WEBHOOK"
fi
SCRIPT

chmod +x /usr/local/bin/check_ip.sh

# Add to cron
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/check_ip.sh $DISCORD_WEBHOOK") | crontab -

# -----------------------------------------------------------------------------
# Create Notification Script
# -----------------------------------------------------------------------------
cat > /usr/local/bin/notify_discord.sh << 'SCRIPT'
#!/bin/bash
DISCORD_WEBHOOK="$1"
MESSAGE="$2"
curl -X POST -H "Content-Type: application/json" -d "$MESSAGE" "$DISCORD_WEBHOOK"
SCRIPT

chmod +x /usr/local/bin/notify_discord.sh

# -----------------------------------------------------------------------------
# Final Discord Notification
# -----------------------------------------------------------------------------
log "Sending final Discord notification..."
HOSTNAME=$(hostname)
PUBLIC_IP=$(curl -s ifconfig.me)

MESSAGE=$(cat <<EOF
{
  "content": "✅ **SecurepathVPN Installation Complete on $HOSTNAME**\n\n"
  "embeds": [
    {
      "title": "Installation Summary",
      "color": 3066993,
      "fields": [
        {"name": "Tailscale", "value": "Connected", "inline": true},
        {"name": "PiVPN", "value": "Port $PIVPN_PROTO/$PIVPN_PORT, Client: $VPN_CLIENT_NAME", "inline": true},
        {"name": "VNC", "value": "Enabled", "inline": true},
        {"name": "Public IP", "value": "$PUBLIC_IP", "inline": true},
        {"name": "Action Required", "value": "Open port $PIVPN_PORT/$PIVPN_PROTO on your router to this Pi.", "inline": false}
      ]
    }
  ]
}
EOF
)

/usr/local/bin/notify_discord.sh "$DISCORD_WEBHOOK" "$MESSAGE"

# -----------------------------------------------------------------------------
# Print Manual Action
# -----------------------------------------------------------------------------
log_success "SecurepathVPN installation completed successfully!"
log "Manual action required: Open port $PIVPN_PORT/$PIVPN_PROTO on your router to forward to this Raspberry Pi."
log "Connect via Tailscale or VNC for maintenance."
log "VPN client configuration file: /home/$PIVPN_USER/ovpns/$VPN_CLIENT_NAME.ovpn"