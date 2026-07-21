"""
Configuration and Constants for VPN Manager
"""

import os
import sys
from pathlib import Path

# Application Info
APP_NAME = "VPN Manager"
APP_VERSION = "2.0.0"

# Directories
CONFIG_DIR = Path.home() / ".config" / "vpn-manager"
LOG_DIR = Path.home() / ".local/share/vpn-manager/logs"
CONFIG_FILE = CONFIG_DIR / "profiles.json"
LOG_FILE = LOG_DIR / "vpn-manager.log"

# VPN Types
VPN_OPENVPN = "openvpn"
VPN_WIREGUARD = "wireguard"

# Status Constants
STATUS_DISCONNECTED = "disconnected"
STATUS_CONNECTING = "connecting"
STATUS_CONNECTED = "connected"
STATUS_FAILED = "failed"

# DNS Leak Detection
DNS_TEST_DOMAIN = "dnsleaktest.com"
DNS_CHECK_INTERVAL = 30  # seconds
AUTO_RECONNECT_DELAY = 5  # seconds
MAX_RECONNECT_ATTEMPTS = 3

# Emoji Constants (simplified for compatibility)
class Emoji:
    DISCONNECTED = "[X]"
    CONNECTING = "[...]"
    CONNECTED = "[OK]"
    FAILED = "[ERR]"
    VPN = "VPN"
    SETTINGS = "SET"
    PLUS = "[+]"
    MINUS = "[-]"
    REFRESH = "[R]"
    LOGS = "LOG"
    DNS = "DNS"
    WARNING = "[!]"
    MOON = "MOON"
    SUN = "SUN"


def ensure_directories():
    """Ensure required directories exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
