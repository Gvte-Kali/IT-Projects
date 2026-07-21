# VPN Manager

Simple cross-distribution VPN manager for Linux with Tkinter GUI.

**Supports:** OpenVPN & WireGuard | **Compatible:** apt, dnf, pacman

---

## ✅ Features

- System tray integration
- DNS leak detection
- Auto-reconnect (configurable)
- Dark/light theme
- Profile management with extra args
- Real-time connection status

---

## 📥 Install

### Quick (recommended)
```bash
chmod +x install.sh && ./install.sh
```

### Manual
```bash
# Deps
pip3 install --user pystray Pillow

# System packages (choose one)
sudo apt install python3 python3-pip openvpn wireguard-tools sudo dnsutils  # Debian/Ubuntu
sudo dnf install python3 python3-pip openvpn wireguard-tools which sudo bind-utils  # Fedora/RHEL
sudo pacman -S python python-pip openvpn wireguard-tools which sudo bind  # Arch

# Run
python3 vpn_manager.py
```

---

## 🚀 Usage

```bash
./run.sh  # or python3 vpn_manager.py
```

- **Add profile:** Name + config path + type (auto-detected) + extra args
- **Connect:** Double-click or select + Connect button
- **Disconnect:** Select + Disconnect button
- **Tray:** Right-click icon for quick actions
- **Theme:** Toggle in Settings tab

---

## 📁 Files

- **Profiles:** `~/.config/vpn-manager/profiles.json`
- **Logs:** `~/.local/share/vpn-manager/logs/`

---

## 🔧 Troubleshooting

- **Missing deps:** `pip3 install --user pystray Pillow`
- **No openvpn:** Install with your package manager (see above)
- **No wg-quick:** Install wireguard-tools
- **No sudo:** Install sudo package

---

**Author:** Gvte-Kali | **License:** MIT
