"""
History Manager Module

Manages connection history, statistics, and session tracking for VPN connections.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging


class ConnectionStatus(Enum):
    """Status of a VPN connection."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ConnectionSession:
    """Represents a single VPN connection session."""
    connection_name: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[float] = None  # Duration in seconds
    status: ConnectionStatus = ConnectionStatus.CONNECTING
    bytes_sent: int = 0
    bytes_received: int = 0
    error_message: Optional[str] = None
    exit_code: Optional[int] = None
    server_address: Optional[str] = None
    protocol: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionSession":
        """Create session from dictionary."""
        return cls(**data)


@dataclass
class ConnectionHistory:
    """Represents the history for a specific VPN connection."""
    connection_name: str
    sessions: List[ConnectionSession] = field(default_factory=list)
    total_connections: int = 0
    total_duration: float = 0.0  # Total duration in seconds
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    last_connection_time: Optional[str] = None
    success_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert history to dictionary."""
        return {
            "connection_name": self.connection_name,
            "sessions": [s.to_dict() for s in self.sessions],
            "total_connections": self.total_connections,
            "total_duration": self.total_duration,
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
            "last_connection_time": self.last_connection_time,
            "success_rate": self.success_rate,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionHistory":
        """Create history from dictionary."""
        history = cls(
            connection_name=data["connection_name"],
            total_connections=data.get("total_connections", 0),
            total_duration=data.get("total_duration", 0.0),
            total_bytes_sent=data.get("total_bytes_sent", 0),
            total_bytes_received=data.get("total_bytes_received", 0),
            last_connection_time=data.get("last_connection_time"),
            success_rate=data.get("success_rate", 0.0),
        )
        history.sessions = [
            ConnectionSession.from_dict(s) for s in data.get("sessions", [])
        ]
        return history


class HistoryManager:
    """
    Manages VPN connection history and statistics.
    """

    def __init__(self, history_dir: Optional[str] = None):
        """
        Initialize HistoryManager.
        
        Args:
            history_dir: Custom directory for history files (optional)
        """
        self.logger = logging.getLogger("HistoryManager")
        
        # Set up history directory
        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            self.history_dir = Path.home() / ".local" / "share" / "vpn-manager" / "history"
        
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory history: {connection_name: ConnectionHistory}
        self.history: Dict[str, ConnectionHistory] = {}
        
        # Active sessions: {connection_name: ConnectionSession}
        self.active_sessions: Dict[str, ConnectionSession] = {}
        
        # Load existing history from disk
        self._load_history()

    def _load_history(self) -> None:
        """Load connection history from disk."""
        try:
            history_file = self.history_dir / "connections.json"
            if history_file.exists():
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for conn_name, conn_data in data.items():
                        self.history[conn_name] = ConnectionHistory.from_dict(conn_data)
                self.logger.info(f"Loaded history for {len(self.history)} connections")
        except Exception as e:
            self.logger.error(f"Error loading history: {str(e)}")

    def _save_history(self) -> bool:
        """
        Save connection history to disk.
        
        Returns:
            True if save was successful
        """
        try:
            history_file = self.history_dir / "connections.json"
            data = {}
            for conn_name, conn_history in self.history.items():
                data[conn_name] = conn_history.to_dict()
            
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Saved connection history")
            return True
        except Exception as e:
            self.logger.error(f"Error saving history: {str(e)}")
            return False

    def start_session(self, connection_name: str, 
                     server_address: Optional[str] = None,
                     protocol: Optional[str] = None) -> bool:
        """
        Start a new connection session.
        
        Args:
            connection_name: Name of the connection
            server_address: Server address (optional)
            protocol: VPN protocol (optional)
            
        Returns:
            True if session started successfully
        """
        try:
            # End any existing active session for this connection
            if connection_name in self.active_sessions:
                self.end_session(connection_name, ConnectionStatus.DISCONNECTED)
            
            # Create new session
            session = ConnectionSession(
                connection_name=connection_name,
                start_time=datetime.now().isoformat(),
                status=ConnectionStatus.CONNECTING,
                server_address=server_address,
                protocol=protocol,
            )
            
            self.active_sessions[connection_name] = session
            
            # Initialize history if not exists
            if connection_name not in self.history:
                self.history[connection_name] = ConnectionHistory(
                    connection_name=connection_name
                )
            
            self.logger.info(f"Started session for {connection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error starting session for {connection_name}: {str(e)}")
            return False

    def update_session_status(self, connection_name: str, 
                             status: ConnectionStatus,
                             error_message: Optional[str] = None,
                             exit_code: Optional[int] = None) -> bool:
        """
        Update the status of an active session.
        
        Args:
            connection_name: Name of the connection
            status: New status
            error_message: Error message (optional)
            exit_code: Exit code (optional)
            
        Returns:
            True if update was successful
        """
        try:
            if connection_name not in self.active_sessions:
                self.logger.warning(f"No active session for {connection_name}")
                return False
            
            session = self.active_sessions[connection_name]
            session.status = status
            session.error_message = error_message
            session.exit_code = exit_code
            
            self.logger.info(f"Updated session status for {connection_name}: {status.value}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating session status: {str(e)}")
            return False

    def end_session(self, connection_name: str, 
                   status: ConnectionStatus = ConnectionStatus.DISCONNECTED,
                   bytes_sent: int = 0,
                   bytes_received: int = 0,
                   error_message: Optional[str] = None,
                   exit_code: Optional[int] = None) -> bool:
        """
        End an active connection session.
        
        Args:
            connection_name: Name of the connection
            status: Final status of the session
            bytes_sent: Bytes sent during the session
            bytes_received: Bytes received during the session
            error_message: Error message (optional)
            exit_code: Exit code (optional)
            
        Returns:
            True if session ended successfully
        """
        try:
            if connection_name not in self.active_sessions:
                self.logger.warning(f"No active session for {connection_name}")
                return False
            
            session = self.active_sessions[connection_name]
            
            # Set end time and calculate duration
            end_time = datetime.now().isoformat()
            start_time = datetime.fromisoformat(session.start_time)
            end_time_dt = datetime.fromisoformat(end_time)
            session.end_time = end_time
            session.duration = (end_time_dt - start_time).total_seconds()
            session.status = status
            session.bytes_sent = bytes_sent
            session.bytes_received = bytes_received
            session.error_message = error_message
            session.exit_code = exit_code
            
            # Add session to history
            history = self.history[connection_name]
            history.sessions.append(session)
            
            # Update history statistics
            history.total_connections += 1
            history.total_duration += session.duration
            history.total_bytes_sent += session.bytes_sent
            history.total_bytes_received += session.bytes_received
            history.last_connection_time = end_time
            
            # Calculate success rate
            successful_sessions = sum(
                1 for s in history.sessions 
                if s.status == ConnectionStatus.DISCONNECTED
            )
            history.success_rate = (
                (successful_sessions / len(history.sessions)) * 100 
                if history.sessions else 0.0
            )
            
            # Remove from active sessions
            del self.active_sessions[connection_name]
            
            # Save to disk
            self._save_history()
            
            self.logger.info(f"Ended session for {connection_name}: {status.value}")
            return True
        except Exception as e:
            self.logger.error(f"Error ending session for {connection_name}: {str(e)}")
            return False

    def get_session(self, connection_name: str) -> Optional[ConnectionSession]:
        """
        Get the active session for a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Active session or None if not found
        """
        return self.active_sessions.get(connection_name)

    def get_history(self, connection_name: str) -> Optional[ConnectionHistory]:
        """
        Get the history for a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Connection history or None if not found
        """
        return self.history.get(connection_name)

    def get_all_history(self) -> Dict[str, ConnectionHistory]:
        """
        Get history for all connections.
        
        Returns:
            Dictionary with all connection histories
        """
        return self.history.copy()

    def get_recent_sessions(self, connection_name: str, 
                           limit: int = 10) -> List[ConnectionSession]:
        """
        Get recent sessions for a connection.
        
        Args:
            connection_name: Name of the connection
            limit: Maximum number of sessions to return
            
        Returns:
            List of recent sessions (most recent first)
        """
        history = self.get_history(connection_name)
        if not history:
            return []
        
        # Sort by start time (most recent first) and limit
        sorted_sessions = sorted(
            history.sessions,
            key=lambda s: s.start_time,
            reverse=True
        )
        return sorted_sessions[:limit]

    def get_session_statistics(self, connection_name: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Dictionary with connection statistics
        """
        history = self.get_history(connection_name)
        if not history:
            return {
                "connection_name": connection_name,
                "total_sessions": 0,
                "successful_sessions": 0,
                "failed_sessions": 0,
                "total_duration": 0,
                "avg_duration": 0,
                "total_bytes_sent": 0,
                "total_bytes_received": 0,
                "success_rate": 0.0,
                "last_connection": None,
            }
        
        # Count session statuses
        successful = sum(
            1 for s in history.sessions 
            if s.status == ConnectionStatus.DISCONNECTED
        )
        failed = sum(
            1 for s in history.sessions 
            if s.status in [ConnectionStatus.FAILED, ConnectionStatus.TIMEOUT]
        )
        
        # Calculate average duration
        avg_duration = (
            (history.total_duration / len(history.sessions))
            if history.sessions else 0
        )
        
        return {
            "connection_name": connection_name,
            "total_sessions": len(history.sessions),
            "successful_sessions": successful,
            "failed_sessions": failed,
            "total_duration": history.total_duration,
            "avg_duration": avg_duration,
            "total_bytes_sent": history.total_bytes_sent,
            "total_bytes_received": history.total_bytes_received,
            "success_rate": history.success_rate,
            "last_connection": history.last_connection_time,
        }

    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all connections.
        
        Returns:
            Dictionary with connection names as keys and their statistics as values
        """
        stats = {}
        for conn_name in self.history.keys():
            stats[conn_name] = self.get_session_statistics(conn_name)
        return stats

    def get_global_statistics(self) -> Dict[str, Any]:
        """
        Get global statistics across all connections.
        
        Returns:
            Dictionary with global statistics
        """
        total_sessions = 0
        successful_sessions = 0
        failed_sessions = 0
        total_duration = 0.0
        total_bytes_sent = 0
        total_bytes_received = 0
        
        for history in self.history.values():
            total_sessions += len(history.sessions)
            successful_sessions += sum(
                1 for s in history.sessions 
                if s.status == ConnectionStatus.DISCONNECTED
            )
            failed_sessions += sum(
                1 for s in history.sessions 
                if s.status in [ConnectionStatus.FAILED, ConnectionStatus.TIMEOUT]
            )
            total_duration += history.total_duration
            total_bytes_sent += history.total_bytes_sent
            total_bytes_received += history.total_bytes_received
        
        return {
            "total_connections": len(self.history),
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "failed_sessions": failed_sessions,
            "total_duration": total_duration,
            "avg_duration": (
                (total_duration / total_sessions) if total_sessions > 0 else 0
            ),
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_received,
            "overall_success_rate": (
                (successful_sessions / total_sessions * 100) if total_sessions > 0 else 0.0
            ),
        }

    def clear_history(self, connection_name: str) -> bool:
        """
        Clear history for a specific connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            True if history was cleared successfully
        """
        try:
            if connection_name in self.history:
                del self.history[connection_name]
                self._save_history()
                self.logger.info(f"Cleared history for {connection_name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error clearing history for {connection_name}: {str(e)}")
            return False

    def clear_all_history(self) -> bool:
        """
        Clear history for all connections.
        
        Returns:
            True if all history was cleared successfully
        """
        try:
            self.history.clear()
            self._save_history()
            self.logger.info("Cleared all connection history")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing all history: {str(e)}")
            return False

    def export_history(self, output_path: str, 
                      format: str = "json") -> bool:
        """
        Export history to a file.
        
        Args:
            output_path: Path to the output file
            format: Export format (json, csv)
            
        Returns:
            True if export was successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "json":
                data = {}
                for conn_name, conn_history in self.history.items():
                    data[conn_name] = conn_history.to_dict()
                
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            elif format == "csv":
                import csv
                with open(output_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Connection", "Start Time", "End Time", "Duration (s)",
                        "Status", "Bytes Sent", "Bytes Received", "Error Message"
                    ])
                    
                    for conn_name, conn_history in self.history.items():
                        for session in conn_history.sessions:
                            writer.writerow([
                                conn_name,
                                session.start_time,
                                session.end_time or "",
                                session.duration or 0,
                                session.status.value,
                                session.bytes_sent,
                                session.bytes_received,
                                session.error_message or ""
                            ])
            
            else:
                self.logger.warning(f"Unknown export format: {format}. Using json.")
                data = {}
                for conn_name, conn_history in self.history.items():
                    data[conn_name] = conn_history.to_dict()
                
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported history to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting history: {str(e)}")
            return False

    def get_active_sessions(self) -> Dict[str, ConnectionSession]:
        """
        Get all currently active sessions.
        
        Returns:
            Dictionary with active sessions
        """
        return self.active_sessions.copy()

    def is_connection_active(self, connection_name: str) -> bool:
        """
        Check if a connection is currently active.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            True if the connection is active
        """
        return connection_name in self.active_sessions

    def get_longest_session(self, connection_name: str) -> Optional[ConnectionSession]:
        """
        Get the longest session for a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Longest session or None
        """
        history = self.get_history(connection_name)
        if not history or not history.sessions:
            return None
        
        return max(history.sessions, key=lambda s: s.duration or 0)

    def get_last_successful_session(self, connection_name: str) -> Optional[ConnectionSession]:
        """
        Get the last successful session for a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Last successful session or None
        """
        history = self.get_history(connection_name)
        if not history or not history.sessions:
            return None
        
        successful_sessions = [
            s for s in history.sessions 
            if s.status == ConnectionStatus.DISCONNECTED
        ]
        
        if not successful_sessions:
            return None
        
        return max(successful_sessions, key=lambda s: s.start_time)
