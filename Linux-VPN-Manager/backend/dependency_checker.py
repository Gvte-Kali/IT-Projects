"""
Dependency Checker Module

Provides functionality to check for required system and Python dependencies.
"""

import subprocess
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from enum import Enum
import logging


class DependencyStatus(Enum):
    """Status of a dependency check."""
    INSTALLED = "installed"
    MISSING = "missing"
    VERSION_TOO_OLD = "version_too_old"
    NOT_CHECKED = "not_checked"


class DependencyType(Enum):
    """Type of dependency."""
    SYSTEM = "system"
    PYTHON = "python"
    OPTIONAL = "optional"


class DependencyChecker:
    """
    Checks for required system and Python dependencies.
    """

    # Required system commands and their minimum versions
    SYSTEM_DEPENDENCIES = {
        "openvpn": {"min_version": "2.4", "optional": False, "description": "OpenVPN client"},
        "wireguard": {"min_version": None, "optional": True, "description": "WireGuard tools"},
        "wg-quick": {"min_version": None, "optional": True, "description": "WireGuard quick setup"},
        "ip": {"min_version": None, "optional": False, "description": "IP route management"},
        "ping": {"min_version": None, "optional": False, "description": "Network connectivity check"},
        "systemctl": {"min_version": None, "optional": True, "description": "Systemd control"},
        "nmcli": {"min_version": None, "optional": True, "description": "NetworkManager CLI"},
        "notify-send": {"min_version": None, "optional": True, "description": "Desktop notifications"},
    }

    # Required Python packages and their minimum versions
    PYTHON_DEPENDENCIES = {
        "PyQt6": {"min_version": "6.0.0", "optional": False, "description": "GUI framework"},
        "psutil": {"min_version": "5.0.0", "optional": True, "description": "System monitoring"},
        "pydbus": {"min_version": "0.6.0", "optional": True, "description": "D-Bus integration"},
        "Pillow": {"min_version": "8.0.0", "optional": True, "description": "Image processing"},
        "matplotlib": {"min_version": "3.0.0", "optional": True, "description": "Graph plotting"},
    }

    def __init__(self):
        """Initialize the dependency checker."""
        self.logger = logging.getLogger("DependencyChecker")
        self._cache: Dict[str, Tuple[DependencyStatus, str]] = {}

    def check_all(self) -> Dict[str, Dict[str, any]]:
        """
        Check all dependencies and return a comprehensive report.
        
        Returns:
            Dictionary with dependency names as keys and their status info as values.
        """
        report = {}
        
        # Check system dependencies
        for cmd, info in self.SYSTEM_DEPENDENCIES.items():
            status, version = self.check_system_dependency(cmd)
            report[cmd] = {
                "type": DependencyType.SYSTEM.value,
                "status": status.value,
                "version": version,
                "optional": info["optional"],
                "description": info["description"],
                "min_version": info.get("min_version"),
            }
        
        # Check Python dependencies
        for pkg, info in self.PYTHON_DEPENDENCIES.items():
            status, version = self.check_python_dependency(pkg)
            report[pkg] = {
                "type": DependencyType.PYTHON.value,
                "status": status.value,
                "version": version,
                "optional": info["optional"],
                "description": info["description"],
                "min_version": info.get("min_version"),
            }
        
        return report

    def check_system_dependency(self, command: str) -> Tuple[DependencyStatus, Optional[str]]:
        """
        Check if a system command is available and its version.
        
        Args:
            command: The command name to check.
            
        Returns:
            Tuple of (status, version) where version is None if not installed.
        """
        cache_key = f"system_{command}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Check if command exists
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                self._cache[cache_key] = (DependencyStatus.MISSING, None)
                return self._cache[cache_key]
            
            # Get version if available
            version = None
            version_commands = [
                [command, "--version"],
                [command, "-v"],
                [command, "version"],
            ]
            
            for cmd in version_commands:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # Extract version from output
                        output = result.stdout + result.stderr
                        version = self._extract_version(output)
                        break
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            self._cache[cache_key] = (DependencyStatus.INSTALLED, version)
            return self._cache[cache_key]
            
        except Exception as e:
            self.logger.warning(f"Error checking system dependency {command}: {e}")
            self._cache[cache_key] = (DependencyStatus.MISSING, None)
            return self._cache[cache_key]

    def check_python_dependency(self, package: str) -> Tuple[DependencyStatus, Optional[str]]:
        """
        Check if a Python package is available and its version.
        
        Args:
            package: The Python package name to check.
            
        Returns:
            Tuple of (status, version) where version is None if not installed.
        """
        cache_key = f"python_{package}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Try to import the package
            module = importlib.import_module(package.lower() if package != "Pillow" else "PIL")
            version = getattr(module, "__version__", None)
            
            if version is None:
                # Try pkg_resources for some packages
                try:
                    import pkg_resources
                    version = pkg_resources.get_distribution(package).version
                except Exception:
                    version = "unknown"
            
            self._cache[cache_key] = (DependencyStatus.INSTALLED, str(version))
            return self._cache[cache_key]
            
        except ImportError:
            self._cache[cache_key] = (DependencyStatus.MISSING, None)
            return self._cache[cache_key]
        except Exception as e:
            self.logger.warning(f"Error checking Python dependency {package}: {e}")
            self._cache[cache_key] = (DependencyStatus.MISSING, None)
            return self._cache[cache_key]

    def _extract_version(self, output: str) -> Optional[str]:
        """
        Extract version number from command output.
        
        Args:
            output: The command output string.
            
        Returns:
            Extracted version string or None.
        """
        import re
        
        # Common version patterns
        patterns = [
            r'\d+\.\d+\.\d+',  # X.Y.Z
            r'\d+\.\d+',        # X.Y
            r'version\s+(\d+\.\d+(\.\d+)?)',
            r'v\d+\.\d+(\.\d+)?',
            r'(\d+\.\d+(\.\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None

    def get_missing_dependencies(self) -> List[Dict[str, any]]:
        """
        Get list of missing or outdated dependencies.
        
        Returns:
            List of dictionaries with information about missing dependencies.
        """
        missing = []
        report = self.check_all()
        
        for name, info in report.items():
            if info["status"] != DependencyStatus.INSTALLED.value and not info["optional"]:
                missing.append(info)
        
        return missing

    def get_optional_missing(self) -> List[Dict[str, any]]:
        """
        Get list of missing optional dependencies.
        
        Returns:
            List of dictionaries with information about missing optional dependencies.
        """
        missing = []
        report = self.check_all()
        
        for name, info in report.items():
            if info["status"] != DependencyStatus.INSTALLED.value and info["optional"]:
                missing.append(info)
        
        return missing

    def check_version_requirement(self, name: str, min_version: str) -> bool:
        """
        Check if a dependency meets the minimum version requirement.
        
        Args:
            name: Dependency name.
            min_version: Minimum required version.
            
        Returns:
            True if version requirement is met, False otherwise.
        """
        from packaging import version
        
        status, current_version = self.check_dependency(name)
        
        if status != DependencyStatus.INSTALLED:
            return False
        
        if current_version is None:
            return True  # Can't check version, assume it's ok
        
        try:
            return version.parse(current_version) >= version.parse(min_version)
        except Exception:
            return True  # If version parsing fails, assume it's ok

    def check_dependency(self, name: str) -> Tuple[DependencyStatus, Optional[str]]:
        """
        Check a specific dependency (system or Python).
        
        Args:
            name: Dependency name.
            
        Returns:
            Tuple of (status, version).
        """
        # Check if it's a system dependency
        if name in self.SYSTEM_DEPENDENCIES:
            return self.check_system_dependency(name)
        
        # Check if it's a Python dependency
        if name in self.PYTHON_DEPENDENCIES:
            return self.check_python_dependency(name)
        
        # Unknown dependency
        return (DependencyStatus.NOT_CHECKED, None)

    def get_installation_commands(self, distro: str = "auto") -> Dict[str, str]:
        """
        Get installation commands for missing dependencies.
        
        Args:
            distro: Linux distribution (auto-detected if 'auto').
            
        Returns:
            Dictionary with dependency names as keys and installation commands as values.
        """
        if distro == "auto":
            distro = self._detect_distro()
        
        commands = {}
        missing = self.get_missing_dependencies()
        
        for dep in missing:
            name = dep["name"]
            if dep["type"] == DependencyType.SYSTEM.value:
                cmd = self._get_system_install_command(name, distro)
                if cmd:
                    commands[name] = cmd
            elif dep["type"] == DependencyType.PYTHON.value:
                commands[name] = f"pip3 install {name}"
        
        return commands

    def _detect_distro(self) -> str:
        """
        Detect the Linux distribution.
        
        Returns:
            Distribution name (lowercase).
        """
        try:
            # Check /etc/os-release
            os_release = Path("/etc/os-release")
            if os_release.exists():
                content = os_release.read_text()
                if "ID=" in content:
                    for line in content.split('\n'):
                        if line.startswith("ID="):
                            return line.split("=")[1].strip().strip('"').lower()
            
            # Check /etc/lsb-release
            lsb_release = Path("/etc/lsb-release")
            if lsb_release.exists():
                content = lsb_release.read_text()
                if "DISTRIB_ID=" in content:
                    for line in content.split('\n'):
                        if line.startswith("DISTRIB_ID="):
                            return line.split("=")[1].strip().strip('"').lower()
            
            # Fallback to uname
            return "linux"
        except Exception:
            return "unknown"

    def _get_system_install_command(self, package: str, distro: str) -> Optional[str]:
        """
        Get installation command for a system package.
        
        Args:
            package: Package name.
            distro: Distribution name.
            
        Returns:
            Installation command or None.
        """
        # Package name mappings for different distros
        package_maps = {
            "debian": {
                "openvpn": "openvpn",
                "wireguard": "wireguard",
                "wg-quick": "wireguard-tools",
                "ip": "iproute2",
                "ping": "iputils-ping",
                "systemctl": "systemd",
                "nmcli": "network-manager",
                "notify-send": "libnotify-bin",
            },
            "ubuntu": {
                "openvpn": "openvpn",
                "wireguard": "wireguard",
                "wg-quick": "wireguard-tools",
                "ip": "iproute2",
                "ping": "iputils-ping",
                "systemctl": "systemd",
                "nmcli": "network-manager",
                "notify-send": "libnotify-bin",
            },
            "fedora": {
                "openvpn": "openvpn",
                "wireguard": "wireguard-tools",
                "wg-quick": "wireguard-tools",
                "ip": "iproute",
                "ping": "iputils",
                "systemctl": "systemd",
                "nmcli": "NetworkManager",
                "notify-send": "libnotify",
            },
            "arch": {
                "openvpn": "openvpn",
                "wireguard": "wireguard-tools",
                "wg-quick": "wireguard-tools",
                "ip": "iproute2",
                "ping": "iputils",
                "systemctl": "systemd",
                "nmcli": "networkmanager",
                "notify-send": "libnotify",
            },
            "opensuse": {
                "openvpn": "openvpn",
                "wireguard": "wireguard-tools",
                "wg-quick": "wireguard-tools",
                "ip": "iproute2",
                "ping": "iputils",
                "systemctl": "systemd",
                "nmcli": "NetworkManager",
                "notify-send": "libnotify4",
            },
        }
        
        # Get the correct package name for the distro
        distro_lower = distro.lower()
        package_name = package
        
        for distro_key, packages in package_maps.items():
            if distro_lower.startswith(distro_key):
                package_name = packages.get(package, package)
                break
        
        # Return installation command based on distro
        if distro_lower in ["debian", "ubuntu", "pop", "linuxmint"]:
            return f"sudo apt-get install -y {package_name}"
        elif distro_lower in ["fedora", "rhel", "centos", "rocky", "almalinux"]:
            return f"sudo dnf install -y {package_name}"
        elif distro_lower in ["arch", "manjaro", "endeavouros"]:
            return f"sudo pacman -S --noconfirm {package_name}"
        elif distro_lower in ["opensuse", "suse"]:
            return f"sudo zypper install -y {package_name}"
        else:
            return None
