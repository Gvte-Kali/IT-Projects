# VPN Manager

A **cross-distribution**, **cross-desktop environment** GUI application for managing VPN connections (OpenVPN, WireGuard) on Linux. Built with **Python**, **PyQt6**, and standard Linux networking tools.

## Features

- **Cross-Platform**: Works on any Linux distribution with PyQt6 and standard networking tools
- **Cross-DE**: Compatible with all major desktop environments (GNOME, KDE, XFCE, LXQt, etc.)
- **VPN Support**: OpenVPN (`.ovpn`) and WireGuard (`.conf`)
- **System Tray Integration**: Control VPN connections directly from the system tray
- **Connection Management**: Add, remove, edit, and manage VPN configurations
- **Real-Time Logs**: View connection logs in real-time for each VPN
- **Status Monitoring**: Visual status indicators (green/red/yellow) for active/inactive/connecting connections
- **Auto-Refresh**: Automatic status updates every 5 seconds
- **Error Handling**: Robust error handling for all operations
- **Log Rotation**: Automatic log file rotation to prevent disk space issues
- **Professional Logging**: System-wide logging with configurable levels

## Screenshots

*(Add screenshots here once the UI is finalized.)*

## Requirements

### System Dependencies

The following system packages are required:

- Python 3.8 or higher
- pip (Python package manager)
- OpenVPN
- WireGuard tools (`wg-quick`, `wg`)
- `iproute2` (for `ip` command)
- `sudo` (for elevated privileges)

### Python Dependencies

- PyQt6 >= 6.4.0

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
5. Create assets (icons)
6. Generate an uninstall script

### Manual Installation

#### 1. Install System Dependencies

```bash
# Debian/Ubuntu
sudo apt install python3 python3-pip python3-venv openvpn wireguard-tools iproute2 sudo

# Fedora/RHEL
sudo dnf install python3 python3-pip openvpn wireguard-tools which sudo

# Arch Linux
sudo pacman -S python python-pip openvpn wireguard-tools which sudo

# openSUSE
sudo zypper install python3 python3-pip openvpn wireguard-tools which sudo
```

#### 2. Install Python Dependencies

```bash
# Create virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

#### 3. Run the Application

```bash
# If using virtual environment
source .venv/bin/activate
python3 main.py

# Or directly
python3 main.py
```

### Install as a Python Package

```bash
# From the project directory
pip install -e .

# Then run
vpn-manager
```

## Usage

### Adding a Connection

1. Click "Add Connection" in the main window or from the File menu
2. Enter a name for your connection (e.g., "My Work VPN")
3. Enter the path to your VPN configuration file (`.ovpn` or `.conf`)
4. Click OK

**Note**: Configuration files must be readable by your user. For OpenVPN, ensure the file has the correct permissions:
```bash
chmod 600 /path/to/your/config.ovpn
```

### Connecting/Disconnecting

- **From Main Window**: Double-click a connection or select it and click "Connect"/"Disconnect"
- **From System Tray**: Right-click the tray icon and select your connection
- **Status Indicators**:
  - 🟢 Green: Connected (UP)
  - 🔴 Red: Disconnected (DOWN)
  - 🟡 Yellow: Connecting

### Viewing Logs

1. Select a connection in the main window
2. Click "View Logs" button or right-click and select "View Logs"
3. Logs will appear in a new window with auto-refresh

**Log Features**:
- Auto-refresh (2s, 5s, 10s, or Off)
- Manual refresh
- Clear logs
- Save logs to file
- Scroll to bottom automatically

### Editing a Connection

1. Right-click a connection in the main window
2. Select "Edit"
3. Update the name and/or configuration file path
4. Click OK

### Removing a Connection

1. Select a connection in the main window
2. Click "Remove Connection" or right-click and select "Remove"
3. Confirm the deletion

**Note**: Active connections will be stopped before removal.

### System Tray Menu

Right-click the VPN Manager tray icon to access:
- Show VPN Manager: Open the main window
- Connection list with status indicators
- Status summary (e.g., "2 active / 5 total")
- Quit: Exit the application

## Configuration

### Configuration Files

- **Connections**: `~/.config/vpn-manager/connections.json`
  - Stores all VPN connection configurations
  - Format: `{"connection_name": {"path": "/path/to/config.ovpn", "type": "openvpn"}}`

- **Logs**: `~/.local/share/vpn-manager/logs/`
  - Contains individual log files for each connection
  - Log rotation: 5 files, 5MB each

- **Application Log**: `~/.local/share/vpn-manager/app.log`
  - System-wide application logging

### Environment Variables

- `VPN_MANAGER_CONFIG_DIR`: Custom configuration directory (default: `~/.config/vpn-manager`)
- `VPN_MANAGER_LOG_DIR`: Custom log directory (default: `~/.local/share/vpn-manager/logs`)

## Troubleshooting

### Common Issues

#### "Required icon files are missing"

Run the install script to generate icons:
```bash
./install.sh
```

Or manually create the `assets/` directory with the required icons:
- `assets/icon.png` - Main application icon
- `assets/green.png` - Connected status icon
- `assets/red.png` - Disconnected status icon
- `assets/yellow.png` - Connecting status icon

#### "OpenVPN command not found"

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

#### "ModuleNotFoundError: No module named 'PyQt6'"

Install PyQt6:
```bash
pip install PyQt6
```

#### VPN connection fails to start

- Ensure your configuration file is valid
- Check file permissions: `chmod 600 /path/to/config.ovpn`
- Verify the configuration file path is correct
- Check if `sudo` is properly configured for your user

### Debug Mode

Run with debug logging:
```bash
python3 -m logging -v main.py
```

Or check the application log:
```bash
cat ~/.local/share/vpn-manager/app.log
```

## Security Considerations

1. **Configuration Files**: VPN configuration files may contain sensitive information (certificates, keys, passwords). Ensure they are stored securely with appropriate permissions.

2. **Sudo Requirements**: The application uses `sudo` for VPN operations. Ensure your user has the necessary sudo privileges.

3. **Network Access**: VPN connections have full network access. Only use trusted configuration files.

4. **Logging**: Connection logs may contain sensitive information. Logs are stored in `~/.local/share/vpn-manager/logs/` with rotation enabled.

## Development

### Project Structure

```
Linux-VPN-Manager/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── setup.py               # Python package setup
├── install.sh             # Installation script
├── uninstall.sh           # Uninstall script
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── assets/                # Icons and assets
│   ├── icon.png           # Main icon
│   ├── green.png          # Connected icon
│   ├── red.png            # Disconnected icon
│   └── yellow.png         # Connecting icon
├── backend/
│   ├── __init__.py
│   ├── vpn_handler.py     # VPN connection management
│   ├── config_manager.py  # Configuration management
│   └── log_manager.py     # Logging management
└── frontend/
    ├── __init__.py
    ├── main_window.py     # Main GUI window
    ├── tray_icon.py        # System tray icon
    └── log_viewer.py      # Log viewer dialog
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-qt

# Run tests
pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Include docstrings for all public methods
- Use logging instead of print statements
- Handle exceptions gracefully

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/) - Python bindings for Qt
- [OpenVPN](https://openvpn.net/) - Open source VPN solution
- [WireGuard](https://www.wireguard.com/) - Fast, modern, secure VPN tunnel

## Support

For issues, questions, or feature requests, please open an issue on the GitHub repository.
