from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QListWidget, QPushButton,
    QHBoxLayout, QLabel, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

class MainWindow(QMainWindow):
    def __init__(self, vpn_handler, config_manager, log_manager):
        super().__init__()
        self.vpn_handler = vpn_handler
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.setWindowTitle("VPN Manager")
        self.setGeometry(100, 100, 500, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.connection_list = QListWidget()
        self.connection_list.itemDoubleClicked.connect(self.on_connection_double_clicked)
        layout.addWidget(self.connection_list)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Connection")
        self.add_button.clicked.connect(self.add_connection)
        button_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Connection")
        self.remove_button.clicked.connect(self.remove_connection)
        button_layout.addWidget(self.remove_button)

        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.clicked.connect(self.refresh_status)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        self.refresh_connections()

    def refresh_connections(self):
        self.connection_list.clear()
        for name in self.config_manager.list_connections():
            status, _ = self.vpn_handler.get_vpn_status(name)
            icon_path = "assets/green.png" if status == "UP" else "assets/red.png"
            icon = QIcon(icon_path)
            item = self.connection_list.addItem(f"{name} ({status})")
            item.setIcon(icon)
            item.setData(Qt.ItemDataRole.UserRole, name)

    def refresh_status(self):
        self.refresh_connections()
        self.status_label.setText("Status refreshed")

    def add_connection(self):
        name, ok = QInputDialog.getText(self, "Add Connection", "Connection Name:")
        if not ok or not name:
            return

        config_path, ok = QInputDialog.getText(self, "Add Connection", "Config File Path:")
        if not ok or not config_path:
            return

        success, message = self.config_manager.add_connection(name, config_path)
        if success:
            self.refresh_connections()
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

    def remove_connection(self):
        selected_items = self.connection_list.selectedItems()
        if not selected_items:
            return

        name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        success, message = self.config_manager.remove_connection(name)
        if success:
            self.refresh_connections()
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

    def on_connection_double_clicked(self, item):
        name = item.data(Qt.ItemDataRole.UserRole)
        status, _ = self.vpn_handler.get_vpn_status(name)

        if status == "UP":
            success, message = self.vpn_handler.stop_vpn(name)
        else:
            success, message = self.vpn_handler.start_vpn(
                self.config_manager.get_config_path(name), name
            )

        if success:
            self.refresh_connections()
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)