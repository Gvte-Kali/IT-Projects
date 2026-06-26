"""
VPN Handler Module

Handles VPN connection management for OpenVPN and WireGuard.
Provides start, stop, and status checking functionality.
"""

import subprocess
import os
import re
from pathlib import Path
from typing import Tuple, Dict, Optional
import logging


class VPNHandler:
    """Handles VPN connection operations."""

    def __init__(self, config_manager, log_manager, stats_manager=None):
        """
        Initialize VPN Handler.

        Args:
            config_manager: ConfigManager instance for managing configurations
            log_manager: LogManager instance for managing logs
            stats_manager: StatsManager instance for managing statistics (optional)
        """
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.stats_manager = stats_manager
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.logger = logging.getLogger("VPNHandler")

    def start_vpn(self, config_path: str, connection_name: str) -> Tuple[bool, str]:
        """
        Start a VPN connection.

        Args:
            config_path: Path to the VPN configuration file
            connection_name: Name of the connection

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate config path
            config_path = os.path.abspath(os.path.expanduser(config_path))
            if not os.path.exists(config_path):
                return False, f"Config file does not exist: {config_path}"

            if not os.path.isfile(config_path):
                return False, f"Config path is not a file: {config_path}"

            # Check file permissions (should be readable by user)
            if not os.access(config_path, os.R_OK):
                return False, f"Cannot read config file (permission denied): {config_path}"

            # Detect VPN type
            vpn_type = self._detect_vpn_type(config_path)
            if vpn_type == "unknown":
                return False, f"Unsupported VPN type for file: {config_path}"

            self.logger.info(f"Starting {vpn_type} VPN: {connection_name}")

            # Stop any existing connection with the same name
            if connection_name in self.active_processes:
                self.stop_vpn(connection_name)

            # Start the VPN process
            if vpn_type == "openvpn":
                process = self._start_openvpn(config_path)
            elif vpn_type == "wireguard":
                process = self._start_wireguard(config_path)
            else:
                return False, f"Unsupported VPN type: {vpn_type}"

            if process is None:
                return False, f"Failed to start {vpn_type} process"

            self.active_processes[connection_name] = process
            self.log_manager.start_logging(connection_name, process.stdout)

            # Start stats monitoring if stats_manager is available
            if self.stats_manager is not None:
                interface = self._get_interface_for_connection(config_path, vpn_type)
                self.stats_manager.start_monitoring(connection_name, interface)

            self.logger.info(f"Successfully started {vpn_type} VPN: {connection_name}")
            return True, f"Starting {vpn_type} VPN: {connection_name}"

        except Exception as e:
            self.logger.error(f"Failed to start VPN {connection_name}: {str(e)}")
            return False, f"Failed to start VPN: {str(e)}"

    def stop_vpn(self, connection_name: str) -> Tuple[bool, str]:
        """
        Stop a VPN connection.

        Args:
            connection_name: Name of the connection to stop

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if connection_name not in self.active_processes:
                # Try to stop via config if process not tracked
                config_path = self.config_manager.get_config_path(connection_name)
                if config_path:
                    vpn_type = self._detect_vpn_type(config_path)
                    if vpn_type == "wireguard":
                        interface = Path(config_path).stem
                        try:
                            subprocess.run(
                                ["sudo", "wg-quick", "down", interface],
                                check=True,
                                capture_output=True,
                            )
                            self.logger.info(
                                f"Stopped WireGuard interface {interface} for {connection_name}"
                            )
                            return True, f"Stopped VPN: {connection_name}"
                        except subprocess.CalledProcessError as e:
                            self.logger.warning(
                                f"Failed to stop WireGuard interface: {str(e)}"
                            )
                return False, f"No active VPN process for: {connection_name}"

            process = self.active_processes[connection_name]
            config_path = self.config_manager.get_config_path(connection_name)
            vpn_type = self._detect_vpn_type(config_path)

            self.logger.info(f"Stopping {vpn_type} VPN: {connection_name}")

            if vpn_type == "openvpn":
                self._stop_openvpn(process)
            elif vpn_type == "wireguard":
                self._stop_wireguard(config_path)

            # Clean up
            del self.active_processes[connection_name]
            self.log_manager.stop_logging(connection_name)

            # Stop stats monitoring if stats_manager is available
            if self.stats_manager is not None:
                self.stats_manager.stop_monitoring(connection_name)

            self.logger.info(f"Successfully stopped {vpn_type} VPN: {connection_name}")
            return True, f"Stopped VPN: {connection_name}"

        except Exception as e:
            self.logger.error(f"Failed to stop VPN {connection_name}: {str(e)}")
            return False, f"Failed to stop VPN: {str(e)}"

    def get_vpn_status(self, connection_name: str) -> Tuple[str, str]:
        """
        Get the status of a VPN connection.

        Args:
            connection_name: Name of the connection

        Returns:
            Tuple of (status: str, message: str)
            Status can be: "UP", "DOWN", "CONNECTING", "ERROR"
        """
        try:
            config_path = self.config_manager.get_config_path(connection_name)
            if not config_path:
                return "DOWN", "Connection not configured"

            vpn_type = self._detect_vpn_type(config_path)

            # Check if process is running
            if connection_name in self.active_processes:
                process = self.active_processes[connection_name]
                if process.poll() is None:
                    return "UP", "Process is running"
                else:
                    # Process exited, clean up
                    del self.active_processes[connection_name]
                    return "DOWN", "Process exited"

            # Check interface status
            if vpn_type == "openvpn":
                return self._check_openvpn_status(config_path)
            elif vpn_type == "wireguard":
                return self._check_wireguard_status(config_path)
            else:
                return "DOWN", "Unsupported VPN type"

        except Exception as e:
            self.logger.error(f"Error checking status for {connection_name}: {str(e)}")
            return "ERROR", f"Error: {str(e)}"

    def stop_all(self) -> Dict[str, Tuple[bool, str]]:
        """
        Stop all active VPN connections.

        Returns:
            Dictionary mapping connection names to (success, message) tuples
        """
        results = {}
        for connection_name in list(self.active_processes.keys()):
            results[connection_name] = self.stop_vpn(connection_name)
        return results

    def _start_openvpn(self, config_path: str) -> Optional[subprocess.Popen]:
        """Start an OpenVPN connection."""
        try:
            process = subprocess.Popen(
                ["sudo", "openvpn", "--config", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            return process
        except FileNotFoundError:
            self.logger.error("OpenVPN command not found. Is openvpn installed?")
            return None
        except Exception as e:
            self.logger.error(f"Failed to start OpenVPN: {str(e)}")
            return None

    def _stop_openvpn(self, process: subprocess.Popen) -> bool:
        """Stop an OpenVPN connection."""
        try:
            # Try to terminate gracefully first
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if terminate doesn't work
                process.kill()
                process.wait()
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop OpenVPN process: {str(e)}")
            return False

    def _start_wireguard(self, config_path: str) -> Optional[subprocess.Popen]:
        """Start a WireGuard connection."""
        try:
            interface = Path(config_path).stem
            process = subprocess.Popen(
                ["sudo", "wg-quick", "up", interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            return process
        except FileNotFoundError:
            self.logger.error("wg-quick command not found. Is wireguard-tools installed?")
            return None
        except Exception as e:
            self.logger.error(f"Failed to start WireGuard: {str(e)}")
            return None

    def _stop_wireguard(self, config_path: str) -> bool:
        """Stop a WireGuard connection."""
        try:
            interface = Path(config_path).stem
            result = subprocess.run(
                ["sudo", "wg-quick", "down", interface],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                self.logger.error(
                    f"Failed to stop WireGuard: {result.stderr or result.stdout}"
                )
                return False
            return True
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout stopping WireGuard interface")
            return False
        except Exception as e:
            self.logger.error(f"Failed to stop WireGuard: {str(e)}")
            return False

    def _check_openvpn_status(self, config_path: str) -> Tuple[str, str]:
        """Check the status of an OpenVPN connection."""
        try:
            interface = self._get_openvpn_interface(config_path)
            result = subprocess.run(
                ["ip", "link", "show", interface],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return "DOWN", f"Interface {interface} not found"

            if "UP" in result.stdout:
                # Check for IP address
                ip_result = subprocess.run(
                    ["ip", "addr", "show", interface],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if "inet " in ip_result.stdout:
                    return "UP", interface
                else:
                    return "CONNECTING", "Interface UP but no IP assigned"
            else:
                return "DOWN", "Interface not UP"

        except subprocess.TimeoutExpired:
            return "ERROR", "Timeout checking interface status"
        except Exception as e:
            return "ERROR", f"Error checking status: {str(e)}"

    def _check_wireguard_status(self, config_path: str) -> Tuple[str, str]:
        """Check the status of a WireGuard connection."""
        try:
            interface = Path(config_path).stem
            result = subprocess.run(
                ["wg", "show", interface],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
                # Check if interface has a handshake
                if "handshake:" in result.stdout:
                    return "UP", interface
                else:
                    return "CONNECTING", "Interface exists but no handshake"
            else:
                return "DOWN", f"Interface {interface} not found or inactive"

        except FileNotFoundError:
            # Fallback to ip link check
            try:
                result = subprocess.run(
                    ["ip", "link", "show", interface],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and "UP" in result.stdout:
                    return "UP", interface
                else:
                    return "DOWN", "Interface not UP"
            except Exception:
                return "DOWN", "Cannot determine status"
        except subprocess.TimeoutExpired:
            return "ERROR", "Timeout checking WireGuard status"
        except Exception as e:
            return "ERROR", f"Error checking status: {str(e)}"

    def _detect_vpn_type(self, config_path: str) -> str:
        """
        Detect the VPN type from the configuration file.

        Args:
            config_path: Path to the configuration file

        Returns:
            "openvpn", "wireguard", or "unknown"
        """
        if config_path.endswith(".ovpn"):
            return "openvpn"
        elif config_path.endswith(".conf"):
            try:
                with open(config_path, "r") as f:
                    content = f.read()
                    if "[Interface]" in content:
                        return "wireguard"
            except Exception:
                pass
            return "openvpn"  # Default to openvpn for .conf files
        return "unknown"

    def _get_openvpn_interface(self, config_path: str) -> str:
        """
        Get the interface name from an OpenVPN configuration file.

        Args:
            config_path: Path to the OpenVPN configuration file

        Returns:
            Interface name (default: "tun0")
        """
        try:
            with open(config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("dev ") and not line.startswith("dev-type"):
                        return line.split()[1].strip()
        except Exception:
            pass
        return "tun0"

    def _get_interface_for_connection(self, config_path: str, vpn_type: str) -> str:
        """
        Get the network interface for a connection.

        Args:
            config_path: Path to the configuration file
            vpn_type: Type of VPN (openvpn, wireguard)

        Returns:
            str: Network interface name
        """
        if vpn_type == "openvpn":
            return self._get_openvpn_interface(config_path)
        elif vpn_type == "wireguard":
            return Path(config_path).stem
        else:
            return "tun0"
