"""
Log Manager Module

Manages logging for VPN connections with log rotation, file storage,
and advanced features like log levels, filtering, and export.
"""

import threading
import os
import time
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from enum import Enum
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFilter:
    """Filter for log messages."""
    
    def __init__(self, keywords: Optional[List[str]] = None, 
                 exclude_keywords: Optional[List[str]] = None,
                 levels: Optional[List[LogLevel]] = None):
        """
        Initialize log filter.
        
        Args:
            keywords: List of keywords to include (AND logic)
            exclude_keywords: List of keywords to exclude (OR logic)
            levels: List of log levels to include
        """
        self.keywords = [kw.lower() for kw in (keywords or [])]
        self.exclude_keywords = [kw.lower() for kw in (exclude_keywords or [])]
        self.levels = levels
    
    def matches(self, message: str, level: LogLevel = LogLevel.INFO) -> bool:
        """
        Check if a log message matches the filter.
        
        Args:
            message: The log message to check
            level: The log level of the message
            
        Returns:
            True if the message matches the filter
        """
        # Check level
        if self.levels and level not in self.levels:
            return False
        
        # Check keywords (AND logic)
        if self.keywords:
            message_lower = message.lower()
            for kw in self.keywords:
                if kw not in message_lower:
                    return False
        
        # Check exclude keywords (OR logic)
        if self.exclude_keywords:
            message_lower = message.lower()
            for kw in self.exclude_keywords:
                if kw in message_lower:
                    return False
        
        return True


class LogManager:
    """Manages VPN connection logs with rotation support."""

    # Maximum log file size in bytes (5 MB)
    MAX_LOG_SIZE = 5 * 1024 * 1024
    # Maximum number of backup log files
    MAX_LOG_BACKUPS = 5
    # Maximum number of log lines to keep in memory
    MAX_LOG_LINES = 1000
    # Log rotation at midnight
    LOG_ROTATION_TIME = "midnight"
    # Log retention in days
    LOG_RETENTION_DAYS = 30

    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize LogManager.

        Args:
            log_dir: Custom log directory (optional)
        """
        self.logger = logging.getLogger("LogManager")

        # Set up log directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / ".local" / "share" / "vpn-manager" / "logs"

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # In-memory logs: {connection_name: [log_lines]}
        self.logs: Dict[str, List[str]] = {}

        # Log threads: {connection_name: thread}
        self.log_threads: Dict[str, threading.Thread] = {}

        # Log file handlers: {connection_name: RotatingFileHandler}
        self.log_handlers: Dict[str, RotatingFileHandler] = {}

    def start_logging(self, connection_name: str, stdout) -> bool:
        """
        Start logging for a VPN connection.

        Args:
            connection_name: Name of the connection
            stdout: Process stdout stream to read from

        Returns:
            True if logging started successfully
        """
        try:
            # Initialize in-memory log
            self.logs[connection_name] = []

            # Create log file path
            log_path = self.log_dir / f"{connection_name}.log"

            # Create rotating file handler
            handler = RotatingFileHandler(
                str(log_path),
                maxBytes=self.MAX_LOG_SIZE,
                backupCount=self.MAX_LOG_BACKUPS,
                encoding="utf-8",
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(message)s")
            )
            self.log_handlers[connection_name] = handler

            # Start log worker thread
            thread = threading.Thread(
                target=self._log_worker,
                args=(connection_name, stdout, handler),
                daemon=True,
            )
            thread.start()
            self.log_threads[connection_name] = thread

            self.logger.info(f"Started logging for connection: {connection_name}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to start logging for {connection_name}: {str(e)}"
            )
            return False

    def stop_logging(self, connection_name: str) -> bool:
        """
        Stop logging for a VPN connection.

        Args:
            connection_name: Name of the connection

        Returns:
            True if logging stopped successfully
        """
        try:
            # Stop the thread
            if connection_name in self.log_threads:
                # Thread will exit when stdout is closed
                del self.log_threads[connection_name]

            # Close the file handler
            if connection_name in self.log_handlers:
                handler = self.log_handlers[connection_name]
                handler.close()
                del self.log_handlers[connection_name]

            self.logger.info(f"Stopped logging for connection: {connection_name}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to stop logging for {connection_name}: {str(e)}"
            )
            return False

    def _log_worker(
        self,
        connection_name: str,
        stdout,
        handler: RotatingFileHandler,
    ):
        """
        Worker thread that reads from stdout and writes to log files.

        Args:
            connection_name: Name of the connection
            stdout: Process stdout stream
            handler: RotatingFileHandler for the connection
        """
        try:
            for line in stdout:
                if line:
                    line = line.strip()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    log_line = f"[{timestamp}] {line}"

                    # Add to in-memory log (with rotation)
                    if connection_name in self.logs:
                        self.logs[connection_name].append(log_line)
                        # Keep only the last MAX_LOG_LINES
                        if len(self.logs[connection_name]) > self.MAX_LOG_LINES:
                            self.logs[connection_name] = self.logs[connection_name][
                                -self.MAX_LOG_LINES :
                            ]

                    # Write to file via handler
                    record = logging.LogRecord(
                        name="VPN",
                        level=logging.INFO,
                        pathname="",
                        lineno=0,
                        msg=line,
                        args=(),
                        exc_info=None,
                    )
                    handler.emit(record)

        except Exception as e:
            self.logger.error(
                f"Log worker error for {connection_name}: {str(e)}"
            )
        finally:
            # Clean up handler
            try:
                handler.close()
            except Exception:
                pass

    def get_logs(self, connection_name: str, max_lines: Optional[int] = None) -> List[str]:
        """
        Get logs for a connection.

        Args:
            connection_name: Name of the connection
            max_lines: Maximum number of lines to return (optional)

        Returns:
            List of log lines
        """
        try:
            logs = self.logs.get(connection_name, [])
            if max_lines and len(logs) > max_lines:
                return logs[-max_lines:]
            return logs.copy()
        except Exception as e:
            self.logger.error(f"Error getting logs for {connection_name}: {str(e)}")
            return []

    def get_log_file_path(self, connection_name: str) -> Optional[str]:
        """
        Get the path to the log file for a connection.

        Args:
            connection_name: Name of the connection

        Returns:
            Path to the log file, or None if not found
        """
        log_path = self.log_dir / f"{connection_name}.log"
        if log_path.exists():
            return str(log_path)
        return None

    def read_log_file(
        self, connection_name: str, max_lines: Optional[int] = None
    ) -> List[str]:
        """
        Read logs directly from the log file.

        Args:
            connection_name: Name of the connection
            max_lines: Maximum number of lines to read (optional)

        Returns:
            List of log lines from the file
        """
        try:
            log_path = self.log_dir / f"{connection_name}.log"
            if not log_path.exists():
                return []

            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if max_lines and len(lines) > max_lines:
                return lines[-max_lines:]
            return lines

        except Exception as e:
            self.logger.error(
                f"Error reading log file for {connection_name}: {str(e)}"
            )
            return []

    def clear_logs(self, connection_name: str) -> bool:
        """
        Clear logs for a connection (both memory and file).

        Args:
            connection_name: Name of the connection

        Returns:
            True if logs cleared successfully
        """
        try:
            # Clear in-memory logs
            if connection_name in self.logs:
                self.logs[connection_name] = []

            # Clear log file
            log_path = self.log_dir / f"{connection_name}.log"
            if log_path.exists():
                log_path.write_text("", encoding="utf-8")

            self.logger.info(f"Cleared logs for connection: {connection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error clearing logs for {connection_name}: {str(e)}")
            return False

    def clear_all_logs(self) -> bool:
        """
        Clear all logs (memory and files).

        Returns:
            True if all logs cleared successfully
        """
        try:
            # Clear in-memory logs
            self.logs.clear()

            # Clear all log files
            for log_file in self.log_dir.glob("*.log"):
                log_file.write_text("", encoding="utf-8")

            self.logger.info("Cleared all logs")
            return True

        except Exception as e:
            self.logger.error(f"Error clearing all logs: {str(e)}")
            return False

    def cleanup_old_logs(self, max_age_days: int = 30) -> int:
        """
        Clean up log files older than a certain age.

        Args:
            max_age_days: Maximum age in days for log files

        Returns:
            Number of files deleted
        """
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            deleted_count = 0

            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1

            self.logger.info(f"Cleaned up {deleted_count} old log files")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Error cleaning up old logs: {str(e)}")
            return 0

    def get_log_directory(self) -> str:
        """
        Get the log directory path.

        Returns:
            Path to the log directory
        """
        return str(self.log_dir)

    def set_verbosity(self, level: str = "INFO") -> bool:
        """
        Set the logging verbosity level.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            
        Returns:
            True if level was set successfully
        """
        try:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if level.upper() not in valid_levels:
                self.logger.warning(f"Invalid log level: {level}. Using INFO.")
                level = "INFO"
            
            self.verbosity_level = level.upper()
            self.logger.info(f"Log verbosity set to: {self.verbosity_level}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting verbosity: {str(e)}")
            return False

    def get_verbosity(self) -> str:
        """
        Get the current logging verbosity level.
        
        Returns:
            Current verbosity level
        """
        return getattr(self, "verbosity_level", "INFO")

    def filter_logs(self, connection_name: str, 
                   log_filter: LogFilter) -> List[str]:
        """
        Filter logs for a connection based on criteria.
        
        Args:
            connection_name: Name of the connection
            log_filter: LogFilter instance with filtering criteria
            
        Returns:
            List of filtered log lines
        """
        try:
            logs = self.get_logs(connection_name)
            filtered = []
            
            for line in logs:
                # Extract level from log line if present
                level = LogLevel.INFO
                if line.startswith("[DEBUG]"):
                    level = LogLevel.DEBUG
                elif line.startswith("[INFO]"):
                    level = LogLevel.INFO
                elif line.startswith("[WARNING]"):
                    level = LogLevel.WARNING
                elif line.startswith("[ERROR]"):
                    level = LogLevel.ERROR
                elif line.startswith("[CRITICAL]"):
                    level = LogLevel.CRITICAL
                
                # Extract message (remove timestamp and level)
                message = line
                if " - " in line:
                    message = line.split(" - ", 1)[1]
                
                if log_filter.matches(message, level):
                    filtered.append(line)
            
            return filtered
        except Exception as e:
            self.logger.error(f"Error filtering logs for {connection_name}: {str(e)}")
            return []

    def search_logs(self, connection_name: str, 
                    search_term: str, 
                    case_sensitive: bool = False) -> List[str]:
        """
        Search logs for a specific term.
        
        Args:
            connection_name: Name of the connection
            search_term: Term to search for
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            List of log lines containing the search term
        """
        try:
            logs = self.get_logs(connection_name)
            results = []
            
            if not case_sensitive:
                search_term = search_term.lower()
            
            for line in logs:
                if not case_sensitive:
                    line_lower = line.lower()
                    if search_term in line_lower:
                        results.append(line)
                else:
                    if search_term in line:
                        results.append(line)
            
            return results
        except Exception as e:
            self.logger.error(f"Error searching logs for {connection_name}: {str(e)}")
            return []

    def export_logs_to_file(self, connection_name: str, 
                           output_path: str, 
                           format: str = "txt") -> bool:
        """
        Export logs to a file in the specified format.
        
        Args:
            connection_name: Name of the connection
            output_path: Path to the output file
            format: Export format (txt, csv, json)
            
        Returns:
            True if export was successful
        """
        try:
            logs = self.get_logs(connection_name)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "txt":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(logs))
            
            elif format == "csv":
                with open(output_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Level", "Message"])
                    for line in logs:
                        # Parse log line
                        parts = line.split(" - ", 2)
                        if len(parts) >= 3:
                            timestamp = parts[0]
                            level = parts[1]
                            message = parts[2]
                        else:
                            timestamp = ""
                            level = "INFO"
                            message = line
                        writer.writerow([timestamp, level, message])
            
            elif format == "json":
                export_data = []
                for line in logs:
                    parts = line.split(" - ", 2)
                    if len(parts) >= 3:
                        timestamp = parts[0]
                        level = parts[1]
                        message = parts[2]
                    else:
                        timestamp = ""
                        level = "INFO"
                        message = line
                    export_data.append({
                        "timestamp": timestamp,
                        "level": level,
                        "message": message
                    })
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            else:
                self.logger.warning(f"Unknown export format: {format}. Using txt.")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(logs))
            
            self.logger.info(f"Exported logs for {connection_name} to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting logs for {connection_name}: {str(e)}")
            return False

    def get_connection_stats(self, connection_name: str) -> Dict[str, any]:
        """
        Get statistics for a connection's logs.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Dictionary with log statistics
        """
        try:
            logs = self.get_logs(connection_name)
            
            stats = {
                "total_lines": len(logs),
                "levels": {
                    "DEBUG": 0,
                    "INFO": 0,
                    "WARNING": 0,
                    "ERROR": 0,
                    "CRITICAL": 0,
                },
                "first_timestamp": None,
                "last_timestamp": None,
            }
            
            if not logs:
                return stats
            
            # Count levels and extract timestamps
            for line in logs:
                if line.startswith("[DEBUG]"):
                    stats["levels"]["DEBUG"] += 1
                elif line.startswith("[INFO]"):
                    stats["levels"]["INFO"] += 1
                elif line.startswith("[WARNING]"):
                    stats["levels"]["WARNING"] += 1
                elif line.startswith("[ERROR]"):
                    stats["levels"]["ERROR"] += 1
                elif line.startswith("[CRITICAL]"):
                    stats["levels"]["CRITICAL"] += 1
                else:
                    stats["levels"]["INFO"] += 1
            
            # Extract timestamps
            if logs:
                stats["first_timestamp"] = logs[0].split(" - ")[0] if " - " in logs[0] else None
                stats["last_timestamp"] = logs[-1].split(" - ")[0] if " - " in logs[-1] else None
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting stats for {connection_name}: {str(e)}")
            return {
                "total_lines": 0,
                "levels": {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0},
                "first_timestamp": None,
                "last_timestamp": None,
            }

    def get_all_connections_stats(self) -> Dict[str, Dict[str, any]]:
        """
        Get statistics for all connections.
        
        Returns:
            Dictionary with connection names as keys and their stats as values
        """
        stats = {}
        for conn_name in self.logs.keys():
            stats[conn_name] = self.get_connection_stats(conn_name)
        return stats

    def cleanup_all_logs(self) -> int:
        """
        Clean up all old log files.
        
        Returns:
            Number of files deleted
        """
        return self.cleanup_old_logs(self.LOG_RETENTION_DAYS)

    def set_log_rotation(self, max_size: int = None, 
                        max_backups: int = None,
                        rotation_time: str = None) -> bool:
        """
        Configure log rotation settings.
        
        Args:
            max_size: Maximum log file size in bytes
            max_backups: Maximum number of backup files
            rotation_time: Time for timed rotation (midnight, hourly)
            
        Returns:
            True if settings were updated successfully
        """
        try:
            if max_size is not None:
                self.MAX_LOG_SIZE = max_size
            if max_backups is not None:
                self.MAX_LOG_BACKUPS = max_backups
            if rotation_time is not None:
                self.LOG_ROTATION_TIME = rotation_time
            
            self.logger.info(
                f"Log rotation settings updated: "
                f"max_size={self.MAX_LOG_SIZE}, "
                f"max_backups={self.MAX_LOG_BACKUPS}, "
                f"rotation_time={self.LOG_ROTATION_TIME}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error setting log rotation: {str(e)}")
            return False
