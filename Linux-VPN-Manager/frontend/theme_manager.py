"""
Theme Manager Module

Manages application theming for different desktop environments.
Supports light, dark, and system theme detection and application.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from enum import Enum
import logging

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication

from backend.de_manager import get_de_manager


class ThemeType(Enum):
    """Theme types supported by the application."""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeManager:
    """Manages application themes and styling."""

    # Theme configurations
    THEME_CONFIGS: Dict[str, Dict[str, Any]] = {
        "light": {
            "name": "Light",
            "palette": {
                "window": "#f5f5f5",
                "window_text": "#212121",
                "base": "#ffffff",
                "alternate_base": "#f0f0f0",
                "tool_tip_base": "#ffffff",
                "tool_tip_text": "#212121",
                "text": "#212121",
                "button": "#e0e0e0",
                "button_text": "#212121",
                "bright_text": "#ff0000",
                "link": "#2196f3",
                "highlight": "#2196f3",
                "highlighted_text": "#ffffff",
            },
            "stylesheet": "",
        },
        "dark": {
            "name": "Dark",
            "palette": {
                "window": "#323232",
                "window_text": "#ffffff",
                "base": "#2d2d2d",
                "alternate_base": "#3d3d3d",
                "tool_tip_base": "#ffffff",
                "tool_tip_text": "#212121",
                "text": "#ffffff",
                "button": "#424242",
                "button_text": "#ffffff",
                "bright_text": "#ff5555",
                "link": "#4da6ff",
                "highlight": "#4da6ff",
                "highlighted_text": "#000000",
            },
            "stylesheet": """
                QMainWindow {
                    background-color: #2d2d2d;
                }
                QListWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #424242;
                }
                QListWidget::item {
                    padding: 4px;
                }
                QListWidget::item:selected {
                    background-color: #4da6ff;
                    color: #000000;
                }
                QPushButton {
                    background-color: #424242;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #525252;
                }
                QPushButton:pressed {
                    background-color: #323232;
                }
                QLabel {
                    color: #ffffff;
                }
                QMenu {
                    background-color: #323232;
                    color: #ffffff;
                    border: 1px solid #424242;
                }
                QMenu::item {
                    padding: 4px 24px 4px 8px;
                }
                QMenu::item:selected {
                    background-color: #4da6ff;
                    color: #000000;
                }
                QStatusBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    background-color: #2d2d2d;
                    border: 1px solid #424242;
                }
                QTabBar::tab {
                    background-color: #323232;
                    color: #ffffff;
                    padding: 6px 12px;
                }
                QTabBar::tab:selected {
                    background-color: #424242;
                }
                QTextEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #424242;
                }
                QComboBox {
                    background-color: #424242;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QComboBox QAbstractItemView {
                    background-color: #424242;
                    color: #ffffff;
                }
                QInputDialog, QMessageBox {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
            """,
        },
    }

    def __init__(self, app: Optional[QApplication] = None):
        """
        Initialize the Theme Manager.

        Args:
            app: QApplication instance (optional)
        """
        self.logger = logging.getLogger("ThemeManager")
        self.app = app
        self._de_manager = None
        self.settings = QSettings("LinuxVPNManager", "VPNManager")
        self._current_theme: Optional[ThemeType] = None

    @property
    def de_manager(self):
        """Get the DEManager instance (lazy loaded)."""
        if self._de_manager is None:
            from backend.de_manager import get_de_manager
            self._de_manager = get_de_manager()
        return self._de_manager

    def detect_system_theme(self) -> ThemeType:
        """
        Detect the current system theme.

        Returns:
            ThemeType: LIGHT, DARK, or SYSTEM
        """
        try:
            system_theme = self.de_manager.get_system_theme()
            if system_theme == "dark":
                return ThemeType.DARK
            elif system_theme == "light":
                return ThemeType.LIGHT
            else:
                return ThemeType.SYSTEM
        except Exception as e:
            self.logger.debug(f"Error detecting system theme: {str(e)}")
            return ThemeType.LIGHT

    def get_user_preference(self) -> ThemeType:
        """
        Get the user's theme preference from settings.

        Returns:
            ThemeType: The user's preferred theme
        """
        theme_str = self.settings.value("theme", "system", type=str)
        try:
            return ThemeType(theme_str)
        except ValueError:
            return ThemeType.SYSTEM

    def set_user_preference(self, theme: ThemeType):
        """
        Set the user's theme preference.

        Args:
            theme: The theme to set as preference
        """
        self.settings.setValue("theme", theme.value)
        self.settings.sync()
        self.logger.info(f"Theme preference set to: {theme.value}")

    @property
    def current_theme(self) -> ThemeType:
        """Get the current effective theme."""
        if self._current_theme is None:
            preference = self.get_user_preference()
            if preference == ThemeType.SYSTEM:
                self._current_theme = self.detect_system_theme()
            else:
                self._current_theme = preference
        return self._current_theme

    def apply_theme(self, app: Optional[QApplication] = None):
        """
        Apply the current theme to the application.

        Args:
            app: QApplication instance to apply the theme to
        """
        if app is None:
            app = self.app

        if app is None:
            self.logger.warning("No QApplication instance provided")
            return

        theme = self.current_theme
        theme_config = self.THEME_CONFIGS.get(theme.value, self.THEME_CONFIGS["light"])

        # Create palette
        palette = QPalette()

        # Set colors from theme config
        palette.setColor(QPalette.ColorRole.Window, QColor(theme_config["palette"]["window"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(theme_config["palette"]["window_text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(theme_config["palette"]["base"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme_config["palette"]["alternate_base"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme_config["palette"]["tool_tip_base"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme_config["palette"]["tool_tip_text"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(theme_config["palette"]["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(theme_config["palette"]["button"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme_config["palette"]["button_text"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(theme_config["palette"]["bright_text"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(theme_config["palette"]["link"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(theme_config["palette"]["highlight"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme_config["palette"]["highlighted_text"]))

        # Set palette for all widgets
        app.setPalette(palette)

        # Apply stylesheet if available
        stylesheet = theme_config.get("stylesheet", "")
        if stylesheet:
            app.setStyleSheet(stylesheet)

        # Set style
        app.setStyle("Fusion")

        self.logger.info(f"Applied {theme.value} theme")

    def get_theme_colors(self) -> Dict[str, str]:
        """
        Get the color palette for the current theme.

        Returns:
            Dict[str, str]: Dictionary of color names to hex values
        """
        theme_config = self.THEME_CONFIGS.get(self.current_theme.value, self.THEME_CONFIGS["light"])
        return theme_config.get("palette", {})

    def get_status_colors(self) -> Dict[str, str]:
        """
        Get status-specific colors based on the current theme.

        Returns:
            Dict[str, str]: Dictionary with status color mappings
        """
        if self.current_theme == ThemeType.DARK:
            return {
                "connected": "#4caf50",  # Green
                "disconnected": "#f44336",  # Red
                "connecting": "#ffc107",  # Amber
                "error": "#ff5722",  # Deep Orange
                "text": "#ffffff",  # White
                "background": "#2d2d2d",  # Dark background
            }
        else:
            return {
                "connected": "#4caf50",  # Green
                "disconnected": "#f44336",  # Red
                "connecting": "#ffc107",  # Amber
                "error": "#ff5722",  # Deep Orange
                "text": "#212121",  # Dark text
                "background": "#f5f5f5",  # Light background
            }

    def get_icon_for_status(self, status: str) -> str:
        """
        Get the appropriate icon name for a connection status.

        Args:
            status: Connection status (UP, DOWN, CONNECTING, ERROR)

        Returns:
            str: Icon name
        """
        status_icons = {
            "UP": "network-vpn",
            "DOWN": "network-vpn-disconnected",
            "CONNECTING": "network-vpn-connecting",
            "ERROR": "dialog-error",
        }
        return status_icons.get(status, "network-vpn")

    def get_color_for_status(self, status: str) -> str:
        """
        Get the appropriate color for a connection status.

        Args:
            status: Connection status (UP, DOWN, CONNECTING, ERROR)

        Returns:
            str: Hex color code
        """
        colors = self.get_status_colors()
        status_colors = {
            "UP": colors["connected"],
            "DOWN": colors["disconnected"],
            "CONNECTING": colors["connecting"],
            "ERROR": colors["error"],
        }
        return status_colors.get(status, colors["text"])

    def toggle_theme(self) -> ThemeType:
        """
        Toggle between light and dark theme.

        Returns:
            ThemeType: The new theme
        """
        current = self.get_user_preference()
        if current == ThemeType.LIGHT:
            new_theme = ThemeType.DARK
        elif current == ThemeType.DARK:
            new_theme = ThemeType.LIGHT
        else:
            # If system, switch to the opposite of detected system theme
            system_theme = self.detect_system_theme()
            new_theme = ThemeType.DARK if system_theme == ThemeType.LIGHT else ThemeType.LIGHT

        self.set_user_preference(new_theme)
        self._current_theme = None  # Force re-detection
        return new_theme

    def reset_to_system(self):
        """Reset theme preference to system default."""
        self.set_user_preference(ThemeType.SYSTEM)
        self._current_theme = None  # Force re-detection


# Singleton instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager(app: Optional[QApplication] = None) -> ThemeManager:
    """
    Get the singleton ThemeManager instance.

    Args:
        app: QApplication instance (optional)

    Returns:
        ThemeManager: The singleton instance
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager(app)
    return _theme_manager
