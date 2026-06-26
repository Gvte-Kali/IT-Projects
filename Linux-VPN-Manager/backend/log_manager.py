"""
Log Manager Module

Manages logging for VPN connections with log rotation and file storage.
"""

import threading
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging
from logging.handlers import RotatingFileHandler


class LogManager:
    """Manages VPN connection logs with rotation support."""

    # Maximum log file size in bytes (5 MB)
    MAX_LOG_SIZE = 5 * 1024 * 1024
    # Maximum number of backup log files
    MAX_LOG_BACKUPS = 5
    # Maximum number of log lines to keep in memory
    MAX_LOG_LINES = 1000

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
