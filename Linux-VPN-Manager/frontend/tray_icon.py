"""
System Tray Icon Module

Provides system tray icon functionality for VPN Manager.
"""

from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QMessageBox, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer, Qt
from pathlib import Path
from typing import Optional
import logging


class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon for VPN Manager."""

    def __init__(self, vpn_handler, config_manager, log_manager, main_window):
        """
        Initialize the system tray icon.

        Args:
            vpn_handler: VPNHandler instance
            config_manager: ConfigManager instance
            log_manager: LogManager instance
            main_window: MainWindow instance
        """
        # Try to find icon
        icon_path = self._get_icon_path("icon.png")
        if icon_path:
            icon = QIcon(icon_path)
        else:
            icon = QIcon()

        super().__init__(icon)

        self.vpn_handler = vpn_handler
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.main_window = main_window
        self.logger = logging.getLogger("SystemTrayIcon")

        # Create menu
        self.menu = QMenu()

        # Show main window action
        self.show_action = QAction("Show VPN Manager")
        self.show_action.triggered.connect(self.show_main_window)
        self.menu.addAction(self.show_action)

        self.menu.addSeparator()

        # Connection actions
        self.connection_actions = {}
        self.refresh_connections()

        self.menu.addSeparator()

        # Status label
        self.status_action = QAction("Status: Ready")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)

        self.setContextMenu(self.menu)
        self.show()

        # Set up status update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(5000)  # Refresh every 5 seconds

        # Set tool tip
        self.setToolTip("VPN Manager - Click to show menu")

    def _get_icon_path(self, filename: str) -> Optional[str]:
        """Get the path to an icon file."""
        # Check in assets directory relative to script
        script_dir = Path(__file__).parent.parent
        icon_path = script_dir / "assets" / filename
        if icon_path.exists():
            return str(icon_path)

        # Check in system data directory
        system_icon_path = Path(f"/usr/local/share/vpn-manager/assets/{filename}")
        if system_icon_path.exists():
            return str(system_icon_path)

        # Check in user data directory
        user_icon_path = Path(
            f"~/.local/share/vpn-manager/assets/{filename}"
        ).expanduser()
        if user_icon_path.exists():
            return str(user_icon_path)

        return None

    def _get_status_icon(self, status: str) -> QIcon:
        """Get the appropriate icon based on status."""
        if status == "UP":
            icon_path = self._get_icon_path("green.png")
        elif status == "CONNECTING":
            icon_path = self._get_icon_path("yellow.png")
        else:
            icon_path = self._get_icon_path("red.png")

        if icon_path:
            return QIcon(icon_path)
        return QIcon()

    def show_main_window(self):
        """Show the main application window."""
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def quit_app(self):
        """Quit the application."""
        try:
            # Stop all active VPN connections
            for connection_name in list(self.vpn_handler.active_processes.keys()):
                self.vpn_handler.stop_vpn(connection_name)

            self.logger.info("Application quit via tray icon")
            QApplication.quit()
        except Exception as e:
            self.logger.error(f"Error during quit: {str(e)}")
            QApplication.quit()

    def refresh_connections(self):
        """Refresh the connection actions in the menu."""
        try:
            # Remove existing connection actions
            for action in list(self.connection_actions.values()):
                self.menu.removeAction(action)
            self.connection_actions.clear()

            # Add connection actions
            connections = self.config_manager.list_connections()
            if not connections:
                no_connections_action = QAction("(No connections)")
                no_connections_action.setEnabled(False)
                self.menu.insertAction(self.menu.actions()[1], no_connections_action)
            else:
                for name in connections:
                    status, _ = self.vpn_handler.get_vpn_status(name)
                    icon = self._get_status_icon(status)

                    action = QAction(icon, f"{name} ({status})")
                    action.triggered.connect(lambda _, n=name: self.toggle_connection(n))
                    self.connection_actions[name] = action
                    self.menu.insertAction(self.menu.actions()[1], action)

            # Update status
            self._update_status_text()

        except Exception as e:
            self.logger.error(f"Error refreshing connections: {str(e)}")

    def refresh_status(self):
        """Refresh the status of all connections."""
        try:
            # Update connection status in menu
            for name, action in self.connection_actions.items():
                status, _ = self.vpn_handler.get_vpn_status(name)
                icon = self._get_status_icon(status)
                action.setIcon(icon)
                action.setText(f"{name} ({status})")

            # Update status text
            self._update_status_text()

        except Exception as e:
            self.logger.error(f"Error refreshing status: {str(e)}")

    def _update_status_text(self):
        """Update the status text in the menu."""
        try:
            connections = self.config_manager.list_connections()
            active_count = 0

            for name in connections:
                status, _ = self.vpn_handler.get_vpn_status(name)
                if status == "UP":
                    active_count += 1

            total = len(connections)
            self.status_action.setText(
                f"Status: {active_count} active / {total} total"
            )

            # Update tool tip
            self.setToolTip(
                f"VPN Manager - {active_count} active, {total} total connections"
            )

        except Exception as e:
            self.logger.error(f"Error updating status text: {str(e)}")

    def toggle_connection(self, name: str):
        """
        Toggle a VPN connection (connect/disconnect).

        Args:
            name: Name of the connection to toggle
        """
        try:
            status, _ = self.vpn_handler.get_vpn_status(name)

            if status == "UP":
                success, message = self.vpn_handler.stop_vpn(name)
            else:
                config_path = self.config_manager.get_config_path(name)
                success, message = self.vpn_handler.start_vpn(config_path, name)

            if success:
                self.refresh_status()
                self.showMessage("VPN Manager", message)
            else:
                self.showMessage("VPN Manager", f"Error: {message}", QIcon(), 5000)

        except Exception as e:
            self.logger.error(f"Error toggling connection {name}: {str(e)}")
            self.showMessage(
                "VPN Manager", f"Error toggling connection: {str(e)}", QIcon(), 5000
            )

    def show_notification(self, title: str, message: str, duration: int = 5000):
        """
        Show a notification from the tray icon.

        Args:
            title: Notification title
            message: Notification message
            duration: Duration in milliseconds
        """
        self.showMessage(title, message, QIcon(), duration)
