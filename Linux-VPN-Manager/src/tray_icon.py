"""
System Tray Icon - Provides system tray integration
"""

import threading
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .config import APP_NAME, APP_VERSION, STATUS_CONNECTED, STATUS_CONNECTING

if TYPE_CHECKING:
    from .vpn_handler import VPNHandler
    from .profile_manager import ProfileManager
    from .theme_manager import ThemeManager

logger = logging.getLogger("SystemTrayIcon")

# Try to import pystray and Pillow
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_SYSTRAY = True
except ImportError:
    HAS_SYSTRAY = False


class SystemTrayIcon:
    """System tray icon for the application."""
    
    def __init__(self, app, vpn_handler: 'VPNHandler', 
                 profile_manager: 'ProfileManager', 
                 theme_manager: 'ThemeManager'):
        """Initialize system tray icon."""
        if not HAS_SYSTRAY:
            logger.warning("System tray not available (pystray/Pillow not installed)")
            return
        
        self.app = app
        self.vpn_handler = vpn_handler
        self.profile_manager = profile_manager
        self.theme_manager = theme_manager
        self.icon = None
        self.icons = self._create_icons()
        self._create_tray_icon()
    
    def _create_icons(self):
        """Create status icons."""
        icons = {}
        
        # Main icon (blue shield)
        icon_size = (64, 64)
        main_icon = Image.new('RGBA', icon_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(main_icon)
        draw.ellipse((10, 10, 54, 45), fill=(74, 144, 226, 255))
        draw.polygon([(32, 10), (50, 35), (14, 35)], fill=(74, 144, 226, 255))
        icons["main"] = main_icon
        
        # Green icon (connected)
        green_icon = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(green_icon)
        draw.ellipse((1, 1, 15, 15), fill=(40, 167, 69, 255))
        icons["green"] = green_icon
        
        # Red icon (disconnected)
        red_icon = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(red_icon)
        draw.ellipse((1, 1, 15, 15), fill=(220, 53, 69, 255))
        icons["red"] = red_icon
        
        # Yellow icon (connecting)
        yellow_icon = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(yellow_icon)
        draw.ellipse((1, 1, 15, 15), fill=(255, 193, 7, 255))
        icons["yellow"] = yellow_icon
        
        return icons
    
    def _create_tray_icon(self) -> None:
        """Create the system tray icon."""
        try:
            menu = pystray.Menu(
                pystray.MenuItem(f"{APP_NAME} v{APP_VERSION}", lambda: None),
                pystray.Menu.SEPARATOR,
            )
            
            self._update_menu()
            
            menu.append(pystray.Menu.SEPARATOR)
            menu.append(pystray.MenuItem("Toggle Theme", lambda: self._toggle_theme()))
            menu.append(pystray.MenuItem("Show", lambda: self._show_app()))
            menu.append(pystray.MenuItem("Quit", lambda: self._quit_app()))
            
            self.icon = pystray.Icon(
                "VPN Manager",
                self.icons["main"],
                f"{APP_NAME} - VPN Manager",
                menu
            )
            
            self.icon_thread = threading.Thread(target=self.icon.run, daemon=True)
            self.icon_thread.start()
            
            self.vpn_handler.register_status_callback(self._on_status_change)
            logger.info("System tray icon created")
            
        except Exception as e:
            logger.error(f"Error creating system tray icon: {e}")
    
    def _update_menu(self) -> None:
        """Update the tray menu with current profiles."""
        try:
            if not self.icon:
                return
            
            new_menu = pystray.Menu(
                pystray.MenuItem(f"{APP_NAME} v{APP_VERSION}", lambda: None),
                pystray.Menu.SEPARATOR,
            )
            
            profiles = self.profile_manager.list_profiles()
            if not profiles:
                new_menu.append(pystray.MenuItem("No profiles", lambda: None, enabled=False))
            else:
                for profile_name in profiles:
                    status, _ = self.vpn_handler.get_status(profile_name)
                    
                    if status == STATUS_CONNECTED:
                        status_text = "[CONNECTED]"
                    elif status == STATUS_CONNECTING:
                        status_text = "[CONNECTING]"
                    else:
                        status_text = "[DISCONNECTED]"
                    
                    def create_handler(pname=profile_name):
                        def handler():
                            self._toggle_connection(pname)
                        return handler
                    
                    new_menu.append(pystray.MenuItem(
                        f"{profile_name} {status_text}", 
                        create_handler()
                    ))
            
            new_menu.append(pystray.Menu.SEPARATOR)
            new_menu.append(pystray.MenuItem("Add Profile", lambda: self._show_app()))
            new_menu.append(pystray.MenuItem("Toggle Theme", lambda: self._toggle_theme()))
            new_menu.append(pystray.MenuItem("Show", lambda: self._show_app()))
            new_menu.append(pystray.MenuItem("Quit", lambda: self._quit_app()))
            
            self.icon.menu = new_menu
            
        except Exception as e:
            logger.error(f"Error updating tray menu: {e}")
    
    def _on_status_change(self, profile_name: str, status: str) -> None:
        """Handle connection status change."""
        try:
            self._update_menu()
            self._update_icon()
        except Exception as e:
            logger.error(f"Error handling status change in tray: {e}")
    
    def _update_icon(self) -> None:
        """Update the tray icon based on connection status."""
        try:
            if not self.icon:
                return
            
            active_count = 0
            connecting_count = 0
            
            for profile_name in self.profile_manager.list_profiles():
                status, _ = self.vpn_handler.get_status(profile_name)
                if status == STATUS_CONNECTED:
                    active_count += 1
                elif status == STATUS_CONNECTING:
                    connecting_count += 1
            
            if active_count > 0:
                self.icon.icon = self.icons["green"]
                self.icon.title = f"{APP_NAME} - {active_count} connected"
            elif connecting_count > 0:
                self.icon.icon = self.icons["yellow"]
                self.icon.title = f"{APP_NAME} - {connecting_count} connecting"
            else:
                self.icon.icon = self.icons["red"]
                self.icon.title = f"{APP_NAME} - Disconnected"
            
            self.icon.update_menu()
            
        except Exception as e:
            logger.error(f"Error updating tray icon: {e}")
    
    def _toggle_connection(self, profile_name: str) -> None:
        """Toggle a VPN connection."""
        try:
            status, _ = self.vpn_handler.get_status(profile_name)
            if status == STATUS_CONNECTED:
                self.vpn_handler.stop_vpn(profile_name)
            else:
                self.vpn_handler.start_vpn(profile_name)
            self._update_menu()
        except Exception as e:
            logger.error(f"Error toggling connection: {e}")
    
    def _show_app(self) -> None:
        """Show the main application window."""
        try:
            self.app.deiconify()
            self.app.lift()
            self.app.focus_force()
        except Exception as e:
            logger.error(f"Error showing app: {e}")
    
    def _quit_app(self) -> None:
        """Quit the application."""
        try:
            self.vpn_handler.stop_all()
            if self.icon:
                self.icon.stop()
            self.app.quit()
            self.app.destroy()
            import sys
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error quitting app: {e}")
    
    def _toggle_theme(self) -> None:
        """Toggle dark/light theme."""
        try:
            self.theme_manager.toggle()
        except Exception as e:
            logger.error(f"Error toggling theme: {e}")
    
    def update(self) -> None:
        """Update the tray icon and menu."""
        try:
            self._update_menu()
            self._update_icon()
        except Exception as e:
            logger.error(f"Error updating tray: {e}")
