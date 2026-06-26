#!/usr/bin/env bash
# =============================================================================
# SecurepathVPN — easyvpn.sh
# Interactive VPN management panel for PiVPN (OpenVPN).
# Wraps pivpn commands, sends notifications and files to Discord.
#
# Usage: sudo easyvpn or sudo ./easyvpn.sh
# Symlink to /usr/local/bin/easyvpn by install.sh
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Color Codes
# -----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Root Check
# -----------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

# -----------------------------------------------------------------------------
# Load Configuration
# -----------------------------------------------------------------------------
CONFIG_FILE=""
for candidate in \
    "/opt/securepathvpn/config.txt" \
    "/opt/easypivpn/config.txt" \
    "$(dirname "$(readlink -f "$0")")/config.txt"; do
    if [[ -f "$candidate" ]]; then
        CONFIG_FILE="$candidate"
        break
    fi
done

if [[ -n "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo -e "${YELLOW}[WARN]${NC} config.txt not found — Discord notifications disabled."
fi

DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK:-}"
OVPNS_DIR="${OVPNS_DIR:-$HOME/ovpns}"

# -----------------------------------------------------------------------------
# Utility Functions
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

# Send Discord notification
send_discord() {
    local message="$1"
    if [[ -z "$DISCORD_WEBHOOK_URL" || "$DISCORD_WEBHOOK_URL" == "PLACEHOLDER" ]]; then
        log_warning "Discord webhook not configured. Skipping notification."
        return
    fi
    curl -X POST -H "Content-Type: application/json" -d "$message" "$DISCORD_WEBHOOK_URL" > /dev/null 2>&1
}

# -----------------------------------------------------------------------------
# Menu Functions
# -----------------------------------------------------------------------------
show_menu() {
    clear
    echo "=================================================="
    echo "         ${PURPLE}SecurepathVPN Management Panel${NC}           "
    echo "=================================================="
    echo ""
    echo "1.  Add a new VPN client"
    echo "2.  Revoke a VPN client"
    echo "3.  List all VPN clients"
    echo "4.  Show active VPN connections"
    echo "5.  Restart OpenVPN service"
    echo "6.  Show OpenVPN logs"
    echo "7.  Show Tailscale status"
    echo "8.  Show public IP"
    echo "9.  Show PiVPN configuration"
    echo "10. Backup VPN configurations"
    echo "11. Restore VPN configurations"
    echo "12. Export client configuration"
    echo "13. Import client configuration"
    echo "14. Show system information"
    echo "15. Send installation recap to Discord"
    echo ""
    echo "0.  Exit"
    echo ""
    echo -n "Enter your choice [0-15]: "
}

# Add a new VPN client
action_add_client() {
    read -p "Enter client name: " client_name
    read -p "Enter password (leave empty for random): " client_pass
    read -p "Enter certificate validity in days (default: 1024): " cert_days
    cert_days="${cert_days:-1024}"
    
    if pivpn add -n "$client_name" -p "$client_pass" -d "$cert_days"; then
        log_success "Client '$client_name' added successfully."
        
        # Send client config to Discord
        ovpn_file="$OVPNS_DIR/$client_name.ovpn"
        if [[ -f "$ovpn_file" ]]; then
            log "Sending client configuration to Discord..."
            encoded_file=$(base64 -w 0 "$ovpn_file")
            HOSTNAME_STR=$(hostname 2>/dev/null || echo "unknown")
            MESSAGE=$(jq -n \
                --arg hostname "$HOSTNAME_STR" \
                --arg client "$client_name" \
                --arg file "$encoded_file" \
                '{
                    "content": "📄 **New VPN Client: \(.client) on \(.hostname)**",
                    "embeds": [{
                        "title": "Client Configuration",
                        "description": "Attached: OpenVPN configuration file for \(.client).",
                        "color": 3447003
                    }],
                    "attachments": [{
                        "filename": "\(.client).ovpn",
                        "content": \(.file)
                    }]
                }')
            send_discord "$MESSAGE"
        fi
    else
        log_error "Failed to add client '$client_name'."
    fi
    
    read -p "Press [Enter] to continue..."
}

# Revoke a VPN client
action_revoke_client() {
    pivpn list
    read -p "Enter client name to revoke: " client_name
    if pivpn revoke "$client_name"; then
        log_success "Client '$client_name' revoked successfully."
        send_discord "{\"content\":\"🗑️ **VPN Client Revoked**: $client_name on $(hostname 2>/dev/null || echo unknown)\"}"
    else
        log_error "Failed to revoke client '$client_name'."
    fi
    read -p "Press [Enter] to continue..."
}

# List all VPN clients
action_list_clients() {
    pivpn list
    read -p "Press [Enter] to continue..."
}

# Show active VPN connections
action_show_connections() {
    echo "Active OpenVPN connections:"
    cat /etc/openvpn/server/openvpn-status.log 2>/dev/null || echo "No active connections found."
    read -p "Press [Enter] to continue..."
}

# Restart OpenVPN service
action_restart_openvpn() {
    if systemctl restart openvpn@server; then
        log_success "OpenVPN service restarted."
        send_discord "{\"content\":\"🔄 **OpenVPN Service Restarted** on $(hostname 2>/dev/null || echo unknown)\"}"
    else
        log_error "Failed to restart OpenVPN service."
    fi
    read -p "Press [Enter] to continue..."
}

# Show OpenVPN logs
action_show_logs() {
    journalctl -u openvpn@server -f --no-pager
    read -p "Press [Enter] to stop viewing logs..."
}

# Show Tailscale status
action_show_tailscale() {
    tailscale status
    read -p "Press [Enter] to continue..."
}

# Show public IP
action_show_public_ip() {
    public_ip=$(curl -s ifconfig.me)
    echo "Public IP: $public_ip"
    send_discord "{\"content\":\"🌐 **Public IP Check**: $public_ip on $(hostname 2>/dev/null || echo unknown)\"}"
    read -p "Press [Enter] to continue..."
}

# Show PiVPN configuration
action_show_config() {
    echo "PiVPN Configuration:"
    cat /etc/pivpn/wireguard/configs/server.conf 2>/dev/null || cat /etc/openvpn/server.conf 2>/dev/null || echo "Configuration file not found."
    read -p "Press [Enter] to continue..."
}

# Backup VPN configurations
action_backup_configs() {
    backup_dir="/home/$(whoami)/securepathvpn_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    log "Backing up VPN configurations to $backup_dir..."
    
    # Backup PiVPN configs
    if [[ -d /etc/pivpn ]]; then
        cp -r /etc/pivpn "$backup_dir/"
    fi
    
    # Backup OpenVPN configs
    if [[ -d /etc/openvpn ]]; then
        cp -r /etc/openvpn "$backup_dir/"
    fi
    
    # Backup client configs
    if [[ -d "$OVPNS_DIR" ]]; then
        cp -r "$OVPNS_DIR" "$backup_dir/"
    fi
    
    # Backup iptables rules
    if [[ -f /etc/iptables/rules.v4 ]]; then
        cp /etc/iptables/rules.v4 "$backup_dir/"
    fi
    
    # Create tar.gz archive
    tar -czvf "$backup_dir.tar.gz" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    rm -rf "$backup_dir"
    
    log_success "Backup created: $backup_dir.tar.gz"
    send_discord "{\"content\":\"💾 **VPN Backup Created** on $(hostname 2>/dev/null || echo unknown): $backup_dir.tar.gz\"}"
    read -p "Press [Enter] to continue..."
}

# Restore VPN configurations
action_restore_configs() {
    log "This feature is not yet implemented. Use manual restore for now."
    read -p "Press [Enter] to continue..."
}

# Export client configuration
action_export_client() {
    pivpn list
    read -p "Enter client name to export: " client_name
    ovpn_file="$OVPNS_DIR/$client_name.ovpn"
    
    if [[ -f "$ovpn_file" ]]; then
        read -p "Enter export directory (default: current): " export_dir
        export_dir="${export_dir:-.}"
        
        if [[ -d "$export_dir" ]]; then
            cp "$ovpn_file" "$export_dir/"
            log_success "Client '$client_name' configuration exported to $export_dir/"
            send_discord "{\"content\":\"📤 **VPN Client Exported**: $client_name to $(hostname 2>/dev/null || echo unknown):$export_dir/\"}"
        else
            log_error "Export directory does not exist: $export_dir"
        fi
    else
        log_error "Client configuration file not found: $ovpn_file"
    fi
    read -p "Press [Enter] to continue..."
}

# Import client configuration
action_import_client() {
    read -p "Enter path to .ovpn file: " ovpn_path
    if [[ -f "$ovpn_path" ]]; then
        client_name=$(basename "$ovpn_path" .ovpn)
        cp "$ovpn_path" "$OVPNS_DIR/$client_name.ovpn"
        log_success "Client '$client_name' configuration imported."
        send_discord "{\"content\":\"📥 **VPN Client Imported**: $client_name on $(hostname 2>/dev/null || echo unknown)\"}"
    else
        log_error "File not found: $ovpn_path"
    fi
    read -p "Press [Enter] to continue..."
}

# Show system information
action_show_system_info() {
    echo "===== System Information ====="
    echo "Hostname: $(hostname)"
    echo "Uptime: $(uptime -p)"
    echo "CPU Load: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
    echo "Memory Usage: $(free -h | awk '/Mem/{print $3 "/" $2 " (" $4 ")"}')"
    echo "Disk Usage: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $4 ")"}')"
    echo "Public IP: $(curl -s ifconfig.me)"
    echo "Local IP: $(hostname -I | awk '{print $1}')"
    echo ""
    echo "===== Services Status ====="
    systemctl is-active --quiet openvpn@server && echo "OpenVPN: Running" || echo "OpenVPN: Not running"
    systemctl is-active --quiet tailscaled && echo "Tailscale: Running" || echo "Tailscale: Not running"
    systemctl is-active --quiet fail2ban && echo "fail2ban: Running" || echo "fail2ban: Not running"
    systemctl is-active --quiet unattended-upgrades && echo "unattended-upgrades: Running" || echo "unattended-upgrades: Not running"
    read -p "Press [Enter] to continue..."
}

# Send installation recap to Discord
action_recap() {
    HOSTNAME_STR=$(hostname 2>/dev/null || echo "unknown")
    PUBLIC_IP=$(curl -s ifconfig.me)
    ACTIVE_CLIENTS=$(pivpn list | grep -c "^\s*[0-9]" 2>/dev/null || echo "0")
    CONNECTED_CLIENTS=$(cat /etc/openvpn/server/openvpn-status.log 2>/dev/null | grep -c "^CLIENT_LIST" || echo "0")
    
    # Check services
    OPENVPN_STATUS=$(systemctl is-active openvpn@server 2>/dev/null || echo "inactive")
    TAILSCALE_STATUS=$(systemctl is-active tailscaled 2>/dev/null || echo "inactive")
    FAIL2BAN_STATUS=$(systemctl is-active fail2ban 2>/dev/null || echo "inactive")
    UNATTENDED_STATUS=$(systemctl is-active unattended-upgrades 2>/dev/null || echo "inactive")
    
    # Get NAT rules
    NAT_RULES=$(iptables -t nat -L POSTROUTING -n 2>/dev/null | grep -c MASQUERADE || echo "0")
    
    # Get LAN interface
    LAN_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)
    
    MESSAGE=$(jq -n \
        --arg hostname "$HOSTNAME_STR" \
        --arg public_ip "$PUBLIC_IP" \
        --arg lan_interface "$LAN_INTERFACE" \
        --arg active_clients "$ACTIVE_CLIENTS" \
        --arg connected_clients "$CONNECTED_CLIENTS" \
        --arg openvpn "$OPENVPN_STATUS" \
        --arg tailscale "$TAILSCALE_STATUS" \
        --arg fail2ban "$FAIL2BAN_STATUS" \
        --arg unattended "$UNATTENDED_STATUS" \
        --arg nat_rules "$NAT_RULES" \
        '{
            "content": "📊 **SecurepathVPN Status on \(.hostname)**",
            "embeds": [
                {
                    "title": "System Overview",
                    "color": 3447003,
                    "fields": [
                        {"name": "Public IP", "value": \(.public_ip), "inline": true},
                        {"name": "LAN Interface", "value": \(.lan_interface), "inline": true},
                        {"name": "Active Clients", "value": \(.active_clients), "inline": true},
                        {"name": "Connected Clients", "value": \(.connected_clients), "inline": true},
                        {"name": "OpenVPN", "value": \(.openvpn), "inline": true},
                        {"name": "Tailscale", "value": \(.tailscale), "inline": true},
                        {"name": "fail2ban", "value": \(.fail2ban), "inline": true},
                        {"name": "unattended-upgrades", "value": \(.unattended), "inline": true},
                        {"name": "NAT Rules", "value": \(.nat_rules) MASQUERADE rules, "inline": false}
                    ]
                }
            ]
        }')
    
    send_discord "$MESSAGE"
    log_success "Recap sent to Discord."
    read -p "Press [Enter] to continue..."
}

# -----------------------------------------------------------------------------
# Main Loop
# -----------------------------------------------------------------------------
while true; do
    show_menu
    read choice
    case $choice in
        1) action_add_client ;;
        2) action_revoke_client ;;
        3) action_list_clients ;;
        4) action_show_connections ;;
        5) action_restart_openvpn ;;
        6) action_show_logs ;;
        7) action_show_tailscale ;;
        8) action_show_public_ip ;;
        9) action_show_config ;;
        10) action_backup_configs ;;
        11) action_restore_configs ;;
        12) action_export_client ;;
        13) action_import_client ;;
        14) action_show_system_info ;;
        15) action_recap ;;
        0)
            log "Exiting..."
            exit 0
            ;;
        *)
            log_error "Invalid option. Please try again."
            ;;
    esac
done