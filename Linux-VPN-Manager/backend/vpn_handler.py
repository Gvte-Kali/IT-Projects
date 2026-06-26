"""
VPN Handler Module

Handles VPN connection management for OpenVPN and WireGuard.
Provides start, stop, status checking, auto-reconnect, and DNS leak detection.
"""

import subprocess
import os
import re
import time
import threading
from pathlib import Path
from typing import Tuple, Dict, Optional, List, Callable
from datetime import datetime
import logging


class VPNHandler:
    """Handles VPN connection operations with auto-reconnect and DNS leak detection."""

    # Auto-reconnect settings
    AUTO_RECONNECT_ENABLED = True
    AUTO_RECONNECT_DELAY = 5  # seconds between reconnection attempts
    MAX_RECONNECT_ATTEMPTS = 3  # maximum reconnection attempts before giving up
    
    # DNS leak detection settings
    DNS_CHECK_INTERVAL = 30  # seconds between DNS checks
    DNS_TEST_DOMAIN = "dnsleaktest.com"
    DNS_EXPECTED_IPS = ["104.28.29.101"]  # Known IPs for dnsleaktest.com
    
    def __init__(self, config_manager, log_manager, stats_manager=None, 
                 history_manager=None, notification_manager=None):
        """
        Initialize VPN Handler.

        Args:
            config_manager: ConfigManager instance for managing configurations
            log_manager: LogManager instance for managing logs
            stats_manager: StatsManager instance for managing statistics (optional)
            history_manager: HistoryManager instance for tracking connection history (optional)
            notification_manager: NotificationManager instance for notifications (optional)
        """
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.stats_manager = stats_manager
        self.history_manager = history_manager
        self.notification_manager = notification_manager
        
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.active_connections: Dict[str, Dict[str, any]] = {}  # Extended connection info
        self.reconnect_threads: Dict[str, threading.Thread] = {}
        self.dns_monitor_threads: Dict[str, threading.Thread] = {}
        self.monitoring_active: Dict[str, bool] = {}
        
        self.logger = logging.getLogger("VPNHandler")
        
        # Callbacks for status changes
        self._status_callbacks: List[Callable] = []
        self._dns_leak_callbacks: List[Callable] = []

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
            
            # Store extended connection info
            self.active_connections[connection_name] = {
                "process": process,
                "config_path": config_path,
                "vpn_type": vpn_type,
                "start_time": datetime.now().isoformat(),
                "status": "connecting",
                "reconnect_attempts": 0,
                "dns_leak_detected": False,
            }
            
            self.log_manager.start_logging(connection_name, process.stdout)

            # Start stats monitoring if stats_manager is available
            if self.stats_manager is not None:
                interface = self._get_interface_for_connection(config_path, vpn_type)
                self.stats_manager.start_monitoring(connection_name, interface)
            
            # Start history session
            if self.history_manager is not None:
                self.history_manager.start_session(connection_name)
            
            # Start DNS leak monitoring in a separate thread
            if self.AUTO_RECONNECT_ENABLED and self.notification_manager is not None:
                self._start_dns_monitoring(connection_name)
            
            # Start connection monitoring for auto-reconnect
            if self.AUTO_RECONNECT_ENABLED:
                self._start_connection_monitoring(connection_name)

            self.logger.info(f"Successfully started {vpn_type} VPN: {connection_name}")
            self._notify_status_change(connection_name, "connecting")
            
            return True, f"Starting {vpn_type} VPN: {connection_name}"

        except Exception as e:
            self.logger.error(f"Failed to start VPN {connection_name}: {str(e)}")
            return False, f"Failed to start VPN: {str(e)}"

    def stop_vpn(self, connection_name: str, 
                end_status: str = "disconnected",
                error_message: Optional[str] = None) -> Tuple[bool, str]:
        """
        Stop a VPN connection.

        Args:
            connection_name: Name of the connection to stop
            end_status: Final status for the connection (disconnected, failed, timeout)
            error_message: Error message if connection failed

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
                            # Clean up monitoring
                            self._cleanup_connection(connection_name, end_status, error_message)
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
            self._cleanup_connection(connection_name, end_status, error_message)

            self.logger.info(f"Successfully stopped {vpn_type} VPN: {connection_name}")
            self._notify_status_change(connection_name, end_status)
            return True, f"Stopped VPN: {connection_name}"

        except Exception as e:
            self.logger.error(f"Failed to stop VPN {connection_name}: {str(e)}")
            self._cleanup_connection(connection_name, "failed", str(e))
            return False, f"Failed to stop VPN: {str(e)}"
    
    def _cleanup_connection(self, connection_name: str, 
                           end_status: str, 
                           error_message: Optional[str] = None) -> None:
        """
        Clean up all resources for a connection.
        
        Args:
            connection_name: Name of the connection
            end_status: Final status
            error_message: Error message if any
        """
        try:
            # Remove from active processes
            if connection_name in self.active_processes:
                del self.active_processes[connection_name]
            
            # Remove from active connections
            if connection_name in self.active_connections:
                conn_info = self.active_connections[connection_name]
                del self.active_connections[connection_name]
            else:
                conn_info = {}
            
            # Stop logging
            self.log_manager.stop_logging(connection_name)

            # Stop stats monitoring
            if self.stats_manager is not None:
                self.stats_manager.stop_monitoring(connection_name)
            
            # Stop DNS monitoring
            self._stop_dns_monitoring(connection_name)
            
            # Stop connection monitoring
            self._stop_connection_monitoring(connection_name)
            
            # End history session
            if self.history_manager is not None:
                # Get bytes from stats if available
                bytes_sent = 0
                bytes_received = 0
                if self.stats_manager is not None:
                    stats = self.stats_manager.get_stats(connection_name)
                    bytes_sent = stats.get("bytes_sent", 0)
                    bytes_received = stats.get("bytes_received", 0)
                
                # Map status to ConnectionStatus
                from backend.history_manager import ConnectionStatus
                status_map = {
                    "disconnected": ConnectionStatus.DISCONNECTED,
                    "failed": ConnectionStatus.FAILED,
                    "timeout": ConnectionStatus.TIMEOUT,
                }
                status = status_map.get(end_status, ConnectionStatus.DISCONNECTED)
                
                self.history_manager.end_session(
                    connection_name,
                    status=status,
                    bytes_sent=bytes_sent,
                    bytes_received=bytes_received,
                    error_message=error_message
                )
            
            # Send notification if connection failed
            if end_status != "disconnected" and self.notification_manager is not None:
                self.notification_manager.send_notification(
                    title="VPN Connection Failed",
                    message=f"Connection '{connection_name}' ended with status: {end_status}",
                    icon="dialog-error",
                    urgency=self.notification_manager.URGENCY_CRITICAL,
                    timeout=10000,
                )
            
        except Exception as e:
            self.logger.error(f"Error cleaning up connection {connection_name}: {str(e)}")

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

    # =========================================================================
    # DNS Leak Detection Methods
    # =========================================================================

    def _start_dns_monitoring(self, connection_name: str) -> None:
        """
        Start DNS leak monitoring for a connection.
        
        Args:
            connection_name: Name of the connection
        """
        try:
            if connection_name in self.dns_monitor_threads:
                return
            
            self.monitoring_active[connection_name] = True
            thread = threading.Thread(
                target=self._dns_monitor_worker,
                args=(connection_name,),
                daemon=True
            )
            thread.start()
            self.dns_monitor_threads[connection_name] = thread
            self.logger.info(f"Started DNS monitoring for {connection_name}")
        except Exception as e:
            self.logger.error(f"Error starting DNS monitoring for {connection_name}: {str(e)}")

    def _stop_dns_monitoring(self, connection_name: str) -> None:
        """
        Stop DNS leak monitoring for a connection.
        
        Args:
            connection_name: Name of the connection
        """
        try:
            self.monitoring_active[connection_name] = False
            if connection_name in self.dns_monitor_threads:
                del self.dns_monitor_threads[connection_name]
            self.logger.info(f"Stopped DNS monitoring for {connection_name}")
        except Exception as e:
            self.logger.error(f"Error stopping DNS monitoring for {connection_name}: {str(e)}")

    def _dns_monitor_worker(self, connection_name: str) -> None:
        """
        Worker thread that periodically checks for DNS leaks.
        
        Args:
            connection_name: Name of the connection
        """
        try:
            while self.monitoring_active.get(connection_name, False):
                # Wait before first check
                time.sleep(self.DNS_CHECK_INTERVAL)
                
                if not self.monitoring_active.get(connection_name, False):
                    break
                
                # Check for DNS leak
                leak_detected, dns_ips = self._check_dns_leak()
                
                if leak_detected:
                    # DNS leak detected!
                    self.logger.warning(f"DNS leak detected for {connection_name}: {dns_ips}")
                    
                    # Update connection info
                    if connection_name in self.active_connections:
                        self.active_connections[connection_name]["dns_leak_detected"] = True
                    
                    # Notify via callback
                    self._notify_dns_leak(connection_name, dns_ips)
                    
                    # Send notification
                    if self.notification_manager is not None:
                        self.notification_manager.send_notification(
                            title="⚠️ DNS Leak Detected!",
                            message=f"Connection '{connection_name}' has a DNS leak.\n"
                                   f"DNS servers: {', '.join(dns_ips)}",
                            icon="dialog-warning",
                            urgency=self.notification_manager.URGENCY_CRITICAL,
                            timeout=15000,
                        )
                    
                    # Log the leak
                    if self.log_manager is not None:
                        self.log_manager.log_message(
                            connection_name,
                            f"DNS LEAK DETECTED: {', '.join(dns_ips)}"
                        )
                else:
                    # No leak, update connection info
                    if connection_name in self.active_connections:
                        self.active_connections[connection_name]["dns_leak_detected"] = False
        except Exception as e:
            self.logger.error(f"DNS monitor error for {connection_name}: {str(e)}")

    def _check_dns_leak(self) -> Tuple[bool, List[str]]:
        """
        Check for DNS leaks by resolving a test domain.
        
        Returns:
            Tuple of (leak_detected: bool, dns_ips: List[str])
        """
        try:
            import socket
            import subprocess
            
            # Method 1: Use dig command if available
            try:
                result = subprocess.run(
                    ["dig", "+short", self.DNS_TEST_DOMAIN],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    dns_ips = [ip.strip() for ip in result.stdout.strip().split('\n') if ip.strip()]
                    return self._is_dns_leak(dns_ips)
            except Exception:
                pass
            
            # Method 2: Use nslookup
            try:
                result = subprocess.run(
                    ["nslookup", self.DNS_TEST_DOMAIN],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # Extract IPs from nslookup output
                    dns_ips = []
                    for line in result.stdout.split('\n'):
                        if line.strip().startswith("Address:") or line.strip().startswith("address ="):
                            ip = line.split()[-1].strip()
                            if self._is_valid_ip(ip):
                                dns_ips.append(ip)
                    return self._is_dns_leak(dns_ips)
            except Exception:
                pass
            
            # Method 3: Use Python socket
            try:
                dns_ips = []
                # Get all addresses for the test domain
                addr_info = socket.getaddrinfo(self.DNS_TEST_DOMAIN, None)
                for info in addr_info:
                    ip = info[4][0]
                    if self._is_valid_ip(ip):
                        dns_ips.append(ip)
                return self._is_dns_leak(dns_ips)
            except Exception:
                pass
            
            return False, []
            
        except Exception as e:
            self.logger.warning(f"Error checking DNS leak: {str(e)}")
            return False, []

    def _is_dns_leak(self, dns_ips: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if the resolved DNS IPs indicate a leak.
        
        Args:
            dns_ips: List of DNS server IPs
            
        Returns:
            Tuple of (leak_detected: bool, dns_ips: List[str])
        """
        try:
            if not dns_ips:
                return False, []
            
            # Check if any of the resolved IPs match expected VPN DNS servers
            # For now, we consider it a leak if we get public DNS servers
            # that are commonly associated with ISPs or public DNS services
            
            public_dns_servers = [
                "8.8.8.8",       # Google DNS
                "8.8.4.4",       # Google DNS
                "1.1.1.1",       # Cloudflare DNS
                "1.0.0.1",       # Cloudflare DNS
                "9.9.9.9",       # Quad9 DNS
                "149.112.112.112", # Quad9 DNS
                "208.67.222.222", # OpenDNS
                "208.67.220.220", # OpenDNS
            ]
            
            # If we detect public DNS servers while VPN is connected, it's a leak
            for ip in dns_ips:
                if ip in public_dns_servers:
                    return True, dns_ips
            
            # Also check if the DNS servers are in common ISP ranges
            # (This is a simplified check - in production, you'd want a more comprehensive list)
            isp_dns_ranges = [
                ("8.8.8.0", "8.8.8.255"),
                ("1.1.1.0", "1.1.1.255"),
                ("9.9.9.0", "9.9.9.255"),
            ]
            
            for ip in dns_ips:
                for start, end in isp_dns_ranges:
                    if self._ip_in_range(ip, start, end):
                        return True, dns_ips
            
            # If none of the above, no leak detected
            return False, dns_ips
            
        except Exception as e:
            self.logger.warning(f"Error checking DNS leak status: {str(e)}")
            return False, dns_ips

    def _is_valid_ip(self, ip: str) -> bool:
        """
        Check if a string is a valid IPv4 address.
        
        Args:
            ip: IP address string
            
        Returns:
            True if valid IPv4 address
        """
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not part.isdigit():
                    return False
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except Exception:
            return False

    def _ip_in_range(self, ip: str, start: str, end: str) -> bool:
        """
        Check if an IP is in a range.
        
        Args:
            ip: IP address to check
            start: Start of range
            end: End of range
            
        Returns:
            True if IP is in range
        """
        try:
            def ip_to_int(ip_str):
                parts = list(map(int, ip_str.split('.')))
                return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
            
            ip_int = ip_to_int(ip)
            start_int = ip_to_int(start)
            end_int = ip_to_int(end)
            
            return start_int <= ip_int <= end_int
        except Exception:
            return False

    # =========================================================================
    # Connection Monitoring and Auto-Reconnect Methods
    # =========================================================================

    def _start_connection_monitoring(self, connection_name: str) -> None:
        """
        Start connection monitoring for auto-reconnect.
        
        Args:
            connection_name: Name of the connection
        """
        try:
            if connection_name in self.reconnect_threads:
                return
            
            self.monitoring_active[connection_name] = True
            thread = threading.Thread(
                target=self._connection_monitor_worker,
                args=(connection_name,),
                daemon=True
            )
            thread.start()
            self.reconnect_threads[connection_name] = thread
            self.logger.info(f"Started connection monitoring for {connection_name}")
        except Exception as e:
            self.logger.error(f"Error starting connection monitoring for {connection_name}: {str(e)}")

    def _stop_connection_monitoring(self, connection_name: str) -> None:
        """
        Stop connection monitoring for a connection.
        
        Args:
            connection_name: Name of the connection
        """
        try:
            self.monitoring_active[connection_name] = False
            if connection_name in self.reconnect_threads:
                del self.reconnect_threads[connection_name]
            self.logger.info(f"Stopped connection monitoring for {connection_name}")
        except Exception as e:
            self.logger.error(f"Error stopping connection monitoring for {connection_name}: {str(e)}")

    def _connection_monitor_worker(self, connection_name: str) -> None:
        """
        Worker thread that monitors connection status and handles auto-reconnect.
        
        Args:
            connection_name: Name of the connection
        """
        try:
            while self.monitoring_active.get(connection_name, False):
                # Check if process is still running
                if connection_name not in self.active_processes:
                    break
                
                process = self.active_processes[connection_name]
                
                # Check process status
                return_code = process.poll()
                
                if return_code is not None:
                    # Process has terminated
                    self.logger.warning(f"VPN process for {connection_name} has terminated with code {return_code}")
                    
                    # Update connection status
                    if connection_name in self.active_connections:
                        self.active_connections[connection_name]["status"] = "failed"
                    
                    # Attempt auto-reconnect
                    if self.AUTO_RECONNECT_ENABLED:
                        self._attempt_auto_reconnect(connection_name)
                    
                    break
                
                # Check every 5 seconds
                time.sleep(5)
                
        except Exception as e:
            self.logger.error(f"Connection monitor error for {connection_name}: {str(e)}")

    def _attempt_auto_reconnect(self, connection_name: str) -> None:
        """
        Attempt to auto-reconnect a failed VPN connection.
        
        Args:
            connection_name: Name of the connection
        """
        try:
            if connection_name not in self.active_connections:
                return
            
            conn_info = self.active_connections[connection_name]
            
            # Increment reconnection attempt counter
            conn_info["reconnect_attempts"] = conn_info.get("reconnect_attempts", 0) + 1
            
            if conn_info["reconnect_attempts"] > self.MAX_RECONNECT_ATTEMPTS:
                self.logger.warning(f"Max reconnection attempts reached for {connection_name}")
                
                # Stop monitoring
                self._stop_connection_monitoring(connection_name)
                self._stop_dns_monitoring(connection_name)
                
                # Clean up
                self._cleanup_connection(connection_name, "failed", 
                                       f"Max reconnection attempts ({self.MAX_RECONNECT_ATTEMPTS}) reached")
                
                # Send notification
                if self.notification_manager is not None:
                    self.notification_manager.send_notification(
                        title="VPN Connection Failed",
                        message=f"Connection '{connection_name}' could not be re-established after "
                               f"{self.MAX_RECONNECT_ATTEMPTS} attempts.",
                        icon="dialog-error",
                        urgency=self.notification_manager.URGENCY_CRITICAL,
                        timeout=10000,
                    )
                return
            
            # Wait before reconnecting
            self.logger.info(f"Attempting to reconnect {connection_name} (attempt {conn_info['reconnect_attempts']})")
            
            # Send notification
            if self.notification_manager is not None:
                self.notification_manager.send_notification(
                    title="VPN Reconnecting",
                    message=f"Attempting to reconnect '{connection_name}'...",
                    icon="dialog-information",
                    urgency=self.notification_manager.URGENCY_NORMAL,
                    timeout=5000,
                )
            
            # Wait before reconnection
            time.sleep(self.AUTO_RECONNECT_DELAY)
            
            # Try to restart the connection
            config_path = conn_info.get("config_path")
            if config_path:
                success, message = self.start_vpn(config_path, connection_name)
                
                if success:
                    self.logger.info(f"Successfully reconnected {connection_name}")
                    
                    # Reset reconnection counter
                    conn_info["reconnect_attempts"] = 0
                    
                    # Send notification
                    if self.notification_manager is not None:
                        self.notification_manager.send_notification(
                            title="VPN Reconnected",
                            message=f"Connection '{connection_name}' has been re-established.",
                            icon="dialog-info",
                            urgency=self.notification_manager.URGENCY_NORMAL,
                            timeout=5000,
                        )
                    
                    # Notify status change
                    self._notify_status_change(connection_name, "connected")
                else:
                    self.logger.warning(f"Reconnection attempt failed for {connection_name}: {message}")
            
        except Exception as e:
            self.logger.error(f"Error attempting auto-reconnect for {connection_name}: {str(e)}")

    # =========================================================================
    # Callback Methods
    # =========================================================================

    def register_status_callback(self, callback: Callable) -> None:
        """
        Register a callback for connection status changes.
        
        Args:
            callback: Function to call when status changes. 
                     Signature: callback(connection_name: str, status: str)
        """
        self._status_callbacks.append(callback)

    def unregister_status_callback(self, callback: Callable) -> None:
        """
        Unregister a status callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def _notify_status_change(self, connection_name: str, status: str) -> None:
        """
        Notify all registered callbacks of a status change.
        
        Args:
            connection_name: Name of the connection
            status: New status
        """
        for callback in self._status_callbacks:
            try:
                callback(connection_name, status)
            except Exception as e:
                self.logger.error(f"Error in status callback: {str(e)}")

    def register_dns_leak_callback(self, callback: Callable) -> None:
        """
        Register a callback for DNS leak detection.
        
        Args:
            callback: Function to call when DNS leak is detected.
                     Signature: callback(connection_name: str, dns_ips: List[str])
        """
        self._dns_leak_callbacks.append(callback)

    def unregister_dns_leak_callback(self, callback: Callable) -> None:
        """
        Unregister a DNS leak callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._dns_leak_callbacks:
            self._dns_leak_callbacks.remove(callback)

    def _notify_dns_leak(self, connection_name: str, dns_ips: List[str]) -> None:
        """
        Notify all registered callbacks of a DNS leak.
        
        Args:
            connection_name: Name of the connection
            dns_ips: List of DNS server IPs that caused the leak
        """
        for callback in self._dns_leak_callbacks:
            try:
                callback(connection_name, dns_ips)
            except Exception as e:
                self.logger.error(f"Error in DNS leak callback: {str(e)}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_connection_info(self, connection_name: str) -> Optional[Dict[str, any]]:
        """
        Get information about an active connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Dictionary with connection info or None if not found
        """
        return self.active_connections.get(connection_name)

    def get_all_connections_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get information about all active connections.
        
        Returns:
            Dictionary with all connection infos
        """
        return self.active_connections.copy()

    def is_dns_leak_detected(self, connection_name: str) -> bool:
        """
        Check if a DNS leak has been detected for a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            True if DNS leak detected
        """
        conn_info = self.active_connections.get(connection_name)
        if conn_info:
            return conn_info.get("dns_leak_detected", False)
        return False

    def get_dns_status(self, connection_name: str) -> Dict[str, any]:
        """
        Get DNS status for a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Dictionary with DNS status information
        """
        leak_detected, dns_ips = self._check_dns_leak()
        return {
            "leak_detected": leak_detected,
            "dns_ips": dns_ips,
            "expected_ips": self.DNS_EXPECTED_IPS,
        }

    def check_connection_health(self, connection_name: str) -> Dict[str, any]:
        """
        Check the health of a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Dictionary with health status
        """
        if connection_name not in self.active_connections:
            return {"status": "not_connected", "healthy": False}
        
        conn_info = self.active_connections[connection_name]
        
        # Check if process is running
        if connection_name in self.active_processes:
            process = self.active_processes[connection_name]
            if process.poll() is not None:
                return {"status": "process_dead", "healthy": False}
        
        # Check for DNS leaks
        dns_status = self.get_dns_status(connection_name)
        
        return {
            "status": conn_info.get("status", "unknown"),
            "healthy": not dns_status["leak_detected"],
            "dns_leak": dns_status["leak_detected"],
            "dns_ips": dns_status["dns_ips"],
        }
