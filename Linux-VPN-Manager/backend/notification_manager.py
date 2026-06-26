"""
Notification Manager Module

Provides desktop environment-specific notifications for VPN Manager.
Supports libnotify (GNOME/XFCE/LXQt), KNotify (KDE), and D-Bus notifications.
"""

import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

try:
    from pydbus import SessionBus
    from pydbus.generic import Signal
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

from .de_manager import get_de_manager


class NotificationManager:
    """Manages notifications for different desktop environments."""

    # Notification urgency levels
    URGENCY_LOW = 0
    URGENCY_NORMAL = 1
    URGENCY_CRITICAL = 2

    def __init__(self):
        """Initialize the Notification Manager."""
        self.logger = logging.getLogger("NotificationManager")
        self.de_manager = get_de_manager()
        self._dbus_notifications = None
        self._notification_id = 0

    def send_notification(
        self,
        title: str,
        message: str,
        icon: Optional[str] = None,
        urgency: int = URGENCY_NORMAL,
        timeout: int = 5000,
        actions: Optional[List[Dict[str, str]]] = None,
        hints: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a notification using the appropriate method for the current DE.

        Args:
            title: Notification title
            message: Notification message
            icon: Path to icon file or icon name
            urgency: Urgency level (LOW=0, NORMAL=1, CRITICAL=2)
            timeout: Timeout in milliseconds (0 = use server default)
            actions: List of action dictionaries with 'key' and 'text'
            hints: Additional hints for the notification

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            de = self.de_manager.current_de
            notification_system = self.de_manager.get_notification_system()

            self.logger.debug(
                f"Sending notification: title='{title}', message='{message}', "
                f"icon='{icon}', urgency={urgency}, timeout={timeout}"
            )

            if notification_system == "knotify" and self.de_manager.is_kde():
                return self._send_kde_notification(title, message, icon, urgency, timeout, actions)
            else:
                # Default to libnotify for most DEs
                return self._send_libnotify_notification(title, message, icon, urgency, timeout, actions, hints)

        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")
            return False

    def _send_libnotify_notification(
        self,
        title: str,
        message: str,
        icon: Optional[str] = None,
        urgency: int = URGENCY_NORMAL,
        timeout: int = 5000,
        actions: Optional[List[Dict[str, str]]] = None,
        hints: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a notification using libnotify (notify-send).

        Args:
            title: Notification title
            message: Notification message
            icon: Path to icon file or icon name
            urgency: Urgency level
            timeout: Timeout in milliseconds
            actions: List of actions
            hints: Additional hints

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Build the notify-send command
            cmd = ["notify-send"]

            # Add urgency if supported
            if urgency in [self.URGENCY_LOW, self.URGENCY_NORMAL, self.URGENCY_CRITICAL]:
                urgency_str = {0: "low", 1: "normal", 2: "critical"}[urgency]
                cmd.extend(["-u", urgency_str])

            # Add timeout
            if timeout > 0:
                cmd.extend(["-t", str(timeout)])

            # Add icon if provided
            if icon:
                # Try to resolve the icon path
                icon_path = self._resolve_icon_path(icon)
                if icon_path:
                    cmd.extend(["-i", icon_path])
                else:
                    cmd.extend(["-i", icon])

            # Add title and message
            cmd.extend([title, message])

            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.warning(
                    f"notify-send failed: {result.stderr}"
                )
                # Try without icon
                cmd = ["notify-send"]
                if urgency in [self.URGENCY_LOW, self.URGENCY_NORMAL, self.URGENCY_CRITICAL]:
                    urgency_str = {0: "low", 1: "normal", 2: "critical"}[urgency]
                    cmd.extend(["-u", urgency_str])
                if timeout > 0:
                    cmd.extend(["-t", str(timeout)])
                cmd.extend([title, message])
                result = subprocess.run(cmd, capture_output=True, text=True)

            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Failed to send libnotify notification: {str(e)}")
            return False

    def _send_kde_notification(
        self,
        title: str,
        message: str,
        icon: Optional[str] = None,
        urgency: int = URGENCY_NORMAL,
        timeout: int = 5000,
        actions: Optional[List[Dict[str, str]]] = None,
    ) -> bool:
        """
        Send a notification using KDE's KNotify.

        Args:
            title: Notification title
            message: Notification message
            icon: Path to icon file or icon name
            urgency: Urgency level
            timeout: Timeout in milliseconds
            actions: List of actions

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Try using qdbus to send notification via KNotify
            cmd = [
                "qdbus",
                "org.kde.knotifications",
                "/Notifications",
                "org.kde.NotificationManager.notify",
                "VPN Manager",  # App name
                "0",  # Replaces ID
                icon or "",  # Icon
                title,  # Summary
                message,  # Text
                [],  # Actions
                {},  # Hints
                str(timeout),  # Timeout
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.warning(
                    f"KNotify via qdbus failed: {result.stderr}"
                )
                # Fallback to notify-send
                return self._send_libnotify_notification(title, message, icon, urgency, timeout, actions)

            return True

        except Exception as e:
            self.logger.error(f"Failed to send KDE notification: {str(e)}")
            # Fallback to notify-send
            return self._send_libnotify_notification(title, message, icon, urgency, timeout, actions)

    def _send_dbus_notification(
        self,
        title: str,
        message: str,
        icon: Optional[str] = None,
        urgency: int = URGENCY_NORMAL,
        timeout: int = 5000,
        actions: Optional[List[Dict[str, str]]] = None,
        hints: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a notification using D-Bus (org.freedesktop.Notifications).

        Args:
            title: Notification title
            message: Notification message
            icon: Path to icon file or icon name
            urgency: Urgency level
            timeout: Timeout in milliseconds
            actions: List of actions
            hints: Additional hints

        Returns:
            bool: True if notification was sent successfully
        """
        if not DBUS_AVAILABLE:
            self.logger.debug("D-Bus notifications not available (pydbus not installed)")
            return self._send_libnotify_notification(title, message, icon, urgency, timeout, actions, hints)

        try:
            bus = SessionBus()
            notifications = bus.get(
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications"
            )

            # Prepare hints
            if hints is None:
                hints = {}

            # Add icon to hints if provided
            if icon:
                icon_path = self._resolve_icon_path(icon)
                if icon_path:
                    hints["icon_data"] = self._load_icon_data(icon_path)
                else:
                    hints["icon_data"] = icon

            # Add urgency to hints
            urgency_str = {0: "low", 1: "normal", 2: "critical"}[urgency]
            hints["urgency"] = (urgency_str,)

            # Prepare actions
            if actions is None:
                actions = []
            action_list = []
            for action in actions:
                action_list.extend([action.get("key", ""), action.get("text", "")])

            # Send notification
            self._notification_id += 1
            notification_id = notifications.Notify(
                "VPN Manager",  # App name
                self._notification_id,  # Replaces ID
                icon or "",  # Icon
                title,  # Summary
                message,  # Body
                action_list,  # Actions
                hints,  # Hints
                timeout,  # Timeout
            )

            return notification_id > 0

        except Exception as e:
            self.logger.error(f"Failed to send D-Bus notification: {str(e)}")
            return self._send_libnotify_notification(title, message, icon, urgency, timeout, actions, hints)

    def _resolve_icon_path(self, icon: str) -> Optional[str]:
        """
        Resolve an icon name or path to an absolute path.

        Args:
            icon: Icon name or path

        Returns:
            str: Absolute path to the icon, or None if not found
        """
        # If it's already an absolute path and exists, return it
        if os.path.isabs(icon) and Path(icon).exists():
            return icon

        # Try to find the icon using DEManager
        de_manager = get_de_manager()
        icon_path = de_manager.get_icon_path(icon)
        if icon_path:
            return icon_path

        # Try common icon paths
        common_paths = [
            f"/usr/share/icons/{icon}.png",
            f"/usr/share/icons/{icon}.svg",
            f"/usr/share/pixmaps/{icon}.png",
            f"/usr/share/pixmaps/{icon}.svg",
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return None

    def _load_icon_data(self, icon_path: str) -> tuple:
        """
        Load icon data for D-Bus notification.

        Args:
            icon_path: Path to the icon file

        Returns:
            tuple: (width, height, rowstride, has_alpha, bits_per_sample, channels, data)
        """
        try:
            from PIL import Image
            import struct

            with Image.open(icon_path) as img:
                # Convert to RGBA if not already
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                width, height = img.size
                # For D-Bus, we need to provide the raw pixel data
                # This is a simplified version - actual implementation would need proper encoding
                return (width, height, width * 4, True, 8, 4, bytes(img.getdata()))

        except ImportError:
            # PIL not available, return empty icon data
            return (0, 0, 0, False, 0, 0, b"")
        except Exception as e:
            self.logger.warning(f"Failed to load icon data: {str(e)}")
            return (0, 0, 0, False, 0, 0, b"")

    def show_connection_connected(self, connection_name: str):
        """Show notification when a connection is established."""
        return self.send_notification(
            title="VPN Connected",
            message=f"{connection_name} is now connected",
            icon="network-vpn",
            urgency=self.URGENCY_NORMAL,
            timeout=5000,
        )

    def show_connection_disconnected(self, connection_name: str):
        """Show notification when a connection is terminated."""
        return self.send_notification(
            title="VPN Disconnected",
            message=f"{connection_name} has been disconnected",
            icon="network-vpn",
            urgency=self.URGENCY_NORMAL,
            timeout=5000,
        )

    def show_connection_error(self, connection_name: str, error: str):
        """Show notification when a connection error occurs."""
        return self.send_notification(
            title="VPN Error",
            message=f"{connection_name}: {error}",
            icon="dialog-error",
            urgency=self.URGENCY_CRITICAL,
            timeout=10000,
        )

    def show_connection_connecting(self, connection_name: str):
        """Show notification when a connection is being established."""
        return self.send_notification(
            title="VPN Connecting",
            message=f"Connecting to {connection_name}...",
            icon="network-vpn",
            urgency=self.URGENCY_LOW,
            timeout=3000,
        )


# Singleton instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get the singleton NotificationManager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
