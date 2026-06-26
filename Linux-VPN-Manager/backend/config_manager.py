"""
Configuration Manager Module

Manages VPN connection configurations stored in JSON format.
Handles adding, removing, listing, and retrieving VPN configurations.
"""

import json
import os
import re
from pathlib import Path
from typing import Tuple, Dict, List, Optional
import logging


class ConfigManager:
    """Manages VPN connection configurations."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            config_dir: Custom configuration directory (optional)
        """
        self.logger = logging.getLogger("ConfigManager")

        # Set up configuration directory
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".config" / "vpn-manager"

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "connections.json"

        # Load connections
        self.connections: Dict[str, Dict] = self._load_connections()

    def _load_connections(self) -> Dict[str, Dict]:
        """
        Load connections from the configuration file.

        Returns:
            Dictionary of connections
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    else:
                        self.logger.warning("Configuration file has invalid format")
                        return {}
            else:
                self.logger.info("No existing configuration file found")
                return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse configuration file: {str(e)}")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading connections: {str(e)}")
            return {}

    def _save_connections(self) -> bool:
        """
        Save connections to the configuration file.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup of existing file
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix(".json.bak")
                self.config_file.rename(backup_file)

            # Write new file
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.connections, f, indent=2, ensure_ascii=False)

            # Remove backup on success
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix(".json.bak")
                if backup_file.exists():
                    backup_file.unlink()

            self.logger.info("Connections saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save connections: {str(e)}")
            # Restore backup if it exists
            backup_file = self.config_file.with_suffix(".json.bak")
            if backup_file.exists():
                backup_file.rename(self.config_file)
            return False

    def _validate_connection_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate a connection name.

        Args:
            name: Connection name to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not name or not name.strip():
            return False, "Connection name cannot be empty"

        name = name.strip()

        # Check for invalid characters
        if not re.match(r"^[a-zA-Z0-9_\-\s]+$", name):
            return (
                False,
                "Connection name can only contain letters, numbers, spaces, underscores, and hyphens",
            )

        # Check length
        if len(name) > 100:
            return False, "Connection name is too long (max 100 characters)"

        return True, ""

    def _validate_config_path(self, config_path: str) -> Tuple[bool, str]:
        """
        Validate a configuration file path.

        Args:
            config_path: Path to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not config_path or not config_path.strip():
            return False, "Config path cannot be empty"

        config_path = os.path.abspath(os.path.expanduser(config_path.strip()))

        if not os.path.exists(config_path):
            return False, f"Config file does not exist: {config_path}"

        if not os.path.isfile(config_path):
            return False, f"Config path is not a file: {config_path}"

        # Check file extension
        valid_extensions = [".ovpn", ".conf"]
        if not any(config_path.endswith(ext) for ext in valid_extensions):
            return (
                False,
                f"Invalid config file extension. Must be one of: {', '.join(valid_extensions)}",
            )

        # Check file permissions
        if not os.access(config_path, os.R_OK):
            return False, f"Cannot read config file (permission denied): {config_path}"

        return True, config_path

    def add_connection(self, name: str, config_path: str) -> Tuple[bool, str]:
        """
        Add a new VPN connection.

        Args:
            name: Name of the connection
            config_path: Path to the configuration file

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate inputs
            is_valid_name, name_error = self._validate_connection_name(name)
            if not is_valid_name:
                return False, name_error

            is_valid_path, path_error = self._validate_config_path(config_path)
            if not is_valid_path:
                return False, path_error

            config_path = path_error  # path_error contains the normalized path

            # Check if connection already exists
            if name in self.connections:
                return False, f"Connection '{name}' already exists"

            # Store connection
            self.connections[name] = {
                "path": config_path,
                "type": self._detect_vpn_type(config_path),
            }

            # Save to file
            if not self._save_connections():
                # Revert changes if save failed
                del self.connections[name]
                return False, "Failed to save connection"

            self.logger.info(f"Added connection: {name} -> {config_path}")
            return True, f"Added connection: {name}"

        except Exception as e:
            self.logger.error(f"Error adding connection: {str(e)}")
            return False, f"Failed to add connection: {str(e)}"

    def update_connection(
        self, old_name: str, new_name: Optional[str] = None, new_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Update an existing VPN connection.

        Args:
            old_name: Current name of the connection
            new_name: New name (optional)
            new_path: New config path (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if old_name not in self.connections:
                return False, f"Connection '{old_name}' not found"

            connection = self.connections[old_name].copy()

            # Update name if provided
            if new_name:
                is_valid, error = self._validate_connection_name(new_name)
                if not is_valid:
                    return False, error

                # Check if new name already exists
                if new_name != old_name and new_name in self.connections:
                    return False, f"Connection '{new_name}' already exists"

            # Update path if provided
            if new_path:
                is_valid, path_or_error = self._validate_config_path(new_path)
                if not is_valid:
                    return False, path_or_error
                connection["path"] = path_or_error
                connection["type"] = self._detect_vpn_type(path_or_error)

            # Remove old connection
            del self.connections[old_name]

            # Add updated connection
            target_name = new_name if new_name else old_name
            self.connections[target_name] = connection

            # Save to file
            if not self._save_connections():
                # Revert changes
                del self.connections[target_name]
                self.connections[old_name] = connection
                return False, "Failed to save connection"

            self.logger.info(f"Updated connection: {old_name} -> {target_name}")
            return True, f"Updated connection: {old_name}"

        except Exception as e:
            self.logger.error(f"Error updating connection: {str(e)}")
            return False, f"Failed to update connection: {str(e)}"

    def remove_connection(self, name: str) -> Tuple[bool, str]:
        """
        Remove a VPN connection.

        Args:
            name: Name of the connection to remove

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if name not in self.connections:
                return False, f"Connection '{name}' not found"

            del self.connections[name]

            if not self._save_connections():
                # Revert changes
                self.connections[name] = {"path": "", "type": ""}
                return False, "Failed to save changes"

            self.logger.info(f"Removed connection: {name}")
            return True, f"Removed connection: {name}"

        except Exception as e:
            self.logger.error(f"Error removing connection: {str(e)}")
            return False, f"Failed to remove connection: {str(e)}"

    def get_config_path(self, name: str) -> Optional[str]:
        """
        Get the configuration file path for a connection.

        Args:
            name: Name of the connection

        Returns:
            Path to the configuration file, or None if not found
        """
        try:
            if name in self.connections:
                return self.connections[name].get("path", "")
            return None
        except Exception as e:
            self.logger.error(f"Error getting config path for {name}: {str(e)}")
            return None

    def get_connection_type(self, name: str) -> Optional[str]:
        """
        Get the VPN type for a connection.

        Args:
            name: Name of the connection

        Returns:
            VPN type ("openvpn" or "wireguard"), or None if not found
        """
        try:
            if name in self.connections:
                return self.connections[name].get("type", "unknown")
            return None
        except Exception as e:
            self.logger.error(f"Error getting connection type for {name}: {str(e)}")
            return None

    def list_connections(self) -> List[str]:
        """
        List all connection names.

        Returns:
            List of connection names
        """
        try:
            return list(self.connections.keys())
        except Exception as e:
            self.logger.error(f"Error listing connections: {str(e)}")
            return []

    def get_all_connections(self) -> Dict[str, Dict]:
        """
        Get all connections with their details.

        Returns:
            Dictionary of all connections
        """
        try:
            return self.connections.copy()
        except Exception as e:
            self.logger.error(f"Error getting all connections: {str(e)}")
            return {}

    def _detect_vpn_type(self, config_path: str) -> str:
        """
        Detect the VPN type from the configuration file path.

        Args:
            config_path: Path to the configuration file

        Returns:
            "openvpn" or "wireguard"
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
            return "openvpn"
        return "unknown"
