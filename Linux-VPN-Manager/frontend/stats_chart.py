"""
Stats Chart Module

Provides chart visualization for VPN connection statistics using matplotlib.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging

try:
    import matplotlib
    matplotlib.use("Qt5Agg")  # Use Qt5 backend for compatibility
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class StatsChart:
    """
    Creates and manages statistics charts for VPN connections.
    """

    def __init__(self):
        """Initialize the stats chart manager."""
        self.logger = logging.getLogger("StatsChart")
        self._available = MATPLOTLIB_AVAILABLE
        
        if not self._available:
            self.logger.warning("matplotlib not available. Chart features disabled.")

    @property
    def is_available(self) -> bool:
        """Check if matplotlib is available."""
        return self._available

    def create_bandwidth_chart(self, 
                               data: Dict[str, List[Dict[str, Any]]],
                               output_path: Optional[str] = None,
                               show: bool = False) -> Optional[Figure]:
        """
        Create a bandwidth usage chart (send/receive over time).
        
        Args:
            data: Dictionary with connection names as keys and list of data points as values.
                  Each data point should have: timestamp, bytes_sent, bytes_received
            output_path: Path to save the chart (optional)
            show: Whether to display the chart
            
        Returns:
            matplotlib Figure object or None if matplotlib is not available
        """
        if not self._available:
            self.logger.warning("Cannot create chart: matplotlib not available")
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Convert bytes to MB for better readability
            for conn_name, data_points in data.items():
                if not data_points:
                    continue
                
                timestamps = []
                sent_mb = []
                received_mb = []
                
                for point in data_points:
                    try:
                        ts = datetime.fromisoformat(point["timestamp"])
                        timestamps.append(ts)
                        sent_mb.append(point.get("bytes_sent", 0) / (1024 * 1024))
                        received_mb.append(point.get("bytes_received", 0) / (1024 * 1024))
                    except Exception:
                        continue
                
                if not timestamps:
                    continue
                
                # Plot sent data
                ax.plot(timestamps, sent_mb, 
                       label=f"{conn_name} - Sent", 
                       color=self._get_color(conn_name, "sent"),
                       linewidth=1.5)
                
                # Plot received data
                ax.plot(timestamps, received_mb, 
                       label=f"{conn_name} - Received",
                       color=self._get_color(conn_name, "received"),
                       linewidth=1.5,
                       linestyle="--")
            
            if not ax.has_data():
                ax.text(0.5, 0.5, "No data available",
                       ha="center", va="center", transform=ax.transAxes)
            else:
                ax.set_xlabel("Time")
                ax.set_ylabel("Data (MB)")
                ax.set_title("VPN Bandwidth Usage")
                ax.legend(loc="upper left")
                ax.grid(True, alpha=0.3)
                
                # Rotate x-axis labels for better readability
                plt.xticks(rotation=45)
                plt.tight_layout()
            
            # Save or show
            if output_path:
                fig.savefig(output_path, dpi=300, bbox_inches="tight")
            
            if show:
                plt.show()
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating bandwidth chart: {str(e)}")
            return None

    def create_duration_chart(self,
                              data: Dict[str, List[float]],
                              output_path: Optional[str] = None,
                              show: bool = False) -> Optional[Figure]:
        """
        Create a chart showing connection durations.
        
        Args:
            data: Dictionary with connection names as keys and list of durations (seconds) as values
            output_path: Path to save the chart (optional)
            show: Whether to display the chart
            
        Returns:
            matplotlib Figure object or None
        """
        if not self._available:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            for conn_name, durations in data.items():
                if not durations:
                    continue
                
                # Convert seconds to minutes for better readability
                durations_min = [d / 60 for d in durations]
                
                ax.plot(range(len(durations_min)), durations_min,
                       label=conn_name,
                       color=self._get_color(conn_name, "duration"),
                       marker="o",
                       linewidth=1.5)
            
            if not ax.has_data():
                ax.text(0.5, 0.5, "No data available",
                       ha="center", va="center", transform=ax.transAxes)
            else:
                ax.set_xlabel("Session")
                ax.set_ylabel("Duration (minutes)")
                ax.set_title("VPN Connection Durations")
                ax.legend(loc="upper right")
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
            
            if output_path:
                fig.savefig(output_path, dpi=300, bbox_inches="tight")
            
            if show:
                plt.show()
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating duration chart: {str(e)}")
            return None

    def create_success_rate_chart(self,
                                  data: Dict[str, Dict[str, Any]],
                                  output_path: Optional[str] = None,
                                  show: bool = False) -> Optional[Figure]:
        """
        Create a chart showing success rates for connections.
        
        Args:
            data: Dictionary with connection names as keys and their statistics as values.
                  Should include: total_sessions, successful_sessions
            output_path: Path to save the chart (optional)
            show: Whether to display the chart
            
        Returns:
            matplotlib Figure object or None
        """
        if not self._available:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            connections = []
            success_rates = []
            
            for conn_name, stats in data.items():
                total = stats.get("total_sessions", 0)
                successful = stats.get("successful_sessions", 0)
                
                if total > 0:
                    rate = (successful / total) * 100
                else:
                    rate = 0
                
                connections.append(conn_name)
                success_rates.append(rate)
            
            if not connections:
                ax.text(0.5, 0.5, "No data available",
                       ha="center", va="center", transform=ax.transAxes)
            else:
                bars = ax.bar(connections, success_rates, 
                            color=[self._get_color(c, "success") for c in connections])
                
                # Add value labels on top of bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width() / 2., height,
                           f"{height:.1f}%",
                           ha="center", va="bottom")
                
                ax.set_xlabel("Connection")
                ax.set_ylabel("Success Rate (%)")
                ax.set_title("VPN Connection Success Rates")
                ax.set_ylim(0, 100)
                ax.grid(True, alpha=0.3, axis="y")
                plt.tight_layout()
            
            if output_path:
                fig.savefig(output_path, dpi=300, bbox_inches="tight")
            
            if show:
                plt.show()
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating success rate chart: {str(e)}")
            return None

    def create_combined_stats_chart(self,
                                    history_data: Dict[str, Any],
                                    output_path: Optional[str] = None,
                                    show: bool = False) -> Optional[Figure]:
        """
        Create a combined chart with multiple statistics.
        
        Args:
            history_data: Dictionary with history data including sessions
            output_path: Path to save the chart (optional)
            show: Whether to display the chart
            
        Returns:
            matplotlib Figure object or None
        """
        if not self._available:
            return None
        
        try:
            # Create a 2x2 grid of subplots
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # Subplot 1: Total sessions per connection
            ax1 = axes[0, 0]
            connections = list(history_data.keys())
            total_sessions = [len(history_data[c]["sessions"]) for c in connections]
            
            if connections:
                ax1.bar(connections, total_sessions, 
                       color=[self._get_color(c, "total") for c in connections])
                ax1.set_xlabel("Connection")
                ax1.set_ylabel("Total Sessions")
                ax1.set_title("Total Sessions per Connection")
                ax1.grid(True, alpha=0.3, axis="y")
            else:
                ax1.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax1.transAxes)
                ax1.set_title("Total Sessions per Connection")
            
            # Subplot 2: Total duration per connection (hours)
            ax2 = axes[0, 1]
            total_durations = [history_data[c]["total_duration"] / 3600 for c in connections]
            
            if connections:
                ax2.bar(connections, total_durations,
                       color=[self._get_color(c, "duration") for c in connections])
                ax2.set_xlabel("Connection")
                ax2.set_ylabel("Total Duration (hours)")
                ax2.set_title("Total Duration per Connection")
                ax2.grid(True, alpha=0.3, axis="y")
            else:
                ax2.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax2.transAxes)
                ax2.set_title("Total Duration per Connection")
            
            # Subplot 3: Success rate per connection
            ax3 = axes[1, 0]
            success_rates = [history_data[c]["success_rate"] for c in connections]
            
            if connections:
                bars = ax3.bar(connections, success_rates,
                             color=[self._get_color(c, "success") for c in connections])
                for bar in bars:
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width() / 2., height,
                            f"{height:.1f}%", ha="center", va="bottom")
                ax3.set_xlabel("Connection")
                ax3.set_ylabel("Success Rate (%)")
                ax3.set_title("Success Rate per Connection")
                ax3.set_ylim(0, 100)
                ax3.grid(True, alpha=0.3, axis="y")
            else:
                ax3.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax3.transAxes)
                ax3.set_title("Success Rate per Connection")
            
            # Subplot 4: Data transfer per connection (MB)
            ax4 = axes[1, 1]
            total_sent = [history_data[c]["total_bytes_sent"] / (1024 * 1024) for c in connections]
            total_received = [history_data[c]["total_bytes_received"] / (1024 * 1024) for c in connections]
            
            if connections:
                x = range(len(connections))
                width = 0.35
                ax4.bar([i - width/2 for i in x], total_sent, width,
                       label="Sent", color="#4CAF50")
                ax4.bar([i + width/2 for i in x], total_received, width,
                       label="Received", color="#2196F3")
                ax4.set_xlabel("Connection")
                ax4.set_ylabel("Data (MB)")
                ax4.set_title("Data Transfer per Connection")
                ax4.legend()
                ax4.grid(True, alpha=0.3, axis="y")
                ax4.set_xticks(x)
                ax4.set_xticklabels(connections, rotation=45, ha="right")
            else:
                ax4.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax4.transAxes)
                ax4.set_title("Data Transfer per Connection")
            
            plt.tight_layout()
            
            if output_path:
                fig.savefig(output_path, dpi=300, bbox_inches="tight")
            
            if show:
                plt.show()
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating combined stats chart: {str(e)}")
            return None

    def _get_color(self, identifier: str, color_type: str) -> str:
        """
        Get a consistent color for a connection based on its name and color type.
        
        Args:
            identifier: Connection name or other identifier
            color_type: Type of color (sent, received, duration, success, total)
            
        Returns:
            Color string in hex format
        """
        # Predefined color schemes for different types
        color_schemes = {
            "sent": ["#FF6B6B", "#FF8E8E", "#FFB3B3", "#FFD8D8"],
            "received": ["#4ECDC4", "#81D4D8", "#B4DDDF", "#E8F4F8"],
            "duration": ["#95E1D3", "#A8E6CF", "#C7F0D8", "#E6F7FF"],
            "success": ["#A8E6CF", "#88D8C0", "#68C5A7", "#48B092"],
            "total": ["#F38181", "#FA9884", "#FCAF98", "#FEC8B8"],
        }
        
        # Get color scheme for the type
        colors = color_schemes.get(color_type, ["#999999", "#AAAAAA", "#BBBBBB"])
        
        # Use hash of identifier to select a color from the scheme
        hash_val = hash(identifier) % len(colors)
        return colors[hash_val]

    def create_chart_widget(self, figure: Figure) -> Optional[Any]:
        """
        Create a Qt widget from a matplotlib figure for embedding in PyQt6 UI.
        
        Args:
            figure: matplotlib Figure object
            
        Returns:
            FigureCanvas widget or None if matplotlib is not available
        """
        if not self._available:
            return None
        
        try:
            canvas = FigureCanvas(figure)
            canvas.setSizePolicy(
                getattr(canvas, "SizePolicy Expanding", None),
                getattr(canvas, "SizePolicy Expanding", None)
            )
            return canvas
        except Exception as e:
            self.logger.error(f"Error creating chart widget: {str(e)}")
            return None

    def close_all_figures(self) -> None:
        """Close all open matplotlib figures."""
        if self._available:
            try:
                plt.close("all")
            except Exception as e:
                self.logger.error(f"Error closing figures: {str(e)}")

    def get_chart_data_from_history(self, history_manager) -> Dict[str, Any]:
        """
        Extract chart data from a HistoryManager instance.
        
        Args:
            history_manager: HistoryManager instance
            
        Returns:
            Dictionary with formatted data for charts
        """
        try:
            all_history = history_manager.get_all_history()
            
            # Bandwidth data
            bandwidth_data = {}
            for conn_name, history in all_history.items():
                data_points = []
                for session in history.sessions:
                    data_points.append({
                        "timestamp": session.start_time,
                        "bytes_sent": session.bytes_sent,
                        "bytes_received": session.bytes_received,
                    })
                bandwidth_data[conn_name] = data_points
            
            # Duration data
            duration_data = {}
            for conn_name, history in all_history.items():
                durations = [s.duration for s in history.sessions if s.duration]
                duration_data[conn_name] = durations
            
            # Statistics data
            stats_data = {}
            for conn_name, history in all_history.items():
                stats_data[conn_name] = {
                    "total_sessions": len(history.sessions),
                    "successful_sessions": sum(
                        1 for s in history.sessions 
                        if s.status.value == "disconnected"
                    ),
                    "total_duration": history.total_duration,
                    "total_bytes_sent": history.total_bytes_sent,
                    "total_bytes_received": history.total_bytes_received,
                    "success_rate": history.success_rate,
                }
            
            return {
                "bandwidth": bandwidth_data,
                "duration": duration_data,
                "statistics": stats_data,
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting chart data: {str(e)}")
            return {"bandwidth": {}, "duration": {}, "statistics": {}}
