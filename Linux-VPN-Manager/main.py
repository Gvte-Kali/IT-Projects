import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from frontend.main_window import MainWindow
from frontend.tray_icon import SystemTrayIcon
from backend.vpn_handler import VPNHandler
from backend.log_manager import LogManager
from backend.config_manager import ConfigManager

class VPNManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Initialize backend
        self.config_manager = ConfigManager()
        self.log_manager = LogManager()
        self.vpn_handler = VPNHandler(self.config_manager, self.log_manager)

        # Initialize frontend
        self.main_window = MainWindow(self.vpn_handler, self.config_manager, self.log_manager)
        self.tray_icon = SystemTrayIcon(
            self.vpn_handler, self.config_manager, self.log_manager, self.main_window
        )

        # Set app icon
        self.app.setWindowIcon(QIcon("assets/icon.png"))

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    if not os.path.exists("assets/green.png") or not os.path.exists("assets/red.png"):
        QMessageBox.critical(
            None, "Error", "Required icon files (green.png, red.png) are missing from the assets folder."
        )
        sys.exit(1)

    manager = VPNManager()
    manager.run()