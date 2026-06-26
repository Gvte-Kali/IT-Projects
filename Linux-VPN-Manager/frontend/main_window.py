"""
Main Window Module

Provides the main GUI window for VPN Manager application.
"""

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
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction
from typing import Optional
import logging


class SignalEmitter(QObject):
    """Emitter for custom signals."""

    connection_updated = pyqtSignal()


class MainWindow(QMainWindow):
    """Main application window for VPN Manager."""

    def __init__(self, vpn_handler, config_manager, log_manager):
        """
        Initialize the main window.

        Args:
            vpn_handler: VPNHandler instance
            config_manager: ConfigManager instance
            log_manager: LogManager instance
        """
        super().__init__()
        self.vpn_handler = vpn_handler
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.logger = logging.getLogger("MainWindow")

        # Set up window properties
        self.setWindowTitle("VPN Manager")
        self.setGeometry(100, 100, 600, 500)
        self.setMinimumSize(500, 400)

        # Create signal emitter for cross-widget communication
        self.signal_emitter = SignalEmitter()

        # Initialize UI
        self._init_ui()

        # Connect signals
        self._connect_signals()

        # Load connections
        self.refresh_connections()

    def _init_ui(self):
        """Initialize the user interface."""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Create connection list
        self.connection_list = QListWidget()
        self.connection_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.connection_list.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self.connection_list.itemDoubleClicked.connect(self.on_connection_double_clicked)
        self.connection_list.itemSelectionChanged.connect(self._update_button_states)
        layout.addWidget(self.connection_list)

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

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        # Create menu bar
        self._create_menu_bar()

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

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

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
        else:
            config_path = self.config_manager.get_config_path(connection_name)
            success, message = self.vpn_handler.start_vpn(config_path, connection_name)

        if success:
            self.refresh_connections()
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #28a745;")
        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText(f"Error: {message}")
            self.status_label.setStyleSheet("color: #dc3545;")

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

        return None

    def refresh_connections(self):
        """Refresh the connection list with current status."""
        try:
            self.connection_list.clear()

            for name in self.config_manager.list_connections():
                status, _ = self.vpn_handler.get_vpn_status(name)

                # Get icon based on status
                if status == "UP":
                    icon_path = self._get_icon_path("green.png")
                    icon = QIcon(icon_path) if icon_path else QIcon()
                elif status == "CONNECTING":
                    icon_path = self._get_icon_path("yellow.png")
                    icon = QIcon(icon_path) if icon_path else QIcon()
                else:
                    icon_path = self._get_icon_path("red.png")
                    icon = QIcon(icon_path) if icon_path else QIcon()

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
        about_text = """
        <h2>VPN Manager</h2>
        <p>A cross-distribution, cross-desktop environment GUI application for managing
        VPN connections (OpenVPN, WireGuard) on Linux.</p>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>License:</b> MIT</p>
        <p><b>Author:</b> LinuxVPNManager Team</p>
        """
        QMessageBox.about(self, "About VPN Manager", about_text)

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Stop all active VPN connections
            for connection_name in list(self.vpn_handler.active_processes.keys()):
                self.vpn_handler.stop_vpn(connection_name)

            self.logger.info("Window closed, all connections stopped")
            event.accept()
        except Exception as e:
            self.logger.error(f"Error during close: {str(e)}")
            event.accept()
