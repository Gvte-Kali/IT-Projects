"""
Desktop Environment Manager Module

Detects the current desktop environment and provides DE-specific information.
Supports GNOME, KDE, XFCE, LXQt, MATE, Cinnamon, and generic environments.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import logging


class DEManager:
    """Manages desktop environment detection and DE-specific configurations."""

    # List of known desktop environments and their identifiers
    KNOWN_DES = {
        "gnome": ["gnome", "ubuntu:gnome", "unity:gnome"],
        "kde": ["kde", "plasma", "kde-plasma"],
        "xfce": ["xfce", "xubuntu", "xfce4"],
        "lxqt": ["lxqt", "lubuntu:lxqt"],
        "mate": ["mate", "ubuntu-mate"],
        "cinnamon": ["cinnamon", "linuxmint:cinnamon"],
        "budgie": ["budgie", "budgie-desktop"],
        "enlightenment": ["enlightenment", "e17", "e20"],
        "pantheon": ["pantheon", "elementary"],
        "deepin": ["deepin"],
        "sway": ["sway"],
        "i3": ["i3", "i3-with-shmlog"],
    }

    # DE-specific configurations
    DE_CONFIGS: Dict[str, Dict[str, Any]] = {
        "gnome": {
            "name": "GNOME",
            "notification_system": "libnotify",
            "theme_system": "gtk",
            "icon_theme": "Adwaita",
            "uses_dbus": True,
            "dbus_service": "org.gnome.SettingsDaemon",
            "settings_schema": "org.gnome.desktop.interface",
        },
        "kde": {
            "name": "KDE Plasma",
            "notification_system": "knotify",
            "theme_system": "kde",
            "icon_theme": "breeze",
            "uses_dbus": True,
            "dbus_service": "org.kde.kwalletd5",
        },
        "xfce": {
            "name": "XFCE",
            "notification_system": "libnotify",
            "theme_system": "gtk",
            "icon_theme": "elementary-xfce",
            "uses_dbus": False,
        },
        "lxqt": {
            "name": "LXQt",
            "notification_system": "libnotify",
            "theme_system": "qt",
            "icon_theme": "Papirus",
            "uses_dbus": False,
        },
        "mate": {
            "name": "MATE",
            "notification_system": "libnotify",
            "theme_system": "gtk",
            "icon_theme": "Adwaita",
            "uses_dbus": False,
        },
        "cinnamon": {
            "name": "Cinnamon",
            "notification_system": "libnotify",
            "theme_system": "gtk",
            "icon_theme": "Adwaita",
            "uses_dbus": False,
        },
        "generic": {
            "name": "Generic",
            "notification_system": "libnotify",
            "theme_system": "none",
            "icon_theme": "Adwaita",
            "uses_dbus": False,
        },
    }

    def __init__(self):
        """Initialize the DE Manager."""
        self.logger = logging.getLogger("DEManager")
        self._current_de: Optional[str] = None
        self._de_info: Optional[Dict[str, Any]] = None

    def detect(self) -> str:
        """
        Detect the current desktop environment.

        Returns:
            str: The detected desktop environment (e.g., "gnome", "kde", "xfce")
        """
        # Try multiple methods to detect the DE
        de = self._detect_from_environment()
        if de:
            self._current_de = de
            self._de_info = self.DE_CONFIGS.get(de, self.DE_CONFIGS["generic"])
            self.logger.info(f"Detected desktop environment: {de}")
            return de

        de = self._detect_from_processes()
        if de:
            self._current_de = de
            self._de_info = self.DE_CONFIGS.get(de, self.DE_CONFIGS["generic"])
            self.logger.info(f"Detected desktop environment from processes: {de}")
            return de

        de = self._detect_from_xdg()
        if de:
            self._current_de = de
            self._de_info = self.DE_CONFIGS.get(de, self.DE_CONFIGS["generic"])
            self.logger.info(f"Detected desktop environment from XDG: {de}")
            return de

        # Default to generic
        self._current_de = "generic"
        self._de_info = self.DE_CONFIGS["generic"]
        self.logger.warning("Could not detect desktop environment, defaulting to generic")
        return "generic"

    def _detect_from_environment(self) -> Optional[str]:
        """Detect DE from environment variables."""
        # Check XDG_CURRENT_DESKTOP
        xdg_de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if xdg_de:
            for de_name, de_aliases in self.KNOWN_DES.items():
                if xdg_de in de_aliases:
                    return de_name

        # Check DESKTOP_SESSION
        desktop_session = os.environ.get("DESKTOP_SESSION", "").lower()
        if desktop_session:
            for de_name, de_aliases in self.KNOWN_DES.items():
                if desktop_session in de_aliases:
                    return de_name

        return None

    def _detect_from_processes(self) -> Optional[str]:
        """Detect DE from running processes."""
        try:
            # Get list of running processes
            result = subprocess.run(
                ["ps", "-e"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            processes = result.stdout.lower()

            # Check for DE-specific processes
            de_processes = {
                "gnome": ["gnome-session", "gnome-shell"],
                "kde": ["plasmashell", "kded5", "kwin_x11"],
                "xfce": ["xfce4-session", "xfwm4", "xfce4-panel"],
                "lxqt": ["lxqt-session", "lxqt-panel"],
                "mate": ["mate-session", "marco", "caja"],
                "cinnamon": ["cinnamon-session", "cinnamon-desktop"],
                "budgie": ["budgie-desktop"],
                "enlightenment": ["enlightenment"],
                "pantheon": ["pantheon-session", "gala"],
                "deepin": ["deepin-session", "dde-daemon"],
                "sway": ["sway"],
                "i3": ["i3"],
            }

            for de_name, process_names in de_processes.items():
                for process in process_names:
                    if process in processes:
                        return de_name

        except Exception as e:
            self.logger.debug(f"Error detecting DE from processes: {str(e)}")

        return None

    def _detect_from_xdg(self) -> Optional[str]:
        """Detect DE from XDG configuration."""
        try:
            # Check for XDG config files
            xdg_config_dir = Path.home() / ".config"
            if xdg_config_dir.exists():
                # Check for DE-specific config directories
                de_configs = {
                    "gnome": xdg_config_dir / "dconf",
                    "kde": xdg_config_dir / "kded5rc" or xdg_config_dir / "kdeglobals",
                    "xfce": xdg_config_dir / "xfce4",
                    "lxqt": xdg_config_dir / "lxqt",
                    "mate": xdg_config_dir / "dconf" or xdg_config_dir / "mate",
                }

                for de_name, config_path in de_configs.items():
                    if isinstance(config_path, Path):
                        if config_path.exists():
                            return de_name
                    elif any(Path(p).exists() for p in config_path):
                        return de_name

        except Exception as e:
            self.logger.debug(f"Error detecting DE from XDG: {str(e)}")

        return None

    @property
    def current_de(self) -> str:
        """Get the current desktop environment."""
        if self._current_de is None:
            self.detect()
        return self._current_de

    @property
    def de_info(self) -> Dict[str, Any]:
        """Get information about the current desktop environment."""
        if self._de_info is None:
            self.detect()
        return self._de_info

    def get_name(self) -> str:
        """Get the display name of the current DE."""
        return self.de_info.get("name", "Unknown")

    def get_notification_system(self) -> str:
        """Get the notification system used by the current DE."""
        return self.de_info.get("notification_system", "libnotify")

    def get_theme_system(self) -> str:
        """Get the theme system used by the current DE."""
        return self.de_info.get("theme_system", "none")

    def get_icon_theme(self) -> str:
        """Get the default icon theme for the current DE."""
        return self.de_info.get("icon_theme", "Adwaita")

    def uses_dbus(self) -> bool:
        """Check if the current DE uses D-Bus."""
        return self.de_info.get("uses_dbus", False)

    def get_dbus_service(self) -> Optional[str]:
        """Get the D-Bus service for the current DE."""
        return self.de_info.get("dbus_service")

    def is_gnome(self) -> bool:
        """Check if the current DE is GNOME."""
        return self.current_de == "gnome"

    def is_kde(self) -> bool:
        """Check if the current DE is KDE."""
        return self.current_de == "kde"

    def is_xfce(self) -> bool:
        """Check if the current DE is XFCE."""
        return self.current_de == "xfce"

    def is_lxqt(self) -> bool:
        """Check if the current DE is LXQt."""
        return self.current_de == "lxqt"

    def is_mate(self) -> bool:
        """Check if the current DE is MATE."""
        return self.current_de == "mate"

    def is_cinnamon(self) -> bool:
        """Check if the current DE is Cinnamon."""
        return self.current_de == "cinnamon"

    def is_wayland(self) -> bool:
        """Check if the current session is using Wayland."""
        return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"

    def is_x11(self) -> bool:
        """Check if the current session is using X11."""
        return os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11"

    def get_system_theme(self) -> str:
        """
        Get the current system theme (light/dark).

        Returns:
            str: "light", "dark", or "unknown"
        """
        try:
            if self.is_gnome() or self.is_cinnamon() or self.is_mate():
                # Use gsettings for GTK-based DEs
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and "dark" in result.stdout.lower():
                    return "dark"
                return "light"

            elif self.is_kde():
                # Use kreadconfig5 for KDE
                result = subprocess.run(
                    ["kreadconfig5", "--file", "kdeglobals", "--group", "General", "--key", "ColorSchemePath"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and "dark" in result.stdout.lower():
                    return "dark"
                return "light"

            elif self.is_xfce():
                # Use xfconf-query for XFCE
                result = subprocess.run(
                    ["xfconf-query", "-c", "xfce4-desktop", "-p", "/desktop-icons/style"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # XFCE doesn't have a direct dark theme setting, check the theme name
                result = subprocess.run(
                    ["xfconf-query", "-c", "xfce4-settings", "-p", "/Net/ThemeName"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and "dark" in result.stdout.lower():
                    return "dark"
                return "light"

            elif self.is_lxqt():
                # Use lxqt-config for LXQt
                result = subprocess.run(
                    ["lxqt-config", "appearance"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # This is a placeholder - actual implementation would need to parse the output
                return "light"

        except Exception as e:
            self.logger.debug(f"Error detecting system theme: {str(e)}")

        # Fallback: check common environment variables
        if os.environ.get("GTK_THEME", "").lower().find("dark") != -1:
            return "dark"
        if os.environ.get("QT_STYLE_OVERRIDE", "").lower().find("dark") != -1:
            return "dark"

        return "unknown"

    def get_icon_path(self, icon_name: str) -> Optional[str]:
        """
        Get the path to an icon, checking DE-specific locations first.

        Args:
            icon_name: Name of the icon (e.g., "network-vpn", "green")

        Returns:
            str: Path to the icon, or None if not found
        """
        icon_theme = self.get_icon_theme()
        
        # Check standard icon paths for the DE's theme
        icon_paths = [
            f"/usr/share/icons/{icon_theme}/16x16/{icon_name}.png",
            f"/usr/share/icons/{icon_theme}/16x16/status/{icon_name}.png",
            f"/usr/share/icons/{icon_theme}/16x16/actions/{icon_name}.png",
            f"/usr/share/icons/{icon_theme}/scalable/{icon_name}.svg",
            f"/usr/share/icons/{icon_theme}/{icon_name}.png",
            f"/usr/share/icons/{icon_theme}/{icon_name}.svg",
            f"/usr/share/icons/{icon_name}.png",
            f"/usr/share/icons/{icon_name}.svg",
        ]

        for path in icon_paths:
            if Path(path).exists():
                return path

        return None


# Singleton instance
_de_manager: Optional[DEManager] = None


def get_de_manager() -> DEManager:
    """Get the singleton DEManager instance."""
    global _de_manager
    if _de_manager is None:
        _de_manager = DEManager()
    return _de_manager
