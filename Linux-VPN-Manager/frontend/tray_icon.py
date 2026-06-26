from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QMessageBox
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer

class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, vpn_handler, config_manager, log_manager, main_window):
        super().__init__(QIcon("assets/icon.png"))
        self.vpn_handler = vpn_handler
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.main_window = main_window

        self.menu = QMenu()

        self.show_action = QAction("Show VPN Manager")
        self.show_action.triggered.connect(self.show_main_window)
        self.menu.addAction(self.show_action)

        self.menu.addSeparator()

        self.connection_actions = {}
        self.refresh_connections()

        self.menu.addSeparator()

        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)

        self.setContextMenu(self.menu)
        self.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(5000)

    def show_main_window(self):
        self.main_window.show()

    def quit_app(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def refresh_connections(self):
        for action in list(self.connection_actions.values()):
            self.menu.removeAction(action)
        self.connection_actions.clear()

        for name in self.config_manager.list_connections():
            status, _ = self.vpn_handler.get_vpn_status(name)
            action = QAction(f"{name} ({status})")
            action.triggered.connect(lambda _, n=name: self.toggle_connection(n))
            self.connection_actions[name] = action
            self.menu.insertAction(self.menu.actions()[1], action)

    def refresh_status(self):
        self.refresh_connections()

    def toggle_connection(self, name):
        status, _ = self.vpn_handler.get_vpn_status(name)
        if status == "UP":
            success, message = self.vpn_handler.stop_vpn(name)
        else:
            success, message = self.vpn_handler.start_vpn(
                self.config_manager.get_config_path(name), name
            )

        if success:
            self.refresh_status()
            self.showMessage("VPN Manager", message)
        else:
            QMessageBox.critical(None, "Error", message)