import threading
import os
from datetime import datetime

class LogManager:
    def __init__(self):
        self.logs = {}
        self.log_threads = {}
        self.log_dir = os.path.expanduser("~/.local/share/vpn-manager/logs")
        os.makedirs(self.log_dir, exist_ok=True)

    def start_logging(self, connection_name, stdout):
        log_path = os.path.join(self.log_dir, f"{connection_name}.log")
        self.logs[connection_name] = []

        def log_worker():
            for line in stdout:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_line = f"[{timestamp}] {line.strip()}"
                self.logs[connection_name].append(log_line)
                with open(log_path, "a") as f:
                    f.write(log_line + "\n")

        thread = threading.Thread(target=log_worker, daemon=True)
        thread.start()
        self.log_threads[connection_name] = thread

    def stop_logging(self, connection_name):
        if connection_name in self.log_threads:
            del self.log_threads[connection_name]

    def get_logs(self, connection_name):
        return self.logs.get(connection_name, [])

    def clear_logs(self, connection_name):
        if connection_name in self.logs:
            self.logs[connection_name] = []