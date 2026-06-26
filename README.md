# 🔧 IT-Projects
**A collection of IT and cybersecurity projects for automation, networking, and pentesting.**

[![GitHub stars](https://img.shields.io/github/stars/Gvte-Kali/IT-Projects?style=flat-square)](https://github.com/Gvte-Kali/IT-Projects/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Gvte-Kali/IT-Projects?style=flat-square)](https://github.com/Gvte-Kali/IT-Projects/network)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-38%25-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Shell](https://img.shields.io/badge/Shell-62%25-green?logo=gnu-bash&logoColor=white)](https://www.gnu.org/software/bash/)

---

## 📌 **About**
This repository contains **open-source IT projects** focused on:
- **Networking & VPN** (OpenVPN, WireGuard, Tailscale)
- **Automation & Scripting** (Bash, Python)
- **Cybersecurity Tools** (Pentesting, Security Hardening)
- **Cross-Platform Solutions** (Linux, Docker, Raspberry Pi)

Each project is designed to be **modular, efficient, and production-ready**.

---

---

## 🚀 **Projects**
   **Project**          | **Description**                                                                                     | **Language**       | **Status**          |
 |----------------------|-----------------------------------------------------------------------------------------------------|--------------------|---------------------|
 | **[Linux-VPN-Manager](Linux-VPN-Manager)** | A **cross-DE GUI** for managing OpenVPN/WireGuard connections with system tray integration.       | Python (PyQt6)     | ✅ Active           |
 | **[SecurepathVPN](SecurepathVPN)**       | Automated **PiVPN deployment** with Tailscale fallback, VNC, and Discord notifications.               | Shell, Python      | ✅ Active           |

---

---

## 🛠 **Technologies & Tools**
- **Languages**: Python 3, Bash/Shell
- **Frameworks**: PyQt6, Qt6
- **Networking**: OpenVPN, WireGuard, Tailscale, NMCLI
- **OS**: Linux (Debian, Arch, Parrot OS), Raspberry Pi OS
- **Containerization**: Docker (Exegol, Portainer)
- **CI/CD**: GitHub Actions (WIP)
- **Monitoring**: Grafana, Prometheus

---

---

## 📥 **Installation**
### Global Requirements
- **Python 3.8+**
- **PyQt6** (`pip install PyQt6`)
- **OpenVPN/WireGuard** (`sudo apt install openvpn wireguard-tools`)

### Per-Project Setup
Each project has its own `README.md` with detailed instructions. Example for **Linux-VPN-Manager**:
```bash
git clone https://github.com/Gvte-Kali/IT-Projects.git
cd IT-Projects/Linux-VPN-Manager
pip install -r requirements.txt
python main.py