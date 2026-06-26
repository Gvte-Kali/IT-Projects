import json
import os

class ConfigManager:
    def __init__(self):
        self.config_file = os.path.expanduser("~/.config/vpn-manager/connections.json")
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        self.connections = self._load_connections()

    def _load_connections(self):
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_connections(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.connections, f, indent=2)

    def add_connection(self, name, config_path):
        if not os.path.exists(config_path):
            return False, f"Config file does not exist: {config_path}"
        self.connections[name] = {"path": config_path}
        self._save_connections()
        return True, f"Added connection: {name}"

    def remove_connection(self, name):
        if name in self.connections:
            del self.connections[name]
            self._save_connections()
            return True, f"Removed connection: {name}"
        return False, f"Connection not found: {name}"

    def get_config_path(self, name):
        return self.connections.get(name, {}).get("path", "")

    def list_connections(self):
        return list(self.connections.keys())