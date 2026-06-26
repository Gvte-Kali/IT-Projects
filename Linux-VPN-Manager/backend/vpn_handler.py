import subprocess
from pathlib import Path

class VPNHandler:
    def __init__(self, config_manager, log_manager):
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.active_processes = {}

    def start_vpn(self, config_path, connection_name):
        try:
            vpn_type = self._detect_vpn_type(config_path)
            if vpn_type == "openvpn":
                process = subprocess.Popen(
                    ["sudo", "openvpn", "--config", config_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )
            elif vpn_type == "wireguard":
                interface = Path(config_path).stem
                process = subprocess.Popen(
                    ["sudo", "wg-quick", "up", interface],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )
            else:
                raise ValueError(f"Unsupported VPN type for file: {config_path}")

            self.active_processes[connection_name] = process
            self.log_manager.start_logging(connection_name, process.stdout)
            return True, f"Starting {vpn_type} VPN: {connection_name}"
        except Exception as e:
            return False, f"Failed to start VPN: {str(e)}"

    def stop_vpn(self, connection_name):
        try:
            if connection_name in self.active_processes:
                process = self.active_processes[connection_name]
                config_path = self.config_manager.get_config_path(connection_name)
                vpn_type = self._detect_vpn_type(config_path)

                if vpn_type == "openvpn":
                    process.terminate()
                elif vpn_type == "wireguard":
                    interface = Path(config_path).stem
                    subprocess.run(["sudo", "wg-quick", "down", interface], check=True)

                del self.active_processes[connection_name]
                self.log_manager.stop_logging(connection_name)
                return True, f"Stopped VPN: {connection_name}"
            else:
                return False, f"No active VPN process for: {connection_name}"
        except Exception as e:
            return False, f"Failed to stop VPN: {str(e)}"

    def get_vpn_status(self, connection_name):
        try:
            config_path = self.config_manager.get_config_path(connection_name)
            vpn_type = self._detect_vpn_type(config_path)

            if vpn_type == "openvpn":
                interface = self._get_openvpn_interface(config_path)
            elif vpn_type == "wireguard":
                interface = Path(config_path).stem
            else:
                return "DOWN", "Unsupported VPN type"

            result = subprocess.run(
                ["ip", "link", "show", interface],
                capture_output=True, text=True
            )

            if "UP" in result.stdout:
                ip_result = subprocess.run(
                    ["ip", "addr", "show", interface],
                    capture_output=True, text=True
                )
                if "inet " in ip_result.stdout:
                    return "UP", interface
                else:
                    return "DOWN", "No IP assigned"
            else:
                return "DOWN", "Interface not UP"
        except Exception as e:
            return "DOWN", f"Error: {str(e)}"

    def _detect_vpn_type(self, config_path):
        if config_path.endswith(".ovpn"):
            return "openvpn"
        elif config_path.endswith(".conf"):
            with open(config_path, 'r') as f:
                content = f.read()
                if "[Interface]" in content:
                    return "wireguard"
        return "unknown"

    def _get_openvpn_interface(self, config_path):
        with open(config_path, 'r') as f:
            for line in f:
                if line.startswith("dev "):
                    return line.split()[1].strip()
        return "tun0"