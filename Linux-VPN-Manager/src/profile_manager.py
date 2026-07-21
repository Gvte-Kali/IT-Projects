"""
Profile Manager - Manages VPN connection profiles
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from .config import CONFIG_DIR, CONFIG_FILE, VPN_OPENVPN, VPN_WIREGUARD

logger = logging.getLogger("ProfileManager")


class ProfileManager:
    """Manages VPN connection profiles."""
    
    def __init__(self):
        """Initialize the profile manager."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, Dict] = {}
        self._load_profiles()
    
    def _load_profiles(self) -> None:
        """Load profiles from configuration file."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.profiles = json.load(f)
                logger.info(f"Loaded {len(self.profiles)} profiles")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading profiles: {e}")
            self.profiles = {}
    
    def _save_profiles(self) -> bool:
        """Save profiles to configuration file."""
        try:
            backup_file = CONFIG_FILE.with_suffix('.bak')
            if CONFIG_FILE.exists():
                CONFIG_FILE.rename(backup_file)
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, indent=2, ensure_ascii=False)
            
            if backup_file.exists():
                backup_file.unlink()
            
            logger.info("Profiles saved successfully")
            return True
        except IOError as e:
            logger.error(f"Error saving profiles: {e}")
            if backup_file.exists():
                backup_file.rename(CONFIG_FILE)
            return False
    
    def add_profile(self, name: str, config_path: str, vpn_type: str, 
                   extra_args: str = "") -> Tuple[bool, str]:
        """Add a new VPN profile."""
        try:
            if not name or not name.strip():
                return False, "Profile name cannot be empty"
            
            name = name.strip()
            
            if name in self.profiles:
                return False, f"Profile '{name}' already exists"
            
            config_path = os.path.abspath(os.path.expanduser(config_path.strip()))
            
            if not os.path.exists(config_path):
                return False, f"Config file does not exist: {config_path}"
            
            if not os.path.isfile(config_path):
                return False, f"Path is not a file: {config_path}"
            
            if vpn_type == "auto":
                vpn_type = self._detect_vpn_type(config_path)
            
            if vpn_type not in [VPN_OPENVPN, VPN_WIREGUARD]:
                return False, f"Unsupported VPN type: {vpn_type}"
            
            self.profiles[name] = {
                "path": config_path,
                "type": vpn_type,
                "extra_args": extra_args.strip(),
                "created": datetime.now().isoformat(),
            }
            
            if self._save_profiles():
                logger.info(f"Added profile: {name}")
                return True, f"Profile '{name}' added successfully"
            else:
                del self.profiles[name]
                return False, "Failed to save profile"
                
        except Exception as e:
            logger.error(f"Error adding profile: {e}")
            return False, f"Error: {str(e)}"
    
    def update_profile(self, old_name: str, new_name: Optional[str] = None,
                      new_path: Optional[str] = None, new_type: Optional[str] = None,
                      new_args: Optional[str] = None) -> Tuple[bool, str]:
        """Update an existing profile."""
        try:
            if old_name not in self.profiles:
                return False, f"Profile '{old_name}' not found"
            
            profile = self.profiles[old_name].copy()
            
            if new_name:
                new_name = new_name.strip()
                if not new_name:
                    return False, "Profile name cannot be empty"
                if new_name != old_name and new_name in self.profiles:
                    return False, f"Profile '{new_name}' already exists"
            
            if new_path:
                new_path = os.path.abspath(os.path.expanduser(new_path.strip()))
                if not os.path.exists(new_path):
                    return False, f"Config file does not exist: {new_path}"
                if not os.path.isfile(new_path):
                    return False, f"Path is not a file: {new_path}"
                profile["path"] = new_path
            
            if new_type:
                if new_type not in [VPN_OPENVPN, VPN_WIREGUARD, "auto"]:
                    return False, f"Unsupported VPN type: {new_type}"
                if new_type == "auto":
                    new_type = self._detect_vpn_type(profile.get("path", ""))
                profile["type"] = new_type
            
            if new_args is not None:
                profile["extra_args"] = new_args.strip()
            
            del self.profiles[old_name]
            target_name = new_name if new_name else old_name
            self.profiles[target_name] = profile
            
            if self._save_profiles():
                logger.info(f"Updated profile: {old_name} -> {target_name}")
                return True, f"Profile '{old_name}' updated successfully"
            else:
                del self.profiles[target_name]
                self.profiles[old_name] = profile
                return False, "Failed to save profile"
                
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False, f"Error: {str(e)}"
    
    def remove_profile(self, name: str) -> Tuple[bool, str]:
        """Remove a profile."""
        try:
            if name not in self.profiles:
                return False, f"Profile '{name}' not found"
            
            del self.profiles[name]
            
            if self._save_profiles():
                logger.info(f"Removed profile: {name}")
                return True, f"Profile '{name}' removed successfully"
            else:
                self.profiles[name] = {}
                return False, "Failed to save changes"
                
        except Exception as e:
            logger.error(f"Error removing profile: {e}")
            return False, f"Error: {str(e)}"
    
    def get_profile(self, name: str) -> Optional[Dict]:
        """Get a profile by name."""
        return self.profiles.get(name)
    
    def list_profiles(self) -> List[str]:
        """List all profile names."""
        return list(self.profiles.keys())
    
    def get_all_profiles(self) -> Dict[str, Dict]:
        """Get all profiles."""
        return self.profiles.copy()
    
    def _detect_vpn_type(self, config_path: str) -> str:
        """Detect VPN type from configuration file."""
        if config_path.endswith(".ovpn"):
            return VPN_OPENVPN
        elif config_path.endswith(".conf"):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "[Interface]" in content:
                        return VPN_WIREGUARD
            except Exception:
                pass
            return VPN_OPENVPN
        return VPN_OPENVPN
