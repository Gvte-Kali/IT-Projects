#!/usr/bin/env python3
"""
Linux VPN Manager - Main Application Entry Point

A cross-distribution, cross-desktop environment GUI application for managing
VPN connections (OpenVPN, WireGuard) on Linux.
"""

import sys
import os
import signal
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from frontend.main_window import MainWindow
from frontend.tray_icon import SystemTrayIcon
from backend.vpn_handler import VPNHandler
from backend.log_manager import LogManager
from backend.config_manager import ConfigManager


class VPNManager:
    """Main VPN Manager application class."""

    def __init__(self):
        """Initialize the VPN Manager application."""
        # Configure logging
        self._setup_logging()

        # Create QApplication
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("VPN Manager")
        self.app.setOrganizationName("LinuxVPNManager")

        # Initialize backend
        self.config_manager = ConfigManager()
        self.log_manager = LogManager()
        self.vpn_handler = VPNHandler(self.config_manager, self.log_manager)

        # Initialize frontend
        self.main_window = MainWindow(
            self.vpn_handler, self.config_manager, self.log_manager
        )
        self.tray_icon = SystemTrayIcon(
            self.vpn_handler,
            self.config_manager,
            self.log_manager,
            self.main_window,
        )

        # Set app icon
        icon_path = self._get_icon_path("icon.png")
        if icon_path:
            self.app.setWindowIcon(QIcon(str(icon_path)))

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def _setup_logging(self):
        """Configure application logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(
                    os.path.expanduser("~/.local/share/vpn-manager/app.log")
                ),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger("VPNManager")

    def _get_icon_path(self, filename):
        """Get the path to an icon file."""
        # Check in assets directory relative to script
        script_dir = Path(__file__).parent
        icon_path = script_dir / "assets" / filename
        if icon_path.exists():
            return icon_path

        # Check in system data directory
        system_icon_path = Path(
            "/usr/local/share/vpn-manager/assets/" + filename
        )
        if system_icon_path.exists():
            return system_icon_path

        # Check in user data directory
        user_icon_path = Path(
            os.path.expanduser("~/.local/share/vpn-manager/assets/") + filename
        )
        if user_icon_path.exists():
            return user_icon_path

        return None

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Handle termination signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self._cleanup()
        sys.exit(0)

    def _cleanup(self):
        """Clean up resources before exit."""
        self.logger.info("Cleaning up resources...")
        # Stop all active VPN connections
        for connection_name in list(self.vpn_handler.active_processes.keys()):
            self.vpn_handler.stop_vpn(connection_name)

    def run(self):
        """Run the application."""
        try:
            sys.exit(self.app.exec())
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise


def main():
    """Main entry point for the application."""
    # Check for required icon files
    script_dir = Path(__file__).parent
    required_icons = ["green.png", "red.png", "icon.png"]

    missing_icons = []
    for icon in required_icons:
        icon_path = script_dir / "assets" / icon
        if not icon_path.exists():
            # Check system-wide installation
            system_path = Path(f"/usr/local/share/vpn-manager/assets/{icon}")
            user_path = Path(
                os.path.expanduser(f"~/.local/share/vpn-manager/assets/{icon}")
            )
            if not system_path.exists() and not user_path.exists():
                missing_icons.append(icon)

    if missing_icons:
        QMessageBox.critical(
            None,
            "Error",
            f"Required icon files are missing: {', '.join(missing_icons)}. "
            "Please install the application properly using install.sh.",
        )
        sys.exit(1)

    # Check for root privileges (needed for VPN operations)
    if os.geteuid() != 0:
        print(
            "Warning: Running as non-root. VPN operations will require sudo password."
        )

    manager = VPNManager()
    manager.run()


if __name__ == "__main__":
    main()
