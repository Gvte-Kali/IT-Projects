"""
Theme Manager - Manages dark/light theme for the application
"""

import json
import logging
from pathlib import Path
from typing import Dict

from .config import CONFIG_DIR

logger = logging.getLogger("ThemeManager")


class ThemeManager:
    """Manages dark/light theme for the application."""
    
    def __init__(self):
        """Initialize theme manager."""
        self.dark_mode = True  # Default to dark mode
        self._load_preference()
    
    def _load_preference(self) -> None:
        """Load theme preference from file."""
        try:
            pref_file = CONFIG_DIR / "theme.json"
            if pref_file.exists():
                with open(pref_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    self.dark_mode = prefs.get("dark_mode", True)
        except Exception as e:
            logger.warning(f"Error loading theme preference: {e}")
    
    def _save_preference(self) -> None:
        """Save theme preference to file."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            pref_file = CONFIG_DIR / "theme.json"
            with open(pref_file, 'w', encoding='utf-8') as f:
                json.dump({"dark_mode": self.dark_mode}, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving theme preference: {e}")
    
    def toggle(self) -> bool:
        """Toggle between dark and light theme."""
        self.dark_mode = not self.dark_mode
        self._save_preference()
        return self.dark_mode
    
    def set_dark(self, dark: bool) -> None:
        """Set dark mode state."""
        self.dark_mode = dark
        self._save_preference()
    
    def get_theme_styles(self) -> Dict[str, str]:
        """Get theme-specific styles."""
        if self.dark_mode:
            return {
                "bg_primary": "#1e1e1e",
                "bg_secondary": "#2d2d2d",
                "bg_tertiary": "#3d3d3d",
                "fg_primary": "#e0e0e0",
                "fg_secondary": "#a0a0a0",
                "accent": "#4a90e2",
                "success": "#28a745",
                "warning": "#ffc107",
                "danger": "#dc3545",
                "border": "#444444",
                "hover": "#3a3a3a",
                "select": "#4a90e2",
            }
        else:
            return {
                "bg_primary": "#f5f5f5",
                "bg_secondary": "#e5e5e5",
                "bg_tertiary": "#d5d5d5",
                "fg_primary": "#1e1e1e",
                "fg_secondary": "#6e6e6e",
                "accent": "#4a90e2",
                "success": "#28a745",
                "warning": "#ffc107",
                "danger": "#dc3545",
                "border": "#cccccc",
                "hover": "#e0e0e0",
                "select": "#4a90e2",
            }
