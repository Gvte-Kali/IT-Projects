"""
Statistics Manager Module

Tracks and manages connection statistics for VPN Manager.
Provides real-time monitoring of bandwidth, connection time, and other metrics.
"""

import time
import threading
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import logging

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class ConnectionStats:
    """Statistics for a single VPN connection."""
    connection_name: str
    interface: str
    
    # Timing
    start_time: float = 0.0
    last_activity: float = 0.0
    total_connected_time: float = 0.0
    
    # Bandwidth
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    
    # Rates (bytes per second)
    current_send_rate: float = 0.0
    current_recv_rate: float = 0.0
    peak_send_rate: float = 0.0
    peak_recv_rate: float = 0.0
    
    # History (last N samples for graphing)
    send_rate_history: deque = field(default_factory=lambda: deque(maxlen=60))
    recv_rate_history: deque = field(default_factory=lambda: deque(maxlen=60))
    
    # Errors
    errors: int = 0
    drops: int = 0
    
    # Connection count
    connection_count: int = 0
    
    def update_rates(self, new_send: int, new_recv: int, new_packets_sent: int, new_packets_recv: int):
        """Update bandwidth statistics."""
        current_time = time.time()
        time_diff = current_time - self.last_activity
        
        if self.last_activity > 0 and time_diff > 0:
            # Calculate rates
            send_diff = new_send - self.bytes_sent
            recv_diff = new_recv - self.bytes_recv
            
            self.current_send_rate = send_diff / time_diff if time_diff > 0 else 0
            self.current_recv_rate = recv_diff / time_diff if time_diff > 0 else 0
            
            # Update peak rates
            self.peak_send_rate = max(self.peak_send_rate, self.current_send_rate)
            self.peak_recv_rate = max(self.peak_recv_rate, self.current_recv_rate)
            
            # Add to history
            self.send_rate_history.append(self.current_send_rate)
            self.recv_rate_history.append(self.current_recv_rate)
        
        # Update totals
        self.bytes_sent = new_send
        self.bytes_recv = new_recv
        self.packets_sent = new_packets_sent
        self.packets_recv = new_packets_recv
        self.last_activity = current_time

    def get_session_time(self) -> float:
        """Get the current session time in seconds."""
        if self.start_time > 0:
            return time.time() - self.start_time
        return 0.0

    def get_total_time(self) -> float:
        """Get the total connected time in seconds."""
        return self.total_connected_time + self.get_session_time()

    def get_send_speed(self) -> str:
        """Get formatted send speed."""
        return self._format_bytes(self.current_send_rate)

    def get_recv_speed(self) -> str:
        """Get formatted receive speed."""
        return self._format_bytes(self.current_recv_rate)

    def get_total_sent(self) -> str:
        """Get formatted total sent bytes."""
        return self._format_bytes(self.bytes_sent)

    def get_total_recv(self) -> str:
        """Get formatted total received bytes."""
        return self._format_bytes(self.bytes_recv)

    def get_peak_send_speed(self) -> str:
        """Get formatted peak send speed."""
        return self._format_bytes(self.peak_send_rate)

    def get_peak_recv_speed(self) -> str:
        """Get formatted peak receive speed."""
        return self._format_bytes(self.peak_recv_rate)

    @staticmethod
    def _format_bytes(bytes_per_second: float) -> str:
        """Format bytes per second to human-readable string."""
        if bytes_per_second < 1024:
            return f"{bytes_per_second:.1f} B/s"
        elif bytes_per_second < 1024 * 1024:
            return f"{bytes_per_second / 1024:.1f} KB/s"
        elif bytes_per_second < 1024 * 1024 * 1024:
            return f"{bytes_per_second / (1024 * 1024):.1f} MB/s"
        else:
            return f"{bytes_per_second / (1024 * 1024 * 1024):.1f} GB/s"

    @staticmethod
    def _format_bytes_total(bytes_total: int) -> str:
        """Format total bytes to human-readable string."""
        if bytes_total < 1024:
            return f"{bytes_total} B"
        elif bytes_total < 1024 * 1024:
            return f"{bytes_total / 1024:.1f} KB"
        elif bytes_total < 1024 * 1024 * 1024:
            return f"{bytes_total / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_total / (1024 * 1024 * 1024):.1f} GB"


@dataclass
class GlobalStats:
    """Global statistics across all connections."""
    total_connections: int = 0
    active_connections: int = 0
    total_bytes_sent: int = 0
    total_bytes_recv: int = 0
    total_session_time: float = 0.0
    total_errors: int = 0
    
    def get_total_speed(self) -> Tuple[str, str]:
        """Get formatted total send and receive speeds."""
        # This would need to be calculated from individual connection stats
        return ("0 B/s", "0 B/s")


class StatsManager:
    """Manages statistics collection and monitoring for VPN connections."""

    def __init__(self):
        """Initialize the Stats Manager."""
        self.logger = logging.getLogger("StatsManager")
        self._stats: Dict[str, ConnectionStats] = {}
        self._global_stats = GlobalStats()
        self._monitoring_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._running = True
        self._monitor_interval = 1.0  # seconds

    def start_monitoring(self, connection_name: str, interface: str):
        """
        Start monitoring a VPN connection.

        Args:
            connection_name: Name of the connection
            interface: Network interface name
        """
        with self._lock:
            if connection_name in self._stats:
                # Connection already being monitored
                self.logger.warning(f"Connection {connection_name} is already being monitored")
                return

            # Create stats object
            stats = ConnectionStats(
                connection_name=connection_name,
                interface=interface,
                start_time=time.time(),
                last_activity=time.time()
            )
            self._stats[connection_name] = stats

            # Start monitoring thread
            thread = threading.Thread(
                target=self._monitor_connection,
                args=(connection_name, interface),
                daemon=True
            )
            thread.start()
            self._monitoring_threads[connection_name] = thread

            # Update global stats
            self._global_stats.total_connections += 1
            self._global_stats.active_connections += 1

            self.logger.info(f"Started monitoring connection: {connection_name} (interface: {interface})")

    def stop_monitoring(self, connection_name: str):
        """
        Stop monitoring a VPN connection.

        Args:
            connection_name: Name of the connection
        """
        with self._lock:
            if connection_name not in self._stats:
                return

            # Update total connected time
            stats = self._stats[connection_name]
            stats.total_connected_time += stats.get_session_time()

            # Stop the monitoring thread
            if connection_name in self._monitoring_threads:
                # The thread will stop when the connection is removed
                del self._monitoring_threads[connection_name]

            # Update global stats
            self._global_stats.active_connections -= 1

            self.logger.info(f"Stopped monitoring connection: {connection_name}")

    def _monitor_connection(self, connection_name: str, interface: str):
        """
        Monitor a single connection in a background thread.

        Args:
            connection_name: Name of the connection
            interface: Network interface name
        """
        try:
            while self._running and connection_name in self._stats:
                # Get network stats for the interface
                if PSUTIL_AVAILABLE:
                    self._update_from_psutil(connection_name, interface)
                else:
                    self._update_from_ip_command(connection_name, interface)

                # Sleep for the monitor interval
                time.sleep(self._monitor_interval)

        except Exception as e:
            self.logger.error(f"Error monitoring connection {connection_name}: {str(e)}")

    def _update_from_psutil(self, connection_name: str, interface: str):
        """Update stats using psutil."""
        try:
            # Get network IO counters
            io_counters = psutil.net_io_counters(pernic=True)
            if interface in io_counters:
                counters = io_counters[interface]
                with self._lock:
                    if connection_name in self._stats:
                        stats = self._stats[connection_name]
                        stats.update_rates(
                            counters.bytes_sent,
                            counters.bytes_recv,
                            counters.packets_sent,
                            counters.packets_recv
                        )
                        
                        # Update errors and drops
                        stats.errors = counters.errin + counters.errout
                        stats.drops = counters.dropin + counters.dropout

        except Exception as e:
            self.logger.debug(f"Error updating stats with psutil: {str(e)}")

    def _update_from_ip_command(self, connection_name: str, interface: str):
        """Update stats using ip command (fallback when psutil is not available)."""
        try:
            import subprocess
            
            # Get bytes sent and received
            result = subprocess.run(
                ["ip", "-s", "link", "show", interface],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse the output to get bytes
                lines = result.stdout.splitlines()
                for line in lines:
                    if "RX:" in line or "bytes" in line:
                        # This is a simplified parser - actual implementation would need to parse properly
                        pass

        except Exception as e:
            self.logger.debug(f"Error updating stats with ip command: {str(e)}")

    def get_stats(self, connection_name: str) -> Optional[ConnectionStats]:
        """
        Get statistics for a specific connection.

        Args:
            connection_name: Name of the connection

        Returns:
            ConnectionStats: Statistics for the connection, or None if not found
        """
        with self._lock:
            return self._stats.get(connection_name)

    def get_all_stats(self) -> Dict[str, ConnectionStats]:
        """
        Get statistics for all connections.

        Returns:
            Dict[str, ConnectionStats]: Statistics for all connections
        """
        with self._lock:
            return self._stats.copy()

    def get_global_stats(self) -> GlobalStats:
        """
        Get global statistics.

        Returns:
            GlobalStats: Global statistics
        """
        with self._lock:
            # Calculate totals from all connections
            total_sent = sum(stats.bytes_sent for stats in self._stats.values())
            total_recv = sum(stats.bytes_recv for stats in self._stats.values())
            total_errors = sum(stats.errors for stats in self._stats.values())
            
            self._global_stats.total_bytes_sent = total_sent
            self._global_stats.total_bytes_recv = total_recv
            self._global_stats.total_errors = total_errors
            
            return self._global_stats

    def get_connection_history(self, connection_name: str, max_samples: int = 60) -> Tuple[List[float], List[float]]:
        """
        Get the send and receive rate history for a connection.

        Args:
            connection_name: Name of the connection
            max_samples: Maximum number of samples to return

        Returns:
            Tuple[List[float], List[float]]: (send_rates, recv_rates)
        """
        with self._lock:
            if connection_name not in self._stats:
                return ([], [])
            
            stats = self._stats[connection_name]
            send_rates = list(stats.send_rate_history)[-max_samples:]
            recv_rates = list(stats.recv_rate_history)[-max_samples:]
            
            return (send_rates, recv_rates)

    def get_formatted_stats(self, connection_name: str) -> Dict[str, str]:
        """
        Get formatted statistics for a connection.

        Args:
            connection_name: Name of the connection

        Returns:
            Dict[str, str]: Formatted statistics
        """
        stats = self.get_stats(connection_name)
        if stats is None:
            return {}

        return {
            "session_time": self._format_time(stats.get_session_time()),
            "total_time": self._format_time(stats.get_total_time()),
            "send_speed": stats.get_send_speed(),
            "recv_speed": stats.get_recv_speed(),
            "total_sent": stats.get_total_sent(),
            "total_recv": stats.get_total_recv(),
            "peak_send": stats.get_peak_send_speed(),
            "peak_recv": stats.get_peak_recv_speed(),
            "packets_sent": str(stats.packets_sent),
            "packets_recv": str(stats.packets_recv),
            "errors": str(stats.errors),
            "drops": str(stats.drops),
        }

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to human-readable time string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m {int(seconds % 60)}s"
        elif seconds < 86400:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            return f"{hours:.0f}h {minutes:.0f}m"
        else:
            days = seconds / 86400
            hours = (seconds % 86400) / 3600
            return f"{days:.0f}d {hours:.0f}h"

    def reset_stats(self, connection_name: str):
        """
        Reset statistics for a connection.

        Args:
            connection_name: Name of the connection
        """
        with self._lock:
            if connection_name in self._stats:
                stats = self._stats[connection_name]
                stats.bytes_sent = 0
                stats.bytes_recv = 0
                stats.packets_sent = 0
                stats.packets_recv = 0
                stats.current_send_rate = 0.0
                stats.current_recv_rate = 0.0
                stats.peak_send_rate = 0.0
                stats.peak_recv_rate = 0.0
                stats.errors = 0
                stats.drops = 0
                stats.send_rate_history.clear()
                stats.recv_rate_history.clear()
                self.logger.info(f"Reset stats for connection: {connection_name}")

    def reset_all_stats(self):
        """Reset statistics for all connections."""
        with self._lock:
            for connection_name in list(self._stats.keys()):
                self.reset_stats(connection_name)
            self._global_stats = GlobalStats()
            self.logger.info("Reset stats for all connections")

    def stop_all_monitoring(self):
        """Stop monitoring all connections."""
        self._running = False
        with self._lock:
            for connection_name in list(self._monitoring_threads.keys()):
                self.stop_monitoring(connection_name)
            self._monitoring_threads.clear()
            self._stats.clear()
            self._global_stats = GlobalStats()
        self._running = True
        self.logger.info("Stopped monitoring all connections")

    def get_top_connections(self, limit: int = 5) -> List[Tuple[str, ConnectionStats]]:
        """
        Get the top connections by bandwidth usage.

        Args:
            limit: Maximum number of connections to return

        Returns:
            List[Tuple[str, ConnectionStats]]: Top connections sorted by total bandwidth
        """
        with self._lock:
            sorted_stats = sorted(
                self._stats.items(),
                key=lambda x: x[1].bytes_sent + x[1].bytes_recv,
                reverse=True
            )
            return sorted_stats[:limit]


# Singleton instance
_stats_manager: Optional[StatsManager] = None


def get_stats_manager() -> StatsManager:
    """Get the singleton StatsManager instance."""
    global _stats_manager
    if _stats_manager is None:
        _stats_manager = StatsManager()
    return _stats_manager
