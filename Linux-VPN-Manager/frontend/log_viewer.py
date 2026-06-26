"""
Log Viewer Module

Provides a dialog for viewing VPN connection logs.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor
from typing import Optional
import logging


class LogViewer(QDialog):
    """Dialog for viewing VPN connection logs."""

    def __init__(self, log_manager, connection_name):
        """
        Initialize the log viewer.

        Args:
            log_manager: LogManager instance
            connection_name: Name of the connection to view logs for
        """
        super().__init__()
        self.log_manager = log_manager
        self.connection_name = connection_name
        self.logger = logging.getLogger("LogViewer")

        # Set up window properties
        self.setWindowTitle(f"Logs: {connection_name}")
        self.setGeometry(100, 100, 700, 500)
        self.setMinimumSize(500, 400)

        # Initialize UI
        self._init_ui()

        # Set up auto-refresh timer
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.refresh_logs)
        self.auto_refresh_timer.start(2000)  # Refresh every 2 seconds

        # Load initial logs
        self.refresh_logs()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Connection label
        connection_label = QLabel(f"Connection: <b>{self.connection_name}</b>")
        layout.addWidget(connection_label)

        # Log file info
        log_path = self.log_manager.get_log_file_path(self.connection_name)
        if log_path:
            log_file_label = QLabel(f"Log file: <i>{log_path}</i>")
            layout.addWidget(log_file_label)

        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_display.setFont(QFont("Monospace", 10))
        layout.addWidget(self.log_display)

        # Control buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)

        # Auto-refresh combo box
        self.auto_refresh_combo = QComboBox()
        self.auto_refresh_combo.addItems(["Auto-refresh: 2s", "Auto-refresh: 5s", "Auto-refresh: 10s", "Auto-refresh: Off"])
        self.auto_refresh_combo.currentIndexChanged.connect(self._change_auto_refresh)
        control_layout.addWidget(self.auto_refresh_combo)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_logs)
        refresh_button.setToolTip("Refresh logs manually")
        control_layout.addWidget(refresh_button)

        # Clear button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_logs)
        clear_button.setToolTip("Clear all logs")
        control_layout.addWidget(clear_button)

        # Save button
        save_button = QPushButton("Save to File")
        save_button.clicked.connect(self.save_logs)
        save_button.setToolTip("Save logs to a file")
        control_layout.addWidget(save_button)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setToolTip("Close this window")
        control_layout.addWidget(close_button)

        layout.addLayout(control_layout)

        self.setLayout(layout)

    def _change_auto_refresh(self, index: int):
        """Change the auto-refresh interval."""
        intervals = [2000, 5000, 10000, 0]  # ms
        interval = intervals[index]

        if interval > 0:
            self.auto_refresh_timer.start(interval)
        else:
            self.auto_refresh_timer.stop()

    def refresh_logs(self):
        """Refresh the logs display."""
        try:
            # Get logs from memory
            logs = self.log_manager.get_logs(self.connection_name, max_lines=1000)

            if logs:
                log_text = "\n".join(logs)
            else:
                # Try to read from file if no logs in memory
                logs_from_file = self.log_manager.read_log_file(
                    self.connection_name, max_lines=1000
                )
                log_text = "\n".join(logs_from_file) if logs_from_file else "No logs available"

            self.log_display.setPlainText(log_text)

            # Scroll to bottom
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_display.setTextCursor(cursor)

        except Exception as e:
            self.logger.error(f"Error refreshing logs: {str(e)}")
            self.log_display.setPlainText(f"Error loading logs: {str(e)}")

    def clear_logs(self):
        """Clear the logs for this connection."""
        try:
            reply = QMessageBox.question(
                self,
                "Clear Logs",
                f"Are you sure you want to clear all logs for '{self.connection_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                success = self.log_manager.clear_logs(self.connection_name)
                if success:
                    self.log_display.clear()
                    self.log_display.setPlainText("Logs cleared")
                else:
                    QMessageBox.critical(self, "Error", "Failed to clear logs")

        except Exception as e:
            self.logger.error(f"Error clearing logs: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to clear logs: {str(e)}")

    def save_logs(self):
        """Save logs to a file."""
        try:
            # Get logs
            logs = self.log_manager.get_logs(self.connection_name)
            if not logs:
                logs = self.log_manager.read_log_file(self.connection_name)

            if not logs:
                QMessageBox.information(self, "Info", "No logs to save")
                return

            log_text = "\n".join(logs)

            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Logs",
                f"{self.connection_name}_logs.txt",
                "Text Files (*.txt);;All Files (*)",
            )

            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(log_text)
                QMessageBox.information(self, "Success", f"Logs saved to {file_path}")

        except Exception as e:
            self.logger.error(f"Error saving logs: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save logs: {str(e)}")

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Stop auto-refresh timer
            if self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.stop()
            event.accept()
        except Exception as e:
            self.logger.error(f"Error during close: {str(e)}")
            event.accept()
