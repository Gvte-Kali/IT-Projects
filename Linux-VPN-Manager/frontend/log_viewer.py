from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton

class LogViewer(QDialog):
    def __init__(self, log_manager, connection_name):
        super().__init__()
        self.log_manager = log_manager
        self.connection_name = connection_name
        self.setWindowTitle(f"Logs: {connection_name}")
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        refresh_button = QPushButton("Refresh Logs")
        refresh_button.clicked.connect(self.refresh_logs)
        layout.addWidget(refresh_button)

        self.setLayout(layout)
        self.refresh_logs()

    def refresh_logs(self):
        logs = self.log_manager.get_logs(self.connection_name)
        self.log_display.setPlainText("\n".join(logs))