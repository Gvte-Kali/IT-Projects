#!/usr/bin/env python3
"""
Linux VPN Manager - Simple & Cross-Distribution
==================================================
A lightweight VPN manager for Linux with Tkinter GUI, system tray support,
DNS leak detection, auto-reconnect, and dark theme.

Supports: OpenVPN and WireGuard
Compatible: apt (Debian/Ubuntu), dnf (Fedora/RHEL), pacman (Arch)

Usage:
    python3 vpn_manager.py

Requirements:
    - Python 3.8+
    - tkinter (usually included with Python)
    - pystray (for system tray): pip install pystray
    - Pillow (for icons): pip install Pillow
    - sudo, openvpn, wireguard-tools (system packages)
"""

import os
import sys
import json
import subprocess
import threading
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import (
    APP_NAME, APP_VERSION, CONFIG_DIR, LOG_DIR, LOG_FILE,
    STATUS_DISCONNECTED, STATUS_CONNECTING, STATUS_CONNECTED, STATUS_FAILED,
    ensure_directories
)
from src.profile_manager import ProfileManager
from src.vpn_handler import VPNHandler
from src.theme_manager import ThemeManager
from src.tray_icon import SystemTrayIcon, HAS_SYSTRAY

# Setup logging
ensure_directories()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("VPNManager")


class VPNManagerApp:
    """Main application class for VPN Manager."""
    
    def __init__(self):
        """Initialize the VPN Manager application."""
        # Initialize managers
        self.profile_manager = ProfileManager()
        self.vpn_handler = VPNHandler(self.profile_manager)
        self.theme_manager = ThemeManager()
        
        # Create root window
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Apply theme
        self._apply_theme()
        
        # Create system tray icon
        self.tray_icon = SystemTrayIcon(
            self.root, self.vpn_handler, 
            self.profile_manager, self.theme_manager
        )
        
        # Initialize UI
        self._init_ui()
        
        # Register callbacks
        self.vpn_handler.register_status_callback(self._on_status_change)
        self.vpn_handler.register_dns_leak_callback(self._on_dns_leak)
        
        # Setup protocol handler for window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Start periodic updates
        self._start_periodic_updates()
        
        logger.info("VPN Manager application initialized")
    
    def _apply_theme(self) -> None:
        """Apply the current theme to the UI."""
        try:
            styles = self.theme_manager.get_theme_styles()
            self.root.configure(bg=styles["bg_primary"], fg=styles["fg_primary"])
            
            style = ttk.Style()
            style.theme_use('clam')
            
            # Configure colors
            style.configure('.', 
                background=styles["bg_primary"], 
                foreground=styles["fg_primary"],
                bordercolor=styles["border"],
                darkcolor=styles["bg_primary"],
                lightcolor=styles["bg_secondary"]
            )
            
            style.configure('TFrame', background=styles["bg_primary"])
            style.configure('TLabel', background=styles["bg_primary"], foreground=styles["fg_primary"])
            style.configure('TButton', 
                background=styles["bg_secondary"], 
                foreground=styles["fg_primary"],
                bordercolor=styles["border"]
            )
            style.map('TButton', 
                background=[('active', styles["hover"]), ('pressed', styles["bg_tertiary"])]
            )
            style.configure('Treeview', 
                background=styles["bg_secondary"], 
                foreground=styles["fg_primary"],
                fieldbackground=styles["bg_secondary"],
                bordercolor=styles["border"]
            )
            style.configure('Treeview.Heading', 
                background=styles["bg_tertiary"], 
                foreground=styles["fg_primary"]
            )
            style.map('Treeview', background=[('selected', styles["select"])])
            style.configure('TEntry', 
                background=styles["bg_secondary"], 
                foreground=styles["fg_primary"],
                fieldbackground=styles["bg_secondary"],
                bordercolor=styles["border"]
            )
            style.configure('TCombobox', 
                background=styles["bg_secondary"], 
                foreground=styles["fg_primary"],
                fieldbackground=styles["bg_secondary"],
                bordercolor=styles["border"]
            )
            style.configure('Vertical.TScrollbar', 
                background=styles["bg_secondary"],
                bordercolor=styles["border"],
                arrowcolor=styles["fg_primary"]
            )
            
            # Update existing widgets
            if hasattr(self, 'main_frame'):
                self._refresh_ui_theme()
                
        except Exception as e:
            logger.error(f"Error applying theme: {e}")
    
    def _refresh_ui_theme(self) -> None:
        """Refresh UI elements with current theme."""
        try:
            styles = self.theme_manager.get_theme_styles()
            if hasattr(self, 'main_frame'):
                self.main_frame.configure(bg=styles["bg_primary"])
            for widget in self.root.winfo_children():
                self._update_widget_theme(widget, styles)
        except Exception as e:
            logger.error(f"Error refreshing UI theme: {e}")
    
    def _update_widget_theme(self, widget, styles) -> None:
        """Recursively update widget theme."""
        try:
            widget_class = widget.winfo_class()
            if widget_class in ['Frame', 'TFrame', 'Labelframe']:
                widget.configure(bg=styles["bg_primary"])
            elif widget_class in ['Label', 'TLabel']:
                widget.configure(bg=styles["bg_primary"], fg=styles["fg_primary"])
            elif widget_class in ['Button', 'TButton']:
                widget.configure(
                    bg=styles["bg_secondary"], 
                    fg=styles["fg_primary"],
                    activebackground=styles["hover"],
                    activeforeground=styles["fg_primary"]
                )
            elif widget_class in ['Entry', 'TEntry']:
                widget.configure(
                    bg=styles["bg_secondary"], 
                    fg=styles["fg_primary"],
                    insertbackground=styles["fg_primary"]
                )
            elif widget_class in ['Text']:
                widget.configure(
                    bg=styles["bg_secondary"], 
                    fg=styles["fg_primary"],
                    insertbackground=styles["fg_primary"]
                )
            
            for child in widget.winfo_children():
                self._update_widget_theme(child, styles)
        except Exception as e:
            logger.warning(f"Error updating widget theme: {e}")
    
    def _init_ui(self) -> None:
        """Initialize the user interface."""
        try:
            self.main_frame = ttk.Frame(self.root, padding=10)
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create notebook (tabs)
            self.notebook = ttk.Notebook(self.main_frame)
            self.notebook.pack(fill=tk.BOTH, expand=True)
            
            # Create tabs
            self._init_connections_tab()
            self._init_profiles_tab()
            self._init_logs_tab()
            self._init_settings_tab()
            
            # Status bar
            self._init_status_bar()
            
            # Update connections list
            self._refresh_connections_list()
            
        except Exception as e:
            logger.error(f"Error initializing UI: {e}")
    
    def _init_connections_tab(self) -> None:
        """Initialize the connections tab."""
        try:
            connections_frame = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(connections_frame, text="Connections")
            
            main_layout = ttk.Frame(connections_frame)
            main_layout.pack(fill=tk.BOTH, expand=True)
            
            # Top bar with controls
            top_bar = ttk.Frame(main_layout)
            top_bar.pack(fill=tk.X, pady=(0, 10))
            
            refresh_btn = ttk.Button(top_bar, text="Refresh", command=self._refresh_connections_list)
            refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self.status_filter = tk.StringVar(value="all")
            status_combo = ttk.Combobox(
                top_bar, 
                textvariable=self.status_filter,
                values=["all", "connected", "disconnected", "connecting", "failed"],
                state="readonly",
                width=12
            )
            status_combo.pack(side=tk.LEFT, padx=(0, 10))
            status_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_connections_list())
            
            # Search box
            search_frame = ttk.Frame(top_bar)
            search_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
            search_label = ttk.Label(search_frame, text="Search:")
            search_label.pack(side=tk.LEFT, padx=(0, 5))
            self.search_var = tk.StringVar()
            search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
            search_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
            search_entry.bind("<KeyRelease>", lambda e: self._filter_connections())
            
            # Connections list (Treeview)
            list_frame = ttk.Frame(main_layout)
            list_frame.pack(fill=tk.BOTH, expand=True)
            
            columns = ("status", "name", "type", "path", "duration", "dns")
            self.connections_tree = ttk.Treeview(
                list_frame, 
                columns=columns, 
                show="headings", 
                selectmode="browse"
            )
            
            self.connections_tree.heading("status", text="Status", anchor=tk.CENTER)
            self.connections_tree.heading("name", text="Name", anchor=tk.W)
            self.connections_tree.heading("type", text="Type", anchor=tk.W)
            self.connections_tree.heading("path", text="Config Path", anchor=tk.W)
            self.connections_tree.heading("duration", text="Duration", anchor=tk.W)
            self.connections_tree.heading("dns", text="DNS", anchor=tk.CENTER)
            
            self.connections_tree.column("status", width=80, anchor=tk.CENTER)
            self.connections_tree.column("name", width=150, anchor=tk.W)
            self.connections_tree.column("type", width=100, anchor=tk.W)
            self.connections_tree.column("path", width=300, anchor=tk.W)
            self.connections_tree.column("duration", width=100, anchor=tk.W)
            self.connections_tree.column("dns", width=80, anchor=tk.CENTER)
            
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.connections_tree.yview)
            self.connections_tree.configure(yscrollcommand=scrollbar.set)
            self.connections_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.connections_tree.bind("<Double-1>", self._on_connection_double_click)
            
            # Bottom bar with action buttons
            bottom_bar = ttk.Frame(main_layout)
            bottom_bar.pack(fill=tk.X, pady=(10, 0))
            
            connect_btn = ttk.Button(bottom_bar, text="Connect", command=self._connect_selected)
            connect_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            disconnect_btn = ttk.Button(bottom_bar, text="Disconnect", command=self._disconnect_selected)
            disconnect_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            disconnect_all_btn = ttk.Button(bottom_bar, text="Disconnect All", command=self._disconnect_all)
            disconnect_all_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            logs_btn = ttk.Button(bottom_bar, text="View Logs", command=self._view_logs_selected)
            logs_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            edit_btn = ttk.Button(bottom_bar, text="Edit", command=self._edit_selected)
            edit_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            remove_btn = ttk.Button(bottom_bar, text="Remove", command=self._remove_selected)
            remove_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self.connections_tree.bind("<Button-3>", self._show_context_menu)
            
        except Exception as e:
            logger.error(f"Error initializing connections tab: {e}")
    
    def _init_profiles_tab(self) -> None:
        """Initialize the profiles tab."""
        try:
            profiles_frame = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(profiles_frame, text="Profiles")
            
            main_layout = ttk.Frame(profiles_frame)
            main_layout.pack(fill=tk.BOTH, expand=True)
            
            list_frame = ttk.Frame(main_layout)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            columns = ("name", "type", "path", "args")
            self.profiles_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
            
            self.profiles_tree.heading("name", text="Name", anchor=tk.W)
            self.profiles_tree.heading("type", text="Type", anchor=tk.W)
            self.profiles_tree.heading("path", text="Config Path", anchor=tk.W)
            self.profiles_tree.heading("args", text="Extra Args", anchor=tk.W)
            
            self.profiles_tree.column("name", width=150, anchor=tk.W)
            self.profiles_tree.column("type", width=100, anchor=tk.W)
            self.profiles_tree.column("path", width=300, anchor=tk.W)
            self.profiles_tree.column("args", width=200, anchor=tk.W)
            
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.profiles_tree.yview)
            self.profiles_tree.configure(yscrollcommand=scrollbar.set)
            self.profiles_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.profiles_tree.bind("<Double-1>", self._on_profile_double_click)
            
            buttons_frame = ttk.Frame(main_layout)
            buttons_frame.pack(fill=tk.X)
            
            add_btn = ttk.Button(buttons_frame, text="Add Profile", command=self._add_profile)
            add_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            edit_btn = ttk.Button(buttons_frame, text="Edit Profile", command=self._edit_profile)
            edit_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            remove_btn = ttk.Button(buttons_frame, text="Remove Profile", command=self._remove_profile)
            remove_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            import_btn = ttk.Button(buttons_frame, text="Import Profile", command=self._import_profile)
            import_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self._refresh_profiles_list()
            
        except Exception as e:
            logger.error(f"Error initializing profiles tab: {e}")
    
    def _init_logs_tab(self) -> None:
        """Initialize the logs tab."""
        try:
            logs_frame = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(logs_frame, text="Logs")
            
            main_layout = ttk.Frame(logs_frame)
            main_layout.pack(fill=tk.BOTH, expand=True)
            
            self.log_text = tk.Text(main_layout, wrap=tk.WORD, state=tk.DISABLED)
            scrollbar = ttk.Scrollbar(main_layout, orient=tk.VERTICAL, command=self.log_text.yview)
            self.log_text.configure(yscrollcommand=scrollbar.set)
            self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            bottom_bar = ttk.Frame(main_layout)
            bottom_bar.pack(fill=tk.X, pady=(10, 0))
            
            clear_btn = ttk.Button(bottom_bar, text="Clear Logs", command=self._clear_logs)
            clear_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            export_btn = ttk.Button(bottom_bar, text="Export Logs", command=self._export_logs)
            export_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self.auto_scroll = tk.BooleanVar(value=True)
            auto_scroll_cb = ttk.Checkbutton(bottom_bar, text="Auto-scroll", variable=self.auto_scroll)
            auto_scroll_cb.pack(side=tk.LEFT, padx=(0, 10))
            
            self._load_logs()
            
        except Exception as e:
            logger.error(f"Error initializing logs tab: {e}")
    
    def _init_settings_tab(self) -> None:
        """Initialize the settings tab."""
        try:
            settings_frame = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(settings_frame, text="Settings")
            
            main_layout = ttk.Frame(settings_frame)
            main_layout.pack(fill=tk.BOTH, expand=True)
            
            # Theme settings
            theme_frame = ttk.LabelFrame(main_layout, text="Theme", padding=10)
            theme_frame.pack(fill=tk.X, pady=(0, 10))
            
            theme_btn = ttk.Button(
                theme_frame, 
                text="Toggle Dark/Light Theme", 
                command=self._toggle_theme
            )
            theme_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self.theme_label = ttk.Label(
                theme_frame, 
                text=f"Current: {'Dark' if self.theme_manager.dark_mode else 'Light'} Mode"
            )
            self.theme_label.pack(side=tk.LEFT)
            
            # DNS Leak Detection settings
            dns_frame = ttk.LabelFrame(main_layout, text="DNS Leak Detection", padding=10)
            dns_frame.pack(fill=tk.X, pady=(0, 10))
            
            check_dns_btn = ttk.Button(dns_frame, text="Check DNS Leak Now", command=self._check_dns_leak)
            check_dns_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self.dns_status_label = ttk.Label(dns_frame, text="DNS Status: Not checked")
            self.dns_status_label.pack(side=tk.LEFT)
            
            # About section
            about_frame = ttk.LabelFrame(main_layout, text="About", padding=10)
            about_frame.pack(fill=tk.X, pady=(0, 10))
            
            about_text = f"{APP_NAME} v{APP_VERSION}\n\nA simple VPN manager for Linux.\nSupports OpenVPN and WireGuard.\n\nAuthor: Gvte-Kali\nLicense: MIT"
            about_label = ttk.Label(about_frame, text=about_text, justify=tk.LEFT)
            about_label.pack(side=tk.LEFT)
            
        except Exception as e:
            logger.error(f"Error initializing settings tab: {e}")
    
    def _init_status_bar(self) -> None:
        """Initialize the status bar."""
        try:
            status_frame = ttk.Frame(self.main_frame)
            status_frame.pack(fill=tk.X, pady=(10, 0))
            
            self.status_label = ttk.Label(
                status_frame, 
                text=f"Ready - {len(self.profile_manager.list_profiles())} profiles loaded",
                relief=tk.SUNKEN,
                anchor=tk.W
            )
            self.status_label.pack(fill=tk.X, expand=True)
        except Exception as e:
            logger.error(f"Error initializing status bar: {e}")
    
    # Connection Management
    def _refresh_connections_list(self) -> None:
        """Refresh the connections list."""
        try:
            for item in self.connections_tree.get_children():
                self.connections_tree.delete(item)
            
            status_filter = self.status_filter.get()
            search_text = self.search_var.get().lower()
            
            for profile_name in self.profile_manager.list_profiles():
                profile = self.profile_manager.get_profile(profile_name)
                if not profile:
                    continue
                
                status, _ = self.vpn_handler.get_status(profile_name)
                
                if status_filter != "all" and status != status_filter:
                    continue
                
                if search_text and search_text not in profile_name.lower():
                    continue
                
                conn_info = self.vpn_handler.get_connection_info(profile_name)
                duration = "-"
                if conn_info and "start_time" in conn_info:
                    try:
                        start_time = datetime.fromisoformat(conn_info["start_time"])
                        duration = str(datetime.now() - start_time).split('.')[0]
                    except Exception:
                        pass
                
                dns_status = "OK"
                if conn_info and conn_info.get("dns_leak_detected", False):
                    dns_status = "LEAK"
                
                if status == STATUS_CONNECTED:
                    status_text = "[OK]"
                elif status == STATUS_CONNECTING:
                    status_text = "[...]"
                elif status == STATUS_FAILED:
                    status_text = "[ERR]"
                else:
                    status_text = "[X]"
                
                self.connections_tree.insert(
                    "", 
                    tk.END, 
                    values=(f"{status_text} {status}", profile_name, profile.get("type", "unknown"), profile.get("path", ""), duration, dns_status),
                    tags=(profile_name,)
                )
            
            active_count = sum(1 for p in self.profile_manager.list_profiles() if self.vpn_handler.get_status(p)[0] == STATUS_CONNECTED)
            total_count = len(self.profile_manager.list_profiles())
            self.status_label.configure(text=f"{active_count} connected / {total_count} profiles")
            
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.update()
                
        except Exception as e:
            logger.error(f"Error refreshing connections list: {e}")
    
    def _filter_connections(self) -> None:
        """Filter connections based on search text."""
        self._refresh_connections_list()
    
    def _connect_selected(self) -> None:
        """Connect to the selected profile."""
        try:
            selected = self.connections_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a connection")
                return
            
            profile_name = self.connections_tree.item(selected[0], "tags")[0]
            status, _ = self.vpn_handler.get_status(profile_name)
            
            if status == STATUS_CONNECTED:
                messagebox.showinfo("Info", f"'{profile_name}' is already connected")
                return
            
            success, message = self.vpn_handler.start_vpn(profile_name)
            
            if success:
                messagebox.showinfo("Success", message)
                self._refresh_connections_list()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            logger.error(f"Error connecting: {e}")
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
    
    def _disconnect_selected(self) -> None:
        """Disconnect the selected profile."""
        try:
            selected = self.connections_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a connection")
                return
            
            profile_name = self.connections_tree.item(selected[0], "tags")[0]
            status, _ = self.vpn_handler.get_status(profile_name)
            
            if status not in [STATUS_CONNECTED, STATUS_CONNECTING]:
                messagebox.showinfo("Info", f"'{profile_name}' is not connected")
                return
            
            success, message = self.vpn_handler.stop_vpn(profile_name)
            
            if success:
                messagebox.showinfo("Success", message)
                self._refresh_connections_list()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            messagebox.showerror("Error", f"Failed to disconnect: {str(e)}")
    
    def _disconnect_all(self) -> None:
        """Disconnect all active connections."""
        try:
            active_profiles = [
                p for p in self.profile_manager.list_profiles()
                if self.vpn_handler.get_status(p)[0] in [STATUS_CONNECTED, STATUS_CONNECTING]
            ]
            
            if not active_profiles:
                messagebox.showinfo("Info", "No active connections to disconnect")
                return
            
            if not messagebox.askyesno("Confirm", f"Disconnect all {len(active_profiles)} active connections?"):
                return
            
            results = self.vpn_handler.stop_all()
            failed = [name for name, (success, _) in results.items() if not success]
            
            if failed:
                messagebox.showwarning("Warning", f"Failed to disconnect: {', '.join(failed)}")
            else:
                messagebox.showinfo("Success", "All connections disconnected")
            
            self._refresh_connections_list()
            
        except Exception as e:
            logger.error(f"Error disconnecting all: {e}")
            messagebox.showerror("Error", f"Failed to disconnect all: {str(e)}")
    
    def _view_logs_selected(self) -> None:
        """View logs for the selected profile."""
        try:
            selected = self.connections_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a connection")
                return
            
            profile_name = self.connections_tree.item(selected[0], "tags")[0]
            self.notebook.select(2)
            self._show_profile_logs(profile_name)
            
        except Exception as e:
            logger.error(f"Error viewing logs: {e}")
            messagebox.showerror("Error", f"Failed to view logs: {str(e)}")
    
    def _edit_selected(self) -> None:
        """Edit the selected profile."""
        try:
            selected = self.connections_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a connection")
                return
            
            profile_name = self.connections_tree.item(selected[0], "tags")[0]
            self.notebook.select(1)
            self._edit_profile_dialog(profile_name)
            
        except Exception as e:
            logger.error(f"Error editing: {e}")
            messagebox.showerror("Error", f"Failed to edit: {str(e)}")
    
    def _remove_selected(self) -> None:
        """Remove the selected profile."""
        try:
            selected = self.connections_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a connection")
                return
            
            profile_name = self.connections_tree.item(selected[0], "tags")[0]
            status, _ = self.vpn_handler.get_status(profile_name)
            
            if status in [STATUS_CONNECTED, STATUS_CONNECTING]:
                if not messagebox.askyesno("Warning", f"'{profile_name}' is connected. Disconnect first?"):
                    return
                self.vpn_handler.stop_vpn(profile_name)
            
            if messagebox.askyesno("Confirm", f"Remove profile '{profile_name}'?"):
                success, message = self.profile_manager.remove_profile(profile_name)
                if success:
                    messagebox.showinfo("Success", message)
                    self._refresh_connections_list()
                    self._refresh_profiles_list()
                else:
                    messagebox.showerror("Error", message)
                    
        except Exception as e:
            logger.error(f"Error removing: {e}")
            messagebox.showerror("Error", f"Failed to remove: {str(e)}")
    
    def _on_connection_double_click(self, event) -> None:
        """Handle double click on connection."""
        try:
            selected = self.connections_tree.selection()
            if selected:
                profile_name = self.connections_tree.item(selected[0], "tags")[0]
                status, _ = self.vpn_handler.get_status(profile_name)
                
                if status == STATUS_CONNECTED:
                    self.vpn_handler.stop_vpn(profile_name)
                else:
                    self.vpn_handler.start_vpn(profile_name)
                
                self._refresh_connections_list()
                
        except Exception as e:
            logger.error(f"Error on double click: {e}")
    
    def _show_context_menu(self, event) -> None:
        """Show context menu for connections."""
        try:
            selected = self.connections_tree.selection()
            if not selected:
                return
            
            profile_name = self.connections_tree.item(selected[0], "tags")[0]
            status, _ = self.vpn_handler.get_status(profile_name)
            
            menu = tk.Menu(self.root, tearoff=0)
            
            if status == STATUS_CONNECTED:
                menu.add_command(label="Disconnect", command=lambda: self._disconnect_profile(profile_name))
            else:
                menu.add_command(label="Connect", command=lambda: self._connect_profile(profile_name))
            
            menu.add_separator()
            menu.add_command(label="View Logs", command=lambda: self._show_profile_logs(profile_name))
            menu.add_command(label="Edit", command=lambda: self._edit_profile_dialog(profile_name))
            menu.add_command(label="Remove", command=lambda: self._remove_profile_dialog(profile_name))
            
            menu.tk_popup(event.x_root, event.y_root)
            
        except Exception as e:
            logger.error(f"Error showing context menu: {e}")
    
    def _connect_profile(self, profile_name) -> None:
        """Connect to a profile."""
        success, message = self.vpn_handler.start_vpn(profile_name)
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
        self._refresh_connections_list()
    
    def _disconnect_profile(self, profile_name) -> None:
        """Disconnect from a profile."""
        success, message = self.vpn_handler.stop_vpn(profile_name)
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
        self._refresh_connections_list()
    
    # Profile Management
    def _refresh_profiles_list(self) -> None:
        """Refresh the profiles list."""
        try:
            for item in self.profiles_tree.get_children():
                self.profiles_tree.delete(item)
            
            for profile_name in self.profile_manager.list_profiles():
                profile = self.profile_manager.get_profile(profile_name)
                if not profile:
                    continue
                
                self.profiles_tree.insert(
                    "", 
                    tk.END, 
                    values=(
                        profile_name,
                        profile.get("type", "unknown"),
                        profile.get("path", ""),
                        profile.get("extra_args", "")
                    ),
                    tags=(profile_name,)
                )
                
        except Exception as e:
            logger.error(f"Error refreshing profiles list: {e}")
    
    def _add_profile(self) -> None:
        """Add a new profile."""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("Add Profile")
            dialog.transient(self.root)
            dialog.grab_set()
            
            form_frame = ttk.Frame(dialog, padding=10)
            form_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(form_frame, text="Profile Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
            name_entry = ttk.Entry(form_frame, width=40)
            name_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(form_frame, text="Config Path:").grid(row=1, column=0, sticky=tk.W, pady=5)
            path_frame = ttk.Frame(form_frame)
            path_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
            path_entry = ttk.Entry(path_frame, width=35)
            path_entry.pack(side=tk.LEFT)
            browse_btn = ttk.Button(path_frame, text="Browse...", command=lambda: self._browse_config(path_entry))
            browse_btn.pack(side=tk.LEFT, padx=(5, 0))
            
            ttk.Label(form_frame, text="VPN Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
            vpn_type_var = tk.StringVar(value="auto")
            vpn_type_combo = ttk.Combobox(
                form_frame, 
                textvariable=vpn_type_var,
                values=["auto", "openvpn", "wireguard"],
                state="readonly",
                width=15
            )
            vpn_type_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(form_frame, text="Extra Args (optional):").grid(row=3, column=0, sticky=tk.W, pady=5)
            args_entry = ttk.Entry(form_frame, width=40)
            args_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
            
            button_frame = ttk.Frame(form_frame)
            button_frame.grid(row=4, column=0, columnspan=2, pady=10)
            ok_btn = ttk.Button(
                button_frame, 
                text="OK", 
                command=lambda: self._add_profile_confirm(
                    dialog, name_entry.get(), path_entry.get(), 
                    vpn_type_var.get(), args_entry.get()
                )
            )
            ok_btn.pack(side=tk.LEFT, padx=(0, 10))
            cancel_btn = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
            cancel_btn.pack(side=tk.LEFT)
            
            name_entry.focus_set()
            
        except Exception as e:
            logger.error(f"Error creating add profile dialog: {e}")
            messagebox.showerror("Error", f"Failed to create dialog: {str(e)}")
    
    def _add_profile_confirm(self, dialog, name, path, vpn_type, args) -> None:
        """Confirm and add a new profile."""
        try:
            if not name or not name.strip():
                messagebox.showerror("Error", "Profile name cannot be empty", parent=dialog)
                return
            if not path or not path.strip():
                messagebox.showerror("Error", "Config path cannot be empty", parent=dialog)
                return
            
            success, message = self.profile_manager.add_profile(name, path, vpn_type, args)
            if success:
                messagebox.showinfo("Success", message, parent=dialog)
                dialog.destroy()
                self._refresh_profiles_list()
                self._refresh_connections_list()
            else:
                messagebox.showerror("Error", message, parent=dialog)
                
        except Exception as e:
            logger.error(f"Error adding profile: {e}")
            messagebox.showerror("Error", f"Failed to add profile: {str(e)}", parent=dialog)
    
    def _browse_config(self, entry) -> None:
        """Browse for a configuration file."""
        try:
            filetypes = [("OpenVPN Config", "*.ovpn"), ("WireGuard Config", "*.conf"), ("All Files", "*.*")]
            filename = filedialog.askopenfilename(title="Select VPN Configuration File", filetypes=filetypes)
            if filename:
                entry.delete(0, tk.END)
                entry.insert(0, filename)
        except Exception as e:
            logger.error(f"Error browsing for config: {e}")
            messagebox.showerror("Error", f"Failed to browse: {str(e)}")
    
    def _edit_profile_dialog(self, profile_name=None) -> None:
        """Show edit profile dialog."""
        try:
            profile = None
            if profile_name:
                profile = self.profile_manager.get_profile(profile_name)
            
            dialog = tk.Toplevel(self.root)
            dialog.title(f"{'Edit' if profile_name else 'Add'} Profile")
            dialog.transient(self.root)
            dialog.grab_set()
            
            form_frame = ttk.Frame(dialog, padding=10)
            form_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(form_frame, text="Profile Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
            name_entry = ttk.Entry(form_frame, width=40)
            name_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
            if profile:
                name_entry.insert(0, profile_name)
            
            ttk.Label(form_frame, text="Config Path:").grid(row=1, column=0, sticky=tk.W, pady=5)
            path_frame = ttk.Frame(form_frame)
            path_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
            path_entry = ttk.Entry(path_frame, width=35)
            path_entry.pack(side=tk.LEFT)
            if profile:
                path_entry.insert(0, profile.get("path", ""))
            browse_btn = ttk.Button(path_frame, text="Browse...", command=lambda: self._browse_config(path_entry))
            browse_btn.pack(side=tk.LEFT, padx=(5, 0))
            
            ttk.Label(form_frame, text="VPN Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
            vpn_type_var = tk.StringVar(value=profile.get("type", "auto") if profile else "auto")
            vpn_type_combo = ttk.Combobox(
                form_frame, 
                textvariable=vpn_type_var,
                values=["auto", "openvpn", "wireguard"],
                state="readonly",
                width=15
            )
            vpn_type_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(form_frame, text="Extra Args (optional):").grid(row=3, column=0, sticky=tk.W, pady=5)
            args_entry = ttk.Entry(form_frame, width=40)
            args_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
            if profile:
                args_entry.insert(0, profile.get("extra_args", ""))
            
            button_frame = ttk.Frame(form_frame)
            button_frame.grid(row=4, column=0, columnspan=2, pady=10)
            
            if profile_name:
                ok_btn = ttk.Button(
                    button_frame, 
                    text="Save", 
                    command=lambda: self._edit_profile_confirm(
                        dialog, profile_name, name_entry.get(), path_entry.get(),
                        vpn_type_var.get(), args_entry.get()
                    )
                )
            else:
                ok_btn = ttk.Button(
                    button_frame, 
                    text="Add", 
                    command=lambda: self._add_profile_confirm(
                        dialog, name_entry.get(), path_entry.get(),
                        vpn_type_var.get(), args_entry.get()
                    )
                )
            ok_btn.pack(side=tk.LEFT, padx=(0, 10))
            cancel_btn = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
            cancel_btn.pack(side=tk.LEFT)
            
            name_entry.focus_set()
            
        except Exception as e:
            logger.error(f"Error creating edit profile dialog: {e}")
            messagebox.showerror("Error", f"Failed to create dialog: {str(e)}")
    
    def _edit_profile_confirm(self, dialog, old_name, new_name, path, vpn_type, args) -> None:
        """Confirm and save profile changes."""
        try:
            if not new_name or not new_name.strip():
                messagebox.showerror("Error", "Profile name cannot be empty", parent=dialog)
                return
            if not path or not path.strip():
                messagebox.showerror("Error", "Config path cannot be empty", parent=dialog)
                return
            
            success, message = self.profile_manager.update_profile(old_name, new_name, path, vpn_type, args)
            if success:
                messagebox.showinfo("Success", message, parent=dialog)
                dialog.destroy()
                self._refresh_profiles_list()
                self._refresh_connections_list()
            else:
                messagebox.showerror("Error", message, parent=dialog)
                
        except Exception as e:
            logger.error(f"Error editing profile: {e}")
            messagebox.showerror("Error", f"Failed to edit profile: {str(e)}", parent=dialog)
    
    def _edit_profile(self) -> None:
        """Edit the selected profile."""
        try:
            selected = self.profiles_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a profile")
                return
            profile_name = self.profiles_tree.item(selected[0], "tags")[0]
            self._edit_profile_dialog(profile_name)
        except Exception as e:
            logger.error(f"Error editing profile: {e}")
            messagebox.showerror("Error", f"Failed to edit profile: {str(e)}")
    
    def _remove_profile_dialog(self, profile_name) -> None:
        """Show remove profile confirmation dialog."""
        try:
            status, _ = self.vpn_handler.get_status(profile_name)
            if status in [STATUS_CONNECTED, STATUS_CONNECTING]:
                if not messagebox.askyesno("Warning", f"'{profile_name}' is connected. Disconnect first?"):
                    return
                self.vpn_handler.stop_vpn(profile_name)
            
            if messagebox.askyesno("Confirm", f"Remove profile '{profile_name}'?"):
                success, message = self.profile_manager.remove_profile(profile_name)
                if success:
                    messagebox.showinfo("Success", message)
                    self._refresh_profiles_list()
                    self._refresh_connections_list()
                else:
                    messagebox.showerror("Error", message)
        except Exception as e:
            logger.error(f"Error removing profile: {e}")
            messagebox.showerror("Error", f"Failed to remove profile: {str(e)}")
    
    def _remove_profile(self) -> None:
        """Remove the selected profile."""
        try:
            selected = self.profiles_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a profile")
                return
            profile_name = self.profiles_tree.item(selected[0], "tags")[0]
            self._remove_profile_dialog(profile_name)
        except Exception as e:
            logger.error(f"Error removing profile: {e}")
            messagebox.showerror("Error", f"Failed to remove profile: {str(e)}")
    
    def _import_profile(self) -> None:
        """Import a profile from file."""
        try:
            filetypes = [("JSON Files", "*.json"), ("All Files", "*.*")]
            filename = filedialog.askopenfilename(title="Import Profile", filetypes=filetypes)
            if not filename:
                return
            
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                if not isinstance(profiles, dict):
                    messagebox.showerror("Error", "Invalid profile format")
                    return
                
                imported = 0
                for name, profile_data in profiles.items():
                    success, _ = self.profile_manager.add_profile(
                        name,
                        profile_data.get("path", ""),
                        profile_data.get("type", "auto"),
                        profile_data.get("extra_args", "")
                    )
                    if success:
                        imported += 1
                
                messagebox.showinfo("Success", f"Imported {imported} of {len(profiles)} profiles")
                self._refresh_profiles_list()
                self._refresh_connections_list()
                
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error importing profile: {e}")
            messagebox.showerror("Error", f"Failed to import: {str(e)}")
    
    def _on_profile_double_click(self, event) -> None:
        """Handle double click on profile."""
        try:
            selected = self.profiles_tree.selection()
            if selected:
                profile_name = self.profiles_tree.item(selected[0], "tags")[0]
                self._edit_profile_dialog(profile_name)
        except Exception as e:
            logger.error(f"Error on profile double click: {e}")
    
    # Logs Management
    def _load_logs(self) -> None:
        """Load logs into the text widget."""
        try:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            if LOG_FILE.exists():
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.log_text.insert(tk.END, content)
            else:
                self.log_text.insert(tk.END, "No logs available")
            self.log_text.configure(state=tk.DISABLED)
            self.log_text.see(tk.END)
        except Exception as e:
            logger.error(f"Error loading logs: {e}")
    
    def _show_profile_logs(self, profile_name) -> None:
        """Show logs for a specific profile."""
        try:
            self.notebook.select(2)
            profile = self.profile_manager.get_profile(profile_name)
            if not profile:
                messagebox.showerror("Error", f"Profile '{profile_name}' not found")
                return
            
            profile_log_dir = LOG_DIR / profile_name
            profile_log_dir.mkdir(parents=True, exist_ok=True)
            profile_log_file = profile_log_dir / f"{profile_name}.log"
            
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            
            if profile_log_file.exists():
                with open(profile_log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.log_text.insert(tk.END, f"=== Logs for {profile_name} ===\n\n{content}")
            else:
                self.log_text.insert(tk.END, f"No logs available for {profile_name}")
            
            self.log_text.configure(state=tk.DISABLED)
            self.log_text.see(tk.END)
            
        except Exception as e:
            logger.error(f"Error showing profile logs: {e}")
            messagebox.showerror("Error", f"Failed to show logs: {str(e)}")
    
    def _clear_logs(self) -> None:
        """Clear the logs."""
        try:
            if messagebox.askyesno("Confirm", "Clear all logs?"):
                if LOG_FILE.exists():
                    LOG_FILE.unlink()
                for profile_name in self.profile_manager.list_profiles():
                    profile_log_dir = LOG_DIR / profile_name
                    if profile_log_dir.exists():
                        for log_file in profile_log_dir.glob("*.log"):
                            log_file.unlink()
                self._load_logs()
                messagebox.showinfo("Success", "Logs cleared")
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            messagebox.showerror("Error", f"Failed to clear logs: {str(e)}")
    
    def _export_logs(self) -> None:
        """Export logs to a file."""
        try:
            filename = filedialog.asksaveasfilename(
                title="Export Logs",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            if not filename:
                return
            
            all_logs = []
            if LOG_FILE.exists():
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    all_logs.append(f"=== Main Log ===\n{f.read()}\n\n")
            
            for profile_name in self.profile_manager.list_profiles():
                profile_log_dir = LOG_DIR / profile_name
                if profile_log_dir.exists():
                    for log_file in profile_log_dir.glob("*.log"):
                        with open(log_file, 'r', encoding='utf-8') as f:
                            all_logs.append(f"=== {profile_name} ===\n{f.read()}\n\n")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(''.join(all_logs))
            
            messagebox.showinfo("Success", f"Logs exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            messagebox.showerror("Error", f"Failed to export logs: {str(e)}")
    
    # Settings and Utilities
    def _toggle_theme(self) -> None:
        """Toggle dark/light theme."""
        try:
            self.theme_manager.toggle()
            self._apply_theme()
            self.theme_label.configure(
                text=f"Current: {'Dark' if self.theme_manager.dark_mode else 'Light'} Mode"
            )
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon._update_icon()
        except Exception as e:
            logger.error(f"Error toggling theme: {e}")
    
    def _check_dns_leak(self) -> None:
        """Check for DNS leaks."""
        try:
            leak_detected, dns_ips = self.vpn_handler._check_dns_leak()
            if leak_detected:
                self.dns_status_label.configure(
                    text=f"DNS Leak Detected: {', '.join(dns_ips)}",
                    foreground="red"
                )
            else:
                self.dns_status_label.configure(
                    text="DNS Status: Secure",
                    foreground="green"
                )
        except Exception as e:
            logger.error(f"Error checking DNS leak: {e}")
            self.dns_status_label.configure(
                text=f"DNS Check Failed: {str(e)}",
                foreground="orange"
            )
    
    # Callbacks
    def _on_status_change(self, profile_name, status):
        """Handle connection status change."""
        try:
            logger.info(f"Status changed: {profile_name} -> {status}")
            self.root.after(0, lambda: self._refresh_connections_list())
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon._update_icon()
        except Exception as e:
            logger.error(f"Error handling status change: {e}")
    
    def _on_dns_leak(self, profile_name, dns_ips):
        """Handle DNS leak detection."""
        try:
            logger.warning(f"DNS leak detected for {profile_name}: {dns_ips}")
            self.root.after(0, lambda: self._show_dns_leak_warning(profile_name, dns_ips))
        except Exception as e:
            logger.error(f"Error handling DNS leak: {e}")
    
    def _show_dns_leak_warning(self, profile_name, dns_ips):
        """Show DNS leak warning in UI."""
        try:
            self.dns_status_label.configure(
                text=f"DNS Leak: {', '.join(dns_ips)}",
                foreground="red"
            )
            messagebox.showwarning(
                "DNS Leak Detected",
                f"DNS leak detected for '{profile_name}'!\n\n"
                f"DNS servers: {', '.join(dns_ips)}\n\n"
                f"This may indicate that your traffic is not fully protected."
            )
            self._refresh_connections_list()
        except Exception as e:
            logger.error(f"Error showing DNS leak warning: {e}")
    
    # Periodic Updates
    def _start_periodic_updates(self) -> None:
        """Start periodic UI updates."""
        try:
            self._update_connections_timer()
            self._update_dns_timer()
        except Exception as e:
            logger.error(f"Error starting periodic updates: {e}")
    
    def _update_connections_timer(self) -> None:
        """Update connections list periodically."""
        try:
            self._refresh_connections_list()
            self.root.after(5000, self._update_connections_timer)
        except Exception as e:
            logger.error(f"Error in connections timer: {e}")
    
    def _update_dns_timer(self) -> None:
        """Update DNS status periodically."""
        try:
            self._check_dns_leak()
            self.root.after(30000, self._update_dns_timer)
        except Exception as e:
            logger.error(f"Error in DNS timer: {e}")
    
    # Window Close Handler
    def _on_close(self) -> None:
        """Handle window close event."""
        try:
            if HAS_SYSTRAY:
                self.root.withdraw()
            else:
                self.vpn_handler.stop_all()
                self.root.quit()
                self.root.destroy()
        except Exception as e:
            logger.error(f"Error on close: {e}")
            self.root.quit()
            self.root.destroy()
    
    def _check_dependencies(self) -> None:
        """Check for required dependencies."""
        try:
            missing = []
            if subprocess.run(["which", "sudo"], capture_output=True).returncode != 0:
                missing.append("sudo")
            if subprocess.run(["which", "openvpn"], capture_output=True).returncode != 0:
                missing.append("openvpn")
            if subprocess.run(["which", "wg-quick"], capture_output=True).returncode != 0:
                missing.append("wireguard-tools (wg-quick)")
            if subprocess.run(["which", "dig"], capture_output=True).returncode != 0:
                logger.warning("dig not found. DNS leak detection will use fallback methods.")
            
            if missing:
                messagebox.showwarning(
                    "Missing Dependencies",
                    f"The following dependencies are missing:\n\n{', '.join(missing)}\n\n"
                    f"Please install them to use all features."
                )
        except Exception as e:
            logger.error(f"Error checking dependencies: {e}")
    
    def run(self) -> None:
        """Run the application."""
        try:
            self._check_dependencies()
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Application error: {e}")
            messagebox.showerror("Error", f"Application error: {str(e)}")


def main():
    """Main entry point for the application."""
    try:
        if os.geteuid() == 0:
            logger.warning("Running as root. Consider running as a regular user with sudo privileges.")
        
        app = VPNManagerApp()
        app.run()
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
