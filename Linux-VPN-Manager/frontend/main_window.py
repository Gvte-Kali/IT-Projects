"""
Main Window Module

Provides the main GUI window for VPN Manager application.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QInputDialog,
    QMenu,
    QTabWidget,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QSettings
from PyQt6.QtGui import QIcon, QAction, QFont
from typing import Optional
import logging


class SignalEmitter(QObject):
    """Emitter for custom signals."""

    connection_updated = pyqtSignal()


class MainWindow(QMainWindow):
    """Main application window for VPN Manager."""

    def __init__(self, vpn_handler, config_manager, log_manager, stats_manager=None, 
                 theme_manager=None, notification_manager=None, history_manager=None,
                 stats_chart=None, dependency_checker=None):
        """
        Initialize the main window.

        Args:
            vpn_handler: VPNHandler instance
            config_manager: ConfigManager instance
            log_manager: LogManager instance
            stats_manager: StatsManager instance (optional)
            theme_manager: ThemeManager instance (optional)
            notification_manager: NotificationManager instance (optional)
            history_manager: HistoryManager instance (optional)
            stats_chart: StatsChart instance (optional)
            dependency_checker: DependencyChecker instance (optional)
        """
        super().__init__()
        self.vpn_handler = vpn_handler
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.stats_manager = stats_manager
        self.theme_manager = theme_manager
        self.notification_manager = notification_manager
        self.history_manager = history_manager
        self.stats_chart = stats_chart
        self.dependency_checker = dependency_checker
        self.logger = logging.getLogger("MainWindow")

        # Set up window properties
        self.setWindowTitle("VPN Manager")
        self.setGeometry(100, 100, 700, 550)
        self.setMinimumSize(600, 500)

        # Restore saved window geometry and state
        self.settings = QSettings("LinuxVPNManager", "VPNManager")
        saved_geometry = self.settings.value("window_geometry", None)
        saved_state = self.settings.value("window_state", None)
        if saved_geometry:
            self.restoreGeometry(saved_geometry)
        if saved_state:
            self.restoreState(saved_state)

        # Create signal emitter for cross-widget communication
        self.signal_emitter = SignalEmitter()

        # Register callbacks with VPN handler
        if self.vpn_handler is not None:
            self.vpn_handler.register_status_callback(self._on_connection_status_change)
            self.vpn_handler.register_dns_leak_callback(self._on_dns_leak_detected)

        # Initialize UI
        self._init_ui()

        # Connect signals
        self._connect_signals()

        # Load connections
        self.refresh_connections()

        # Set up stats update timer
        if self.stats_manager is not None:
            self.stats_timer = QTimer()
            self.stats_timer.timeout.connect(self._update_stats_display)
            self.stats_timer.start(1000)  # Update stats every second

    def _init_ui(self):
        """Initialize the user interface."""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create connections tab
        self.connections_tab = QWidget()
        self._init_connections_tab()
        self.tab_widget.addTab(self.connections_tab, "Connections")

        # Create statistics tab if stats_manager is available
        if self.stats_manager is not None:
            self.stats_tab = QWidget()
            self._init_stats_tab()
            self.tab_widget.addTab(self.stats_tab, "Statistics")
        
        # Create history tab if history_manager is available
        if self.history_manager is not None:
            self._init_history_tab()

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        # Create menu bar
        self._create_menu_bar()

    def _init_connections_tab(self):
        """Initialize the connections tab."""
        # Store layout reference for search bar insertion
        self.connections_tab_layout = QVBoxLayout(self.connections_tab)
        self.connections_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.connections_tab_layout.setSpacing(10)

        # Initialize search bar
        self._init_search_bar()

        # Create connection list
        self.connection_list = QListWidget()
        self.connection_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.connection_list.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self.connection_list.itemDoubleClicked.connect(self.on_connection_double_clicked)
        self.connection_list.itemSelectionChanged.connect(self._update_button_states)
        self.connections_tab_layout.addWidget(self.connection_list)

        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Add Connection button
        self.add_button = QPushButton("Add Connection")
        self.add_button.clicked.connect(self.add_connection)
        self.add_button.setToolTip("Add a new VPN connection")
        button_layout.addWidget(self.add_button)

        # Remove Connection button
        self.remove_button = QPushButton("Remove Connection")
        self.remove_button.clicked.connect(self.remove_connection)
        self.remove_button.setToolTip("Remove the selected VPN connection")
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)

        # View Logs button
        self.view_logs_button = QPushButton("View Logs")
        self.view_logs_button.clicked.connect(self.view_logs)
        self.view_logs_button.setToolTip("View logs for the selected connection")
        self.view_logs_button.setEnabled(False)
        button_layout.addWidget(self.view_logs_button)

        # Refresh button
        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.clicked.connect(self.refresh_status)
        self.refresh_button.setToolTip("Refresh the status of all connections")
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

    def _init_stats_tab(self):
        """Initialize the statistics tab."""
        if self.stats_manager is None:
            return

        layout = QVBoxLayout(self.stats_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Global stats group
        global_group = QGroupBox("Global Statistics")
        global_layout = QFormLayout()

        self.global_active_label = QLabel("0")
        self.global_total_label = QLabel("0")
        self.global_sent_label = QLabel("0 B")
        self.global_recv_label = QLabel("0 B")
        self.global_errors_label = QLabel("0")

        global_layout.addRow("Active Connections:", self.global_active_label)
        global_layout.addRow("Total Connections:", self.global_total_label)
        global_layout.addRow("Total Sent:", self.global_sent_label)
        global_layout.addRow("Total Received:", self.global_recv_label)
        global_layout.addRow("Total Errors:", self.global_errors_label)

        global_group.setLayout(global_layout)
        layout.addWidget(global_group)

        # DNS Leak Status
        dns_group = QGroupBox("DNS Leak Detection")
        dns_layout = QVBoxLayout()
        
        self.dns_leak_label = QLabel("No DNS leaks detected")
        self.dns_leak_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.dns_leak_label.setWordWrap(True)
        dns_layout.addWidget(self.dns_leak_label)
        
        # DNS check button
        if self.vpn_handler is not None:
            check_dns_button = QPushButton("Check DNS Leak Status")
            check_dns_button.clicked.connect(self._check_all_dns_leaks)
            dns_layout.addWidget(check_dns_button)
        
        dns_group.setLayout(dns_layout)
        layout.addWidget(dns_group)

        # Per-connection stats group
        connection_group = QGroupBox("Connection Statistics")
        connection_layout = QVBoxLayout()

        self.connection_stats_list = QListWidget()
        self.connection_stats_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.connection_stats_list.customContextMenuRequested.connect(
            self._show_stats_context_menu
        )
        connection_layout.addWidget(self.connection_stats_list)

        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)

        # Update stats display
        self._update_stats_display()

    def _create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        add_action = QAction("Add Connection", self)
        add_action.triggered.connect(self.add_connection)
        file_menu.addAction(add_action)

        remove_action = QAction("Remove Connection", self)
        remove_action.triggered.connect(self.remove_connection)
        file_menu.addAction(remove_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        refresh_action = QAction("Refresh Status", self)
        refresh_action.triggered.connect(self.refresh_status)
        view_menu.addAction(refresh_action)

        view_logs_action = QAction("View Logs", self)
        view_logs_action.triggered.connect(self.view_logs)
        view_menu.addAction(view_logs_action)

        # Theme menu (if theme_manager is available)
        if self.theme_manager is not None:
            theme_menu = menubar.addMenu("Theme")

            light_action = QAction("Light", self)
            light_action.triggered.connect(self._set_light_theme)
            theme_menu.addAction(light_action)

            dark_action = QAction("Dark", self)
            dark_action.triggered.connect(self._set_dark_theme)
            theme_menu.addAction(dark_action)

            system_action = QAction("System", self)
            system_action.triggered.connect(self._set_system_theme)
            theme_menu.addAction(system_action)

            theme_menu.addSeparator()

            toggle_action = QAction("Toggle Theme", self)
            toggle_action.triggered.connect(self._toggle_theme)
            theme_menu.addAction(toggle_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # Test notification action (if notification_manager is available)
        if self.notification_manager is not None:
            help_menu.addSeparator()
            test_notification_action = QAction("Test Notification", self)
            test_notification_action.triggered.connect(self._test_notification)
            help_menu.addAction(test_notification_action)

    def _connect_signals(self):
        """Connect signals between components."""
        # Connect signal emitter to refresh
        self.signal_emitter.connection_updated.connect(self.refresh_connections)

    def _show_context_menu(self, pos):
        """Show context menu for connection list."""
        item = self.connection_list.itemAt(pos)
        if not item:
            return

        connection_name = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        # Connect/Disconnect action
        status, _ = self.vpn_handler.get_vpn_status(connection_name)
        if status == "UP":
            disconnect_action = QAction("Disconnect", self)
            disconnect_action.triggered.connect(
                lambda: self._toggle_connection(connection_name)
            )
            menu.addAction(disconnect_action)
        else:
            connect_action = QAction("Connect", self)
            connect_action.triggered.connect(
                lambda: self._toggle_connection(connection_name)
            )
            menu.addAction(connect_action)

        menu.addSeparator()

        # View Logs action
        view_logs_action = QAction("View Logs", self)
        view_logs_action.triggered.connect(self.view_logs)
        menu.addAction(view_logs_action)

        menu.addSeparator()

        # Edit action
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(self.edit_connection)
        menu.addAction(edit_action)

        # Remove action
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(self.remove_connection)
        menu.addAction(remove_action)

        menu.exec(self.connection_list.viewport().mapToGlobal(pos))

    def _show_stats_context_menu(self, pos):
        """Show context menu for stats list."""
        item = self.connection_stats_list.itemAt(pos)
        if not item:
            return

        connection_name = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        # View detailed stats action
        details_action = QAction("View Details", self)
        details_action.triggered.connect(
            lambda: self._show_connection_details(connection_name)
        )
        menu.addAction(details_action)

        # Reset stats action
        reset_action = QAction("Reset Stats", self)
        reset_action.triggered.connect(
            lambda: self._reset_connection_stats(connection_name)
        )
        menu.addAction(reset_action)

        menu.exec(self.connection_stats_list.viewport().mapToGlobal(pos))

    def _update_button_states(self):
        """Update button enabled states based on selection."""
        selected_items = self.connection_list.selectedItems()
        has_selection = len(selected_items) > 0
        self.remove_button.setEnabled(has_selection)
        self.view_logs_button.setEnabled(has_selection)

    def _toggle_connection(self, connection_name: str):
        """Toggle a VPN connection (connect/disconnect)."""
        status, _ = self.vpn_handler.get_vpn_status(connection_name)

        if status == "UP":
            success, message = self.vpn_handler.stop_vpn(connection_name)
            if success and self.notification_manager is not None:
                self.notification_manager.show_connection_disconnected(connection_name)
        else:
            config_path = self.config_manager.get_config_path(connection_name)
            success, message = self.vpn_handler.start_vpn(config_path, connection_name)
            if success and self.notification_manager is not None:
                self.notification_manager.show_connection_connected(connection_name)

        if success:
            self.refresh_connections()
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #28a745;")
        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText(f"Error: {message}")
            self.status_label.setStyleSheet("color: #dc3545;")
            if self.notification_manager is not None:
                self.notification_manager.show_connection_error(connection_name, message)

    def _get_icon_path(self, filename: str) -> Optional[str]:
        """Get the path to an icon file."""
        from pathlib import Path

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

        # Try using DE manager if available
        if self.theme_manager is not None and hasattr(self.theme_manager, 'de_manager'):
            de_icon = self.theme_manager.de_manager.get_icon_path(filename.replace(".png", ""))
            if de_icon:
                return de_icon

        return None

    def _get_status_icon(self, status: str) -> QIcon:
        """Get the appropriate icon for a connection status."""
        if self.theme_manager is not None:
            # Use theme-aware icons
            if status == "UP":
                icon_path = self._get_icon_path("green.png")
            elif status == "CONNECTING":
                icon_path = self._get_icon_path("yellow.png")
            else:
                icon_path = self._get_icon_path("red.png")
        else:
            # Fallback to default icons
            script_dir = Path(__file__).parent.parent
            if status == "UP":
                icon_path = script_dir / "assets" / "green.png"
            elif status == "CONNECTING":
                icon_path = script_dir / "assets" / "yellow.png"
            else:
                icon_path = script_dir / "assets" / "red.png"

        if icon_path and Path(icon_path).exists():
            return QIcon(str(icon_path))
        return QIcon()

    def refresh_connections(self):
        """Refresh the connection list with current status."""
        try:
            self.connection_list.clear()

            for name in self.config_manager.list_connections():
                status, _ = self.vpn_handler.get_vpn_status(name)
                icon = self._get_status_icon(status)

                item = QListWidgetItem(f"{name} ({status})")
                item.setIcon(icon)
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.connection_list.addItem(item)

            # Update status label
            count = len(self.config_manager.list_connections())
            self.status_label.setText(f"Ready - {count} connection(s)")
            self.status_label.setStyleSheet("color: #666;")

        except Exception as e:
            self.logger.error(f"Error refreshing connections: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: #dc3545;")

    def refresh_status(self):
        """Refresh the status of all connections."""
        self.refresh_connections()
        self.status_label.setText("Status refreshed")
        self.status_label.setStyleSheet("color: #28a745;")

    def _update_stats_display(self):
        """Update the statistics display."""
        if self.stats_manager is None:
            return

        try:
            # Update global stats
            global_stats = self.stats_manager.get_global_stats()
            self.global_active_label.setText(str(global_stats.active_connections))
            self.global_total_label.setText(str(global_stats.total_connections))
            self.global_sent_label.setText(
                self._format_bytes(global_stats.total_bytes_sent)
            )
            self.global_recv_label.setText(
                self._format_bytes(global_stats.total_bytes_recv)
            )
            self.global_errors_label.setText(str(global_stats.total_errors))

            # Update per-connection stats
            self.connection_stats_list.clear()
            all_stats = self.stats_manager.get_all_stats()

            for name, stats in all_stats.items():
                # Get formatted stats
                formatted = self.stats_manager.get_formatted_stats(name)

                item_text = (
                    f"{name}: "
                    f"↑{formatted.get('send_speed', '0 B/s')} "
                    f"↓{formatted.get('recv_speed', '0 B/s')} | "
                    f"Total: ↑{formatted.get('total_sent', '0 B')} ↓{formatted.get('total_recv', '0 B')}"
                )

                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.connection_stats_list.addItem(item)

        except Exception as e:
            self.logger.error(f"Error updating stats display: {str(e)}")

    @staticmethod
    def _format_bytes(bytes_total: int) -> str:
        """Format bytes to human-readable string."""
        if bytes_total < 1024:
            return f"{bytes_total} B"
        elif bytes_total < 1024 * 1024:
            return f"{bytes_total / 1024:.1f} KB"
        elif bytes_total < 1024 * 1024 * 1024:
            return f"{bytes_total / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_total / (1024 * 1024 * 1024):.1f} GB"

    def _show_connection_details(self, connection_name: str):
        """Show detailed statistics for a connection."""
        if self.stats_manager is None:
            return

        stats = self.stats_manager.get_stats(connection_name)
        if stats is None:
            QMessageBox.information(self, "Info", f"No statistics available for {connection_name}")
            return

        formatted = self.stats_manager.get_formatted_stats(connection_name)

        details = f"""
        <h2>{connection_name} Statistics</h2>
        <table>
            <tr><td><b>Session Time:</b></td><td>{formatted.get('session_time', '0s')}</td></tr>
            <tr><td><b>Total Time:</b></td><td>{formatted.get('total_time', '0s')}</td></tr>
            <tr><td><b>Send Speed:</b></td><td>{formatted.get('send_speed', '0 B/s')}</td></tr>
            <tr><td><b>Receive Speed:</b></td><td>{formatted.get('recv_speed', '0 B/s')}</td></tr>
            <tr><td><b>Total Sent:</b></td><td>{formatted.get('total_sent', '0 B')}</td></tr>
            <tr><td><b>Total Received:</b></td><td>{formatted.get('total_recv', '0 B')}</td></tr>
            <tr><td><b>Peak Send:</b></td><td>{formatted.get('peak_send', '0 B/s')}</td></tr>
            <tr><td><b>Peak Receive:</b></td><td>{formatted.get('peak_recv', '0 B/s')}</td></tr>
            <tr><td><b>Packets Sent:</b></td><td>{formatted.get('packets_sent', '0')}</td></tr>
            <tr><td><b>Packets Received:</b></td><td>{formatted.get('packets_recv', '0')}</td></tr>
            <tr><td><b>Errors:</b></td><td>{formatted.get('errors', '0')}</td></tr>
            <tr><td><b>Drops:</b></td><td>{formatted.get('drops', '0')}</td></tr>
        </table>
        """

        QMessageBox.about(self, f"{connection_name} Details", details)

    def _reset_connection_stats(self, connection_name: str):
        """Reset statistics for a connection."""
        if self.stats_manager is None:
            return

        reply = QMessageBox.question(
            self,
            "Reset Statistics",
            f"Are you sure you want to reset statistics for {connection_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.stats_manager.reset_stats(connection_name)
            self._update_stats_display()

    # Theme management methods
    def _set_light_theme(self):
        """Set the theme to light."""
        if self.theme_manager is not None:
            self.theme_manager.set_user_preference(self.theme_manager.ThemeType.LIGHT)
            self.theme_manager.apply_theme(self.app)

    def _set_dark_theme(self):
        """Set the theme to dark."""
        if self.theme_manager is not None:
            self.theme_manager.set_user_preference(self.theme_manager.ThemeType.DARK)
            self.theme_manager.apply_theme(self.app)

    def _set_system_theme(self):
        """Set the theme to follow system."""
        if self.theme_manager is not None:
            self.theme_manager.set_user_preference(self.theme_manager.ThemeType.SYSTEM)
            self.theme_manager.apply_theme(self.app)

    def _toggle_theme(self):
        """Toggle between light and dark theme."""
        if self.theme_manager is not None:
            new_theme = self.theme_manager.toggle_theme()
            self.theme_manager.apply_theme(self.app)

    def add_connection(self):
        """Add a new VPN connection."""
        try:
            name, ok = QInputDialog.getText(
                self,
                "Add Connection",
                "Connection Name:",
                QInputDialog.InputMode.Normal,
                "",
            )
            if not ok or not name:
                return

            config_path, ok = QInputDialog.getText(
                self,
                "Add Connection",
                "Config File Path:",
                QInputDialog.InputMode.Normal,
                "",
            )
            if not ok or not config_path:
                return

            success, message = self.config_manager.add_connection(name, config_path)
            if success:
                self.refresh_connections()
                self.status_label.setText(message)
                self.status_label.setStyleSheet("color: #28a745;")
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.critical(self, "Error", message)
                self.status_label.setText(f"Error: {message}")
                self.status_label.setStyleSheet("color: #dc3545;")

        except Exception as e:
            self.logger.error(f"Error adding connection: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add connection: {str(e)}")

    def edit_connection(self):
        """Edit an existing VPN connection."""
        try:
            selected_items = self.connection_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Info", "Please select a connection to edit")
                return

            old_name = selected_items[0].data(Qt.ItemDataRole.UserRole)

            new_name, ok = QInputDialog.getText(
                self,
                "Edit Connection",
                "New Connection Name:",
                QInputDialog.InputMode.Normal,
                old_name,
            )
            if not ok:
                return

            config_path = self.config_manager.get_config_path(old_name)
            new_path, ok = QInputDialog.getText(
                self,
                "Edit Connection",
                "New Config File Path:",
                QInputDialog.InputMode.Normal,
                config_path or "",
            )
            if not ok:
                return

            success, message = self.config_manager.update_connection(
                old_name, new_name if new_name else None, new_path if new_path else None
            )
            if success:
                self.refresh_connections()
                self.status_label.setText(message)
                self.status_label.setStyleSheet("color: #28a745;")
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.critical(self, "Error", message)
                self.status_label.setText(f"Error: {message}")
                self.status_label.setStyleSheet("color: #dc3545;")

        except Exception as e:
            self.logger.error(f"Error editing connection: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to edit connection: {str(e)}")

    def remove_connection(self):
        """Remove a VPN connection."""
        try:
            selected_items = self.connection_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Info", "Please select a connection to remove")
                return

            name = selected_items[0].data(Qt.ItemDataRole.UserRole)

            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                f"Are you sure you want to remove the connection '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Stop the connection if it's running
                status, _ = self.vpn_handler.get_vpn_status(name)
                if status == "UP":
                    self.vpn_handler.stop_vpn(name)

                success, message = self.config_manager.remove_connection(name)
                if success:
                    self.refresh_connections()
                    self.status_label.setText(message)
                    self.status_label.setStyleSheet("color: #28a745;")
                    QMessageBox.information(self, "Success", message)
                else:
                    QMessageBox.critical(self, "Error", message)
                    self.status_label.setText(f"Error: {message}")
                    self.status_label.setStyleSheet("color: #dc3545;")

        except Exception as e:
            self.logger.error(f"Error removing connection: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove connection: {str(e)}")

    def view_logs(self):
        """View logs for the selected connection."""
        try:
            selected_items = self.connection_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Info", "Please select a connection to view logs")
                return

            name = selected_items[0].data(Qt.ItemDataRole.UserRole)

            # Import here to avoid circular imports
            from .log_viewer import LogViewer

            log_viewer = LogViewer(self.log_manager, name)
            log_viewer.exec()

        except Exception as e:
            self.logger.error(f"Error viewing logs: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to view logs: {str(e)}")

    def on_connection_double_clicked(self, item):
        """Handle double-click on a connection item."""
        connection_name = item.data(Qt.ItemDataRole.UserRole)
        self._toggle_connection(connection_name)

    def show_about(self):
        """Show the about dialog."""
        de_name = "Unknown"
        if self.theme_manager is not None and hasattr(self.theme_manager, 'de_manager'):
            de_name = self.theme_manager.de_manager.get_name()

        about_text = f"""
        <h2>VPN Manager</h2>
        <p>A cross-distribution, cross-desktop environment GUI application for managing
        VPN connections (OpenVPN, WireGuard) on Linux.</p>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Desktop Environment:</b> {de_name}</p>
        <p><b>License:</b> MIT</p>
        <p><b>Author:</b> LinuxVPNManager Team</p>
        """
        QMessageBox.about(self, "About VPN Manager", about_text)

    def _test_notification(self):
        """Test the notification system."""
        if self.notification_manager is not None:
            self.notification_manager.send_notification(
                title="VPN Manager Test",
                message="This is a test notification to verify that notifications are working correctly.",
                icon="dialog-info",
                urgency=self.notification_manager.URGENCY_NORMAL,
                timeout=5000,
            )

    # =========================================================================
    # Callback Methods for VPN Handler
    # =========================================================================

    def _on_connection_status_change(self, connection_name: str, status: str) -> None:
        """
        Callback for connection status changes.
        
        Args:
            connection_name: Name of the connection
            status: New status (connecting, connected, failed, disconnected, timeout)
        """
        try:
            self.logger.info(f"Connection status changed: {connection_name} -> {status}")
            
            # Update UI on the main thread
            QTimer.singleShot(0, lambda: self._update_connection_status_ui(connection_name, status))
        except Exception as e:
            self.logger.error(f"Error in status change callback: {str(e)}")

    def _update_connection_status_ui(self, connection_name: str, status: str) -> None:
        """
        Update UI based on connection status change.
        
        Args:
            connection_name: Name of the connection
            status: New status
        """
        try:
            # Find the connection item in the list
            for i in range(self.connections_list.count()):
                item = self.connections_list.item(i)
                if item is not None and item.data(Qt.UserRole) == connection_name:
                    # Update icon based on status
                    icon_name = self._get_status_icon(status)
                    icon_path = self._get_icon_path(icon_name)
                    if icon_path:
                        item.setIcon(QIcon(str(icon_path)))
                    
                    # Update text
                    item.setText(f"{connection_name} ({status})")
                    
                    # Update button states
                    self._update_connection_buttons()
                    break
            
            # Update status label
            self.status_label.setText(f"Status: {connection_name} - {status}")
            
            # Refresh stats display
            if self.stats_manager is not None:
                self._update_stats_display()
            
            # Refresh history display if visible
            if hasattr(self, 'history_tab') and self.tab_widget.currentWidget() == self.history_tab:
                self._update_history_display()
                
        except Exception as e:
            self.logger.error(f"Error updating connection status UI: {str(e)}")

    def _get_status_icon(self, status: str) -> str:
        """
        Get icon name based on connection status.
        
        Args:
            status: Connection status
            
        Returns:
            Icon filename
        """
        status_icons = {
            "connecting": "yellow.png",
            "connected": "green.png",
            "disconnected": "red.png",
            "failed": "red.png",
            "timeout": "red.png",
        }
        return status_icons.get(status, "red.png")

    def _on_dns_leak_detected(self, connection_name: str, dns_ips: List[str]) -> None:
        """
        Callback for DNS leak detection.
        
        Args:
            connection_name: Name of the connection with DNS leak
            dns_ips: List of DNS server IPs that caused the leak
        """
        try:
            self.logger.warning(f"DNS leak detected for {connection_name}: {dns_ips}")
            
            # Update UI on the main thread
            QTimer.singleShot(0, lambda: self._update_dns_leak_ui(connection_name, dns_ips))
        except Exception as e:
            self.logger.error(f"Error in DNS leak callback: {str(e)}")

    def _update_dns_leak_ui(self, connection_name: str, dns_ips: List[str]) -> None:
        """
        Update UI to show DNS leak warning.
        
        Args:
            connection_name: Name of the connection
            dns_ips: List of DNS server IPs
        """
        try:
            # Update status label with DNS leak warning
            current_text = self.status_label.text()
            if "DNS LEAK" not in current_text:
                self.status_label.setText(
                    f"{current_text} - ⚠️ DNS LEAK: {', '.join(dns_ips)}"
                )
            
            # Update connection item in list
            for i in range(self.connections_list.count()):
                item = self.connections_list.item(i)
                if item is not None and item.data(Qt.UserRole) == connection_name:
                    # Add DNS leak indicator to text
                    current_text = item.text()
                    if "DNS LEAK" not in current_text:
                        item.setText(f"{current_text} - ⚠️ DNS LEAK")
                    break
            
            # Update stats display to show DNS leak
            if hasattr(self, 'dns_leak_label'):
                self.dns_leak_label.setText(f"⚠️ DNS Leak Detected: {', '.join(dns_ips)}")
                self.dns_leak_label.setStyleSheet("color: #ff5555; font-weight: bold;")
            
            # Refresh stats display
            if self.stats_manager is not None:
                self._update_stats_display()
                
        except Exception as e:
            self.logger.error(f"Error updating DNS leak UI: {str(e)}")

    # =========================================================================
    # Search Functionality
    # =========================================================================

    def _init_search_bar(self):
        """Initialize the search bar for filtering connections."""
        try:
            # Create search layout
            search_layout = QHBoxLayout()
            
            # Search label
            search_label = QLabel("Search:")
            search_layout.addWidget(search_label)
            
            # Search input
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("Filter connections...")
            self.search_input.textChanged.connect(self._filter_connections)
            search_layout.addWidget(self.search_input)
            
            # Clear button
            clear_button = QPushButton("Clear")
            clear_button.clicked.connect(self._clear_search)
            search_layout.addWidget(clear_button)
            
            # Add search layout to connections tab
            if hasattr(self, 'connections_tab_layout'):
                self.connections_tab_layout.insertLayout(0, search_layout)
                
        except Exception as e:
            self.logger.error(f"Error initializing search bar: {str(e)}")

    def _filter_connections(self, text: str) -> None:
        """
        Filter connections based on search text.
        
        Args:
            text: Search text
        """
        try:
            search_text = text.lower()
            
            for i in range(self.connections_list.count()):
                item = self.connections_list.item(i)
                if item is None:
                    continue
                
                connection_name = item.data(Qt.UserRole)
                if connection_name is None:
                    continue
                
                # Show/hide items based on search
                if search_text in connection_name.lower():
                    item.setHidden(False)
                else:
                    item.setHidden(True)
                    
        except Exception as e:
            self.logger.error(f"Error filtering connections: {str(e)}")

    def _clear_search(self) -> None:
        """Clear the search filter."""
        try:
            self.search_input.clear()
            
            # Show all items
            for i in range(self.connections_list.count()):
                item = self.connections_list.item(i)
                if item is not None:
                    item.setHidden(False)
                    
        except Exception as e:
            self.logger.error(f"Error clearing search: {str(e)}")

    # =========================================================================
    # History Display Methods
    # =========================================================================

    def _init_history_tab(self):
        """Initialize the history tab."""
        try:
            if self.history_manager is None:
                return
            
            # Create history tab
            self.history_tab = QWidget()
            self.tab_widget.addTab(self.history_tab, "History")
            
            # Create layout
            history_layout = QVBoxLayout(self.history_tab)
            history_layout.setContentsMargins(10, 10, 10, 10)
            history_layout.setSpacing(10)
            
            # Create history display
            self.history_text = QTextEdit()
            self.history_text.setReadOnly(True)
            history_layout.addWidget(self.history_text)
            
            # Update display
            self._update_history_display()
            
        except Exception as e:
            self.logger.error(f"Error initializing history tab: {str(e)}")

    def _update_history_display(self) -> None:
        """Update the history display."""
        try:
            if not hasattr(self, 'history_text') or self.history_manager is None:
                return
            
            # Get all statistics
            stats = self.history_manager.get_all_statistics()
            global_stats = self.history_manager.get_global_statistics()
            
            # Build display text
            text = "<h2>Connection History</h2>\n\n"
            
            # Global statistics
            text += "<h3>Global Statistics</h3>\n"
            text += f"<b>Total Connections:</b> {global_stats['total_connections']}\n"
            text += f"<b>Total Sessions:</b> {global_stats['total_sessions']}\n"
            text += f"<b>Successful Sessions:</b> {global_stats['successful_sessions']}\n"
            text += f"<b>Failed Sessions:</b> {global_stats['failed_sessions']}\n"
            text += f"<b>Overall Success Rate:</b> {global_stats['overall_success_rate']:.1f}%\n"
            text += f"<b>Total Duration:</b> {self._format_duration(global_stats['total_duration'])}\n"
            text += f"<b>Total Data Sent:</b> {self._format_bytes(global_stats['total_bytes_sent'])}\n"
            text += f"<b>Total Data Received:</b> {self._format_bytes(global_stats['total_bytes_received'])}\n\n"
            
            # Per-connection statistics
            text += "<h3>Per-Connection Statistics</h3>\n"
            for conn_name, conn_stats in stats.items():
                text += f"<h4>{conn_name}</h4>\n"
                text += f"  <b>Sessions:</b> {conn_stats['total_sessions']}\n"
                text += f"  <b>Success Rate:</b> {conn_stats['success_rate']:.1f}%\n"
                text += f"  <b>Total Duration:</b> {self._format_duration(conn_stats['total_duration'])}\n"
                text += f"  <b>Avg Duration:</b> {self._format_duration(conn_stats['avg_duration'])}\n"
                text += f"  <b>Data Sent:</b> {self._format_bytes(conn_stats['total_bytes_sent'])}\n"
                text += f"  <b>Data Received:</b> {self._format_bytes(conn_stats['total_bytes_received'])}\n"
                text += f"  <b>Last Connection:</b> {conn_stats['last_connection'] or 'Never'}\n\n"
            
            # DNS Leak Status
            text += "<h3>DNS Leak Status</h3>\n"
            for conn_name in self.vpn_handler.active_connections.keys():
                dns_status = self.vpn_handler.get_dns_status(conn_name)
                if dns_status['leak_detected']:
                    text += f"<b style='color: red;'>{conn_name}:</b> DNS Leak Detected - {', '.join(dns_status['dns_ips'])}\n"
                else:
                    text += f"<b style='color: green;'>{conn_name}:</b> No DNS Leak\n"
            
            self.history_text.setHtml(text)
            
        except Exception as e:
            self.logger.error(f"Error updating history display: {str(e)}")

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in seconds to human-readable format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted string
        """
        try:
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                minutes = seconds / 60
                return f"{minutes:.1f}m"
            else:
                hours = seconds / 3600
                return f"{hours:.1f}h"
        except Exception:
            return "0s"

    def _format_bytes(self, bytes_val: int) -> str:
        """
        Format bytes to human-readable format.
        
        Args:
            bytes_val: Number of bytes
            
        Returns:
            Formatted string
        """
        try:
            if bytes_val < 1024:
                return f"{bytes_val}B"
            elif bytes_val < 1024 * 1024:
                kb = bytes_val / 1024
                return f"{kb:.1f}KB"
            elif bytes_val < 1024 * 1024 * 1024:
                mb = bytes_val / (1024 * 1024)
                return f"{mb:.1f}MB"
            else:
                gb = bytes_val / (1024 * 1024 * 1024)
                return f"{gb:.1f}GB"
        except Exception:
            return "0B"

    def _check_all_dns_leaks(self) -> None:
        """Check DNS leak status for all active connections."""
        try:
            if self.vpn_handler is None:
                return
            
            active_connections = self.vpn_handler.get_all_connections_info()
            
            if not active_connections:
                self.dns_leak_label.setText("No active connections to check")
                self.dns_leak_label.setStyleSheet("color: #666;")
                return
            
            # Check DNS for each active connection
            leak_detected = False
            leak_info = []
            
            for conn_name in active_connections.keys():
                dns_status = self.vpn_handler.get_dns_status(conn_name)
                if dns_status['leak_detected']:
                    leak_detected = True
                    leak_info.append(f"{conn_name}: {', '.join(dns_status['dns_ips'])}")
            
            if leak_detected:
                self.dns_leak_label.setText("⚠️ DNS Leaks Detected:\n" + "\n".join(leak_info))
                self.dns_leak_label.setStyleSheet("color: #ff5555; font-weight: bold;")
            else:
                self.dns_leak_label.setText("✅ No DNS leaks detected")
                self.dns_leak_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                
        except Exception as e:
            self.logger.error(f"Error checking DNS leaks: {str(e)}")
            self.dns_leak_label.setText(f"Error checking DNS: {str(e)}")
            self.dns_leak_label.setStyleSheet("color: #ff5555;")

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Save window geometry and state
            self.settings = QSettings("LinuxVPNManager", "VPNManager")
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.setValue("window_state", self.saveState())
            self.settings.sync()

            # Stop all active VPN connections
            for connection_name in list(self.vpn_handler.active_processes.keys()):
                self.vpn_handler.stop_vpn(connection_name)

            # Stop stats timer
            if hasattr(self, 'stats_timer') and self.stats_timer.isActive():
                self.stats_timer.stop()

            self.logger.info("Window closed, all connections stopped")
            event.accept()
        except Exception as e:
            self.logger.error(f"Error during close: {str(e)}")
            event.accept()
