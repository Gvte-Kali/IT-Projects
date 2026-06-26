# VPN Manager

A **cross-distribution**, **cross-desktop environment** GUI application for managing VPN connections (OpenVPN, WireGuard) on Linux. Built with **Python**, **PyQt6**, and standard Linux networking tools.

## Features

- **Cross-Platform**: Works on any Linux distribution with PyQt6 and standard networking tools.
- **Cross-DE**: Compatible with all major desktop environments (GNOME, KDE, XFCE, LXQt, etc.).
- **VPN Support**: OpenVPN (`.ovpn`) and WireGuard (`.conf`).
- **System Tray Integration**: Control VPN connections directly from the system tray.
- **Connection Management**: Add, remove, and manage VPN configurations from any location on your system.
- **Real-Time Logs**: View connection logs in real-time for each VPN.
- **Status Monitoring**: Visual status indicators (green/red) for active/inactive connections.
- **Error Handling**: Robust error handling for all operations.

## Screenshots

*(Add screenshots here once the UI is finalized.)*

## Installation

### Dependencies

Ensure the following dependencies are installed on your system:

```bash
# Debian/Ubuntu
sudo apt install python3-pyqt6 openvpn wireguard-tools
```
```bash
# Fedora/RHEL
sudo dnf install python3-qt6 openvpn wireguard-tools
```
```bash
# Arch Linux
sudo pacman -S python-pyqt6 openvpn wireguard-tools
```
## Install Python Dependencies
```bash
pip install -r https://raw.githubusercontent.com/Gvte-Kali/IT-Projects/refs/heads/main/Linux-VPN-Manager/requirements.txt
```

## Usage


### Add a Connection:

Click "Add Connection" in the main window.
Enter a name and the path to your VPN configuration file (.ovpn or .conf).


### Connect/Disconnect:

Double-click a connection in the list or use the system tray menu.
Green icon = Connected (UP), Red icon = Disconnected (DOWN).


### View Logs:

Double-click a connection and select "View Logs" to see real-time logs.


### System Tray:

Right-click the tray icon to access all connections and controls.

### Configuration

VPN configurations are stored in ~/.config/vpn-manager/connections.json.
Logs are saved in ~/.local/share/vpn-manager/logs/.
Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
License
MIT
