# VPN Manager

A **simple**, **cross-distribution** GUI application for managing VPN connections (OpenVPN, WireGuard) on Linux. Built with **Python** and **Tkinter**.

## Features

- **Cross-Platform**: Works on any Linux distribution (Debian/Ubuntu, Fedora/RHEL, Arch)
- **Cross-DE**: Compatible with all major desktop environments
- **VPN Support**: OpenVPN (`.ovpn`) and WireGuard (`.conf`)
- **System Tray Integration**: Control VPN connections directly from the system tray
- **Profile Management**: Add, remove, edit, and manage VPN configuration profiles
- **Extra Arguments**: Add custom command line arguments to VPN connections
- **Real-Time Status**: Visual status indicators for active/inactive/connecting connections
- **DNS Leak Detection**: Automatically checks for DNS leaks while VPN is connected
- **Auto-Reconnect**: Automatically reconnects if VPN connection drops
- **Dark/Light Theme**: Toggle between dark and light themes
- **Simple & Lightweight**: Single Python file with minimal dependencies

## Screenshots

*(Add screenshots here once the UI is finalized.)*

## Requirements

### System Dependencies

The following system packages are required:

- Python 3.8 or higher
- pip (Python package manager)
- OpenVPN
- WireGuard tools (`wg-quick`, `wg`)
- `sudo` (for elevated privileges)
- `dig` or `nslookup` (for DNS leak detection, optional)

### Python Dependencies

- pystray (for system tray icon)
- Pillow (for image handling)

## Installation

### Quick Install (Recommended)

Run the installation script:

```bash
chmod +x install.sh
./install.sh
```

This will:
1. Detect your Linux distribution
2. Install all required system dependencies
3. Install Python dependencies
4. Create desktop entry
5. Create uninstall script

### Manual Installation

#### 1. Install System Dependencies

```bash
# Debian/Ubuntu
sudo apt install python3 python3-pip openvpn wireguard-tools sudo dnsutils

# Fedora/RHEL
sudo dnf install python3 python3-pip openvpn wireguard-tools which sudo bind-utils

# Arch Linux
sudo pacman -S python python-pip openvpn wireguard-tools which sudo bind

# openSUSE
sudo zypper install python3 python3-pip openvpn wireguard-tools which sudo bind-utils
```

#### 2. Install Python Dependencies

```bash
pip3 install --user pystray Pillow
```

#### 3. Run the Application

```bash
python3 vpn_manager.py
```

## Usage

### Adding a Profile

1. Click "Add Profile" in the Profiles tab or from the context menu
2. Enter a name for your profile (e.g., "My Work VPN")
3. Enter the path to your VPN configuration file (`.ovpn` or `.conf`)
4. Select VPN type (auto-detected from file extension)
5. Optionally add extra command line arguments
6. Click OK

**Note**: Configuration files must be readable by your user. For OpenVPN, ensure the file has the correct permissions:
```bash
chmod 600 /path/to/your/config.ovpn
```

### Connecting/Disconnecting

- **From Main Window**: Double-click a profile or select it and click "Connect"/"Disconnect"
- **From System Tray**: Right-click the tray icon and select your profile
- **Status Indicators**:
  - `[OK]`: Connected
  - `[...]`: Connecting
  - `[X]`: Disconnected
  - `[ERR]`: Failed

### Viewing Logs

1. Select a profile in the Connections tab
2. Click "View Logs" button or right-click and select "View Logs"
3. Logs will appear in the Logs tab

### Editing a Profile

1. Right-click a profile in the Profiles tab
2. Select "Edit Profile"
3. Update the name, config file path, VPN type, or extra arguments
4. Click Save

### Removing a Profile

1. Select a profile in the Connections or Profiles tab
2. Click "Remove" or right-click and select "Remove"
3. Confirm the deletion

**Note**: Active connections will be stopped before removal.

### System Tray Menu

Right-click the VPN Manager tray icon to access:
- Profile list with status indicators
- Add Profile
- Toggle Theme
- Show (open main window)
- Quit

### DNS Leak Detection

The application automatically checks for DNS leaks every 30 seconds when a VPN is connected. If a leak is detected:
- A warning will be shown in the UI
- The DNS status label will turn red
- The connection will show "LEAK" in the DNS column

You can also manually check for DNS leaks by clicking "Check DNS Leak Now" in the Settings tab.

### Auto-Reconnect

If a VPN connection drops, the application will automatically attempt to reconnect up to 3 times (configurable in Settings tab).

### Theme

Toggle between dark and light themes:
- Click "Toggle Dark/Light Theme" in the Settings tab
- Or from the system tray menu

## Configuration

### Configuration Files

- **Profiles**: `~/.config/vpn-manager/profiles.json`
  - Stores all VPN profile configurations
  - Format: JSON with profile name as key

- **Logs**: `~/.local/share/vpn-manager/logs/`
  - Contains main application log and per-profile logs

- **Theme**: `~/.config/vpn-manager/theme.json`
  - Stores theme preference

### Profile Format

Each profile in `profiles.json` has the following structure:

```json
{
  "profile_name": {
    "path": "/path/to/config.ovpn",
    "type": "openvpn",
    "extra_args": "--some-arg value",
    "created": "2024-01-01T12:00:00"
  }
}
```

## Troubleshooting

### Common Issues

#### "pystray or Pillow not found"

Install the required Python packages:
```bash
pip3 install --user pystray Pillow
```

#### "openvpn command not found"

Install OpenVPN:
```bash
# Debian/Ubuntu
sudo apt install openvpn

# Fedora/RHEL
sudo dnf install openvpn

# Arch Linux
sudo pacman -S openvpn
```

#### "wg-quick command not found"

Install WireGuard tools:
```bash
# Debian/Ubuntu
sudo apt install wireguard-tools

# Fedora/RHEL
sudo dnf install wireguard-tools

# Arch Linux
sudo pacman -S wireguard-tools
```

#### "sudo: command not found"

Install sudo:
```bash
# Debian/Ubuntu
sudo apt install sudo

# Fedora/RHEL
sudo dnf install sudo

# Arch Linux
sudo pacman -S sudo
```

#### VPN connection fails to start

- Ensure your configuration file is valid
- Check file permissions: `chmod 600 /path/to/config.ovpn`
- Verify the configuration file path is correct
- Check if `sudo` is properly configured for your user
- Try running the VPN command manually to see the error

### Debug Mode

Run with debug logging:
```bash
python3 vpn_manager.py
```

Or check the application log:
```bash
cat ~/.local/share/vpn-manager/logs/vpn-manager.log
```

## Security Considerations

1. **Configuration Files**: VPN configuration files may contain sensitive information (certificates, keys, passwords). Ensure they are stored securely with appropriate permissions.

2. **Sudo Requirements**: The application uses `sudo` for VPN operations. Ensure your user has the necessary sudo privileges.

3. **Network Access**: VPN connections have full network access. Only use trusted configuration files.

4. **Logging**: Connection logs may contain sensitive information. Logs are stored in `~/.local/share/vpn-manager/logs/`.

## Project Structure

```
Linux-VPN-Manager/
├── vpn_manager.py      # Main application entry point
├── install.sh           # Installation script
├── uninstall.sh         # Uninstall script (created by install.sh)
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── LICENSE              # License file
├── assets/              # Icons and assets
│   ├── icon.svg
│   ├── green.svg
│   ├── red.svg
│   └── yellow.svg
└── src/                # Source modules
    ├── __init__.py
    ├── config.py        # Configuration and constants
    ├── profile_manager.py  # Profile management
    ├── vpn_handler.py   # VPN connection handling
    ├── theme_manager.py # Theme management
    └── tray_icon.py     # System tray icon
```

## Development

### Running

```bash
# Run the application
python3 vpn_manager.py

# Or with Python path
PYTHONPATH=./src python3 vpn_manager.py
```

### Testing

The application has been tested on:
- Arch Linux
- Ubuntu
- Fedora

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Tkinter](https://docs.python.org/3/library/tkinter.html) - Python GUI framework
- [pystray](https://github.com/moses-palmer/pystray) - System tray icon support
- [Pillow](https://python-pillow.org/) - Image handling
- [OpenVPN](https://openvpn.net/) - Open source VPN solution
- [WireGuard](https://www.wireguard.com/) - Fast, modern, secure VPN tunnel

## Support

For issues, questions, or feature requests, please open an issue on the GitHub repository.
