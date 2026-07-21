"""
VPN Handler - Manages VPN connections
"""

import subprocess
import os
import socket
import threading
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Callable

from .config import (
    STATUS_DISCONNECTED, STATUS_CONNECTING, STATUS_CONNECTED, 
    STATUS_FAILED, DNS_TEST_DOMAIN, DNS_CHECK_INTERVAL,
    AUTO_RECONNECT_DELAY, MAX_RECONNECT_ATTEMPTS, VPN_OPENVPN, VPN_WIREGUARD
)

logger = logging.getLogger("VPNHandler")


class VPNHandler:
    """Handles VPN connection operations."""
    
    def __init__(self, profile_manager):
        """Initialize VPN handler."""
        self.profile_manager = profile_manager
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.active_connections: Dict[str, Dict] = {}
        self.reconnect_threads: Dict[str, threading.Thread] = {}
        self.dns_monitor_threads: Dict[str, threading.Thread] = {}
        self.monitoring_active: Dict[str, bool] = {}
        self._status_callbacks: List[Callable] = []
        self._dns_leak_callbacks: List[Callable] = []
    
    def start_vpn(self, profile_name: str) -> Tuple[bool, str]:
        """Start a VPN connection."""
        try:
            profile = self.profile_manager.get_profile(profile_name)
            if not profile:
                return False, f"Profile '{profile_name}' not found"
            
            config_path = profile.get("path", "")
            vpn_type = profile.get("type", VPN_OPENVPN)
            extra_args = profile.get("extra_args", "")
            
            if not os.path.exists(config_path):
                return False, f"Config file does not exist: {config_path}"
            
            logger.info(f"Starting {vpn_type} VPN: {profile_name}")
            
            # Stop any existing connection with the same name
            if profile_name in self.active_processes:
                self.stop_vpn(profile_name)
            
            # Build command
            if vpn_type == VPN_OPENVPN:
                cmd = ["sudo", "openvpn", "--config", config_path]
                if extra_args:
                    cmd.extend(extra_args.split())
            elif vpn_type == VPN_WIREGUARD:
                interface = Path(config_path).stem
                cmd = ["sudo", "wg-quick", "up", interface]
                if extra_args:
                    cmd.extend(extra_args.split())
            else:
                return False, f"Unsupported VPN type: {vpn_type}"
            
            process = self._start_process(cmd)
            if process is None:
                return False, f"Failed to start {vpn_type} process"
            
            # Store connection info
            self.active_processes[profile_name] = process
            self.active_connections[profile_name] = {
                "profile": profile,
                "process": process,
                "status": STATUS_CONNECTING,
                "start_time": datetime.now().isoformat(),
                "reconnect_attempts": 0,
                "dns_leak_detected": False,
            }
            
            # Start monitoring
            self._start_connection_monitoring(profile_name)
            self._start_dns_monitoring(profile_name)
            
            # Notify status change
            self._notify_status_change(profile_name, STATUS_CONNECTING)
            
            logger.info(f"Successfully started {vpn_type} VPN: {profile_name}")
            return True, f"Starting {vpn_type} VPN: {profile_name}"
            
        except Exception as e:
            logger.error(f"Failed to start VPN {profile_name}: {e}")
            return False, f"Failed to start VPN: {str(e)}"
    
    def stop_vpn(self, profile_name: str, end_status: str = STATUS_DISCONNECTED,
                error_message: Optional[str] = None) -> Tuple[bool, str]:
        """Stop a VPN connection."""
        try:
            if profile_name not in self.active_processes:
                profile = self.profile_manager.get_profile(profile_name)
                if profile:
                    vpn_type = profile.get("type", VPN_OPENVPN)
                    config_path = profile.get("path", "")
                    if vpn_type == VPN_WIREGUARD:
                        interface = Path(config_path).stem
                        try:
                            subprocess.run(
                                ["sudo", "wg-quick", "down", interface],
                                check=True,
                                capture_output=True
                            )
                            logger.info(f"Stopped WireGuard interface {interface}")
                            self._cleanup_connection(profile_name, end_status, error_message)
                            return True, f"Stopped VPN: {profile_name}"
                        except subprocess.CalledProcessError as e:
                            logger.warning(f"Failed to stop WireGuard: {e}")
                return False, f"No active VPN process for: {profile_name}"
            
            process = self.active_processes[profile_name]
            profile = self.active_connections[profile_name].get("profile", {})
            vpn_type = profile.get("type", VPN_OPENVPN)
            
            logger.info(f"Stopping {vpn_type} VPN: {profile_name}")
            
            # Terminate process
            self._stop_process(process)
            
            # Clean up
            self._cleanup_connection(profile_name, end_status, error_message)
            
            logger.info(f"Successfully stopped {vpn_type} VPN: {profile_name}")
            self._notify_status_change(profile_name, end_status)
            return True, f"Stopped VPN: {profile_name}"
            
        except Exception as e:
            logger.error(f"Failed to stop VPN {profile_name}: {e}")
            self._cleanup_connection(profile_name, STATUS_FAILED, str(e))
            return False, f"Failed to stop VPN: {str(e)}"
    
    def _cleanup_connection(self, profile_name: str, end_status: str,
                           error_message: Optional[str] = None) -> None:
        """Clean up all resources for a connection."""
        try:
            if profile_name in self.active_processes:
                del self.active_processes[profile_name]
            
            if profile_name in self.active_connections:
                del self.active_connections[profile_name]
            
            # Stop monitoring
            self._stop_connection_monitoring(profile_name)
            self._stop_dns_monitoring(profile_name)
            
            # Notify status change
            self._notify_status_change(profile_name, end_status)
            
        except Exception as e:
            logger.error(f"Error cleaning up connection {profile_name}: {e}")
    
    def get_status(self, profile_name: str) -> Tuple[str, str]:
        """Get the status of a VPN connection."""
        try:
            if profile_name not in self.active_connections:
                return STATUS_DISCONNECTED, "Not connected"
            
            conn_info = self.active_connections[profile_name]
            status = conn_info.get("status", STATUS_DISCONNECTED)
            
            # Check if process is still running
            if profile_name in self.active_processes:
                process = self.active_processes[profile_name]
                if process.poll() is not None:
                    del self.active_processes[profile_name]
                    conn_info["status"] = STATUS_DISCONNECTED
                    return STATUS_DISCONNECTED, "Process exited"
            
            return status, f"Status: {status}"
            
        except Exception as e:
            logger.error(f"Error checking status for {profile_name}: {e}")
            return STATUS_FAILED, f"Error: {str(e)}"
    
    def stop_all(self) -> Dict[str, Tuple[bool, str]]:
        """Stop all active VPN connections."""
        results = {}
        for profile_name in list(self.active_processes.keys()):
            results[profile_name] = self.stop_vpn(profile_name)
        return results
    
    def _start_process(self, cmd: List[str]) -> Optional[subprocess.Popen]:
        """Start a subprocess."""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            return process
        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            return None
    
    def _stop_process(self, process: subprocess.Popen) -> bool:
        """Stop a subprocess."""
        try:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return True
        except Exception as e:
            logger.error(f"Failed to stop process: {e}")
            return False
    
    # DNS Leak Detection
    def _start_dns_monitoring(self, profile_name: str) -> None:
        """Start DNS leak monitoring for a connection."""
        try:
            if profile_name in self.dns_monitor_threads:
                return
            
            self.monitoring_active[profile_name] = True
            thread = threading.Thread(
                target=self._dns_monitor_worker,
                args=(profile_name,),
                daemon=True
            )
            thread.start()
            self.dns_monitor_threads[profile_name] = thread
        except Exception as e:
            logger.error(f"Error starting DNS monitoring: {e}")
    
    def _stop_dns_monitoring(self, profile_name: str) -> None:
        """Stop DNS leak monitoring."""
        try:
            self.monitoring_active[profile_name] = False
            if profile_name in self.dns_monitor_threads:
                del self.dns_monitor_threads[profile_name]
        except Exception as e:
            logger.error(f"Error stopping DNS monitoring: {e}")
    
    def _dns_monitor_worker(self, profile_name: str) -> None:
        """Worker thread for DNS leak monitoring."""
        try:
            while self.monitoring_active.get(profile_name, False):
                time.sleep(DNS_CHECK_INTERVAL)
                
                if not self.monitoring_active.get(profile_name, False):
                    break
                
                leak_detected, dns_ips = self._check_dns_leak()
                
                if leak_detected:
                    if profile_name in self.active_connections:
                        self.active_connections[profile_name]["dns_leak_detected"] = True
                    self._notify_dns_leak(profile_name, dns_ips)
                else:
                    if profile_name in self.active_connections:
                        self.active_connections[profile_name]["dns_leak_detected"] = False
                        
        except Exception as e:
            logger.error(f"DNS monitor error: {e}")
    
    def _check_dns_leak(self) -> Tuple[bool, List[str]]:
        """Check for DNS leaks."""
        try:
            # Method 1: Use dig
            try:
                result = subprocess.run(
                    ["dig", "+short", DNS_TEST_DOMAIN],
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
                    ["nslookup", DNS_TEST_DOMAIN],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
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
                addr_info = socket.getaddrinfo(DNS_TEST_DOMAIN, None)
                for info in addr_info:
                    ip = info[4][0]
                    if self._is_valid_ip(ip):
                        dns_ips.append(ip)
                return self._is_dns_leak(dns_ips)
            except Exception:
                pass
            
            return False, []
            
        except Exception as e:
            logger.warning(f"Error checking DNS leak: {e}")
            return False, []
    
    def _is_dns_leak(self, dns_ips: List[str]) -> Tuple[bool, List[str]]:
        """Check if resolved DNS IPs indicate a leak."""
        try:
            if not dns_ips:
                return False, []
            
            public_dns = [
                "8.8.8.8", "8.8.4.4",       # Google DNS
                "1.1.1.1", "1.0.0.1",       # Cloudflare DNS
                "9.9.9.9", "149.112.112.112", # Quad9 DNS
                "208.67.222.222", "208.67.220.220", # OpenDNS
            ]
            
            for ip in dns_ips:
                if ip in public_dns:
                    return True, dns_ips
            
            return False, dns_ips
            
        except Exception as e:
            logger.warning(f"Error checking DNS leak status: {e}")
            return False, dns_ips
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if a string is a valid IPv4 address."""
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
    
    # Connection Monitoring and Auto-Reconnect
    def _start_connection_monitoring(self, profile_name: str) -> None:
        """Start connection monitoring for auto-reconnect."""
        try:
            if profile_name in self.reconnect_threads:
                return
            
            self.monitoring_active[profile_name] = True
            thread = threading.Thread(
                target=self._connection_monitor_worker,
                args=(profile_name,),
                daemon=True
            )
            thread.start()
            self.reconnect_threads[profile_name] = thread
        except Exception as e:
            logger.error(f"Error starting connection monitoring: {e}")
    
    def _stop_connection_monitoring(self, profile_name: str) -> None:
        """Stop connection monitoring."""
        try:
            self.monitoring_active[profile_name] = False
            if profile_name in self.reconnect_threads:
                del self.reconnect_threads[profile_name]
        except Exception as e:
            logger.error(f"Error stopping connection monitoring: {e}")
    
    def _connection_monitor_worker(self, profile_name: str) -> None:
        """Worker thread for connection monitoring."""
        try:
            while self.monitoring_active.get(profile_name, False):
                if profile_name not in self.active_processes:
                    break
                
                process = self.active_processes[profile_name]
                return_code = process.poll()
                
                if return_code is not None:
                    logger.warning(f"VPN process for {profile_name} has terminated with code {return_code}")
                    
                    if profile_name in self.active_connections:
                        self.active_connections[profile_name]["status"] = STATUS_FAILED
                    
                    self._attempt_auto_reconnect(profile_name)
                    break
                
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"Connection monitor error: {e}")
    
    def _attempt_auto_reconnect(self, profile_name: str) -> None:
        """Attempt to auto-reconnect a failed VPN connection."""
        try:
            if profile_name not in self.active_connections:
                return
            
            conn_info = self.active_connections[profile_name]
            conn_info["reconnect_attempts"] = conn_info.get("reconnect_attempts", 0) + 1
            
            if conn_info["reconnect_attempts"] > MAX_RECONNECT_ATTEMPTS:
                logger.warning(f"Max reconnection attempts reached for {profile_name}")
                self._stop_connection_monitoring(profile_name)
                self._stop_dns_monitoring(profile_name)
                self._cleanup_connection(
                    profile_name, 
                    STATUS_FAILED, 
                    f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached"
                )
                return
            
            logger.info(f"Attempting to reconnect {profile_name} (attempt {conn_info['reconnect_attempts']})")
            time.sleep(AUTO_RECONNECT_DELAY)
            
            profile = conn_info.get("profile", {})
            if profile:
                success, message = self.start_vpn(profile_name)
                if success:
                    logger.info(f"Successfully reconnected {profile_name}")
                    conn_info["reconnect_attempts"] = 0
                    self._notify_status_change(profile_name, STATUS_CONNECTED)
                else:
                    logger.warning(f"Reconnection attempt failed for {profile_name}: {message}")
                    
        except Exception as e:
            logger.error(f"Error attempting auto-reconnect: {e}")
    
    # Callback Methods
    def register_status_callback(self, callback: Callable) -> None:
        """Register a callback for connection status changes."""
        self._status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable) -> None:
        """Unregister a status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_status_change(self, profile_name: str, status: str) -> None:
        """Notify all registered callbacks of a status change."""
        for callback in self._status_callbacks:
            try:
                callback(profile_name, status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    def register_dns_leak_callback(self, callback: Callable) -> None:
        """Register a callback for DNS leak detection."""
        self._dns_leak_callbacks.append(callback)
    
    def unregister_dns_leak_callback(self, callback: Callable) -> None:
        """Unregister a DNS leak callback."""
        if callback in self._dns_leak_callbacks:
            self._dns_leak_callbacks.remove(callback)
    
    def _notify_dns_leak(self, profile_name: str, dns_ips: List[str]) -> None:
        """Notify all registered callbacks of a DNS leak."""
        for callback in self._dns_leak_callbacks:
            try:
                callback(profile_name, dns_ips)
            except Exception as e:
                logger.error(f"Error in DNS leak callback: {e}")
    
    def get_connection_info(self, profile_name: str) -> Optional[Dict]:
        """Get information about an active connection."""
        return self.active_connections.get(profile_name)
    
    def is_dns_leak_detected(self, profile_name: str) -> bool:
        """Check if a DNS leak has been detected."""
        conn_info = self.active_connections.get(profile_name)
        if conn_info:
            return conn_info.get("dns_leak_detected", False)
        return False
