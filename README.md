# SecurepathVPN

## Description

**SecurepathVPN** is an automated, non-interactive deployment solution for setting up a Raspberry Pi (ARM-based) as a VPN server using PiVPN (OpenVPN). It includes Tailscale for fallback remote access, VNC for desktop management, and automated notifications via Discord webhooks. Designed for easy deployment on client sites with minimal manual intervention.

---

## Features

- **Automated PiVPN Deployment**: Non-interactive setup with OpenVPN.
- **Tailscale Integration**: Fallback remote access.
- **VNC & Desktop Auto-Login**: Easy GUI access.
- **IP Change Monitoring**: Discord notifications for public IP changes.
- **NAT & IPv4 Forwarding**: Automatic traffic redirection from VPN to LAN.
- **Security Tools**: `fail2ban`, `unattended-upgrades`, and `iptables-persistent` included.
- **Client Configuration**: Pre-configured OpenVPN client files.

---

## Repository Structure

```
SecurepathVPN/
├── install.sh          # Main installation script (non-interactive)
├── easyvpn.sh          # Interactive VPN management script
├── config.txt          # Configuration file for environment variables
├── README.md           # This file
├── LICENSE             # License file
└── scripts/
    ├── check_ip.sh      # Script to monitor public IP changes
    └── notify_discord.sh # Script to send Discord notifications
```

---

## Requirements

- **Hardware**: Raspberry Pi 3B+ (or newer, ARM-based).
- **OS**: Raspberry Pi OS (recommended) or DietPi.
- **Dependencies**: `curl`, `git`, `openvpn`, `tailscale`, `iptables-persistent`, `fail2ban`, `unattended-upgrades`.

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/SecurepathVPN.git
cd SecurepathVPN
```

### 2. Configure Environment Variables

Edit `config.txt` to set your preferences:

```bash
# Example config.txt
PIVPN_USER="pi"
PIVPN_PROTO="udp"
PIVPN_PORT="1194"
PIVPN_DNS="1.1.1.1"
PIVPN_NET="10.8.0.0/24"
LAN_INTERFACE="eth0"
VPN_CLIENT_NAME="client1"
VPN_CLIENT_PASS=""  # Leave empty for random password
DISCORD_WEBHOOK="https://discord.com/api/webhooks/your-webhook-url"
TAILSCALE_AUTHKEY="your-tailscale-authkey"
```

### 3. Run the Installation Script

```bash
chmod +x install.sh
sudo ./install.sh
```

### 4. Post-Installation Steps

- Open port `$PIVPN_PORT/$PIVPN_PROTO` on your router to forward traffic to the Raspberry Pi.
- Connect to the Pi via Tailscale or VNC for maintenance.

---

## Configuration Details

### `install.sh`

- Automates the entire setup:
  - OS updates and dependency installation.
  - Tailscale and VNC configuration.
  - PiVPN deployment (non-interactive).
  - IPv4 forwarding and NAT rules.
  - `fail2ban` and `unattended-upgrades` setup.
  - Discord notification for completion/failures.

### `easyvpn.sh`

- Interactive script for managing VPN clients after deployment:
  - Add/remove clients.
  - List active connections.
  - Revoke certificates.
  - Send recap notifications to Discord.

### `check_ip.sh`

- Monitors public IP changes every 5 minutes.
- Sends a Discord notification if the IP changes.

---

## Usage

### Adding a New VPN Client

```bash
sudo pivpn add -n "client-name" -p "password" -d 1024
```

### Removing a VPN Client

```bash
sudo pivpn revoke client-name
```

### Viewing Active Connections

```bash
sudo pivpn list
```

---

## Security Notes

- SSH password authentication is **enabled** (32-character random passwords recommended).
- No firewall is installed on the Raspberry Pi (rely on router rules).
- `fail2ban` is installed to mitigate brute-force attacks.
- `unattended-upgrades` keeps the system updated automatically.

---

## Troubleshooting

### PiVPN Issues

- Check logs: `journalctl -u pivpn -f`
- Verify OpenVPN service: `sudo systemctl status openvpn@server`

### Tailscale Issues

- Check status: `tailscale status`
- Restart service: `sudo systemctl restart tailscaled`

### IP Forwarding Issues

- Verify forwarding is enabled: `cat /proc/sys/net/ipv4/ip_forward` (should return `1`).
- Check NAT rules: `sudo iptables -t nat -L -n`

---

## License

This project is proprietary. Do not distribute without permission.

---

## Contributing

This is a private repository. Contributions are not accepted at this time.

---

## Support

For issues or questions, contact the repository owner.