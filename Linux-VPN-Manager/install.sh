#!/bin/bash

# VPN Manager - Installation Script
# =================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

print_header() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "       VPN Manager Installation"
    echo "=========================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[*] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif command -v lsb_release >/dev/null 2>&1; then
        lsb_release -si | tr '[:upper:]' '[:lower:]'
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    else
        echo "unknown"
    fi
}

install_deps_apt() {
    print_step "Installing dependencies with apt..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip openvpn wireguard-tools sudo dnsutils
    print_success "Dependencies installed with apt"
}

install_deps_dnf() {
    print_step "Installing dependencies with dnf..."
    sudo dnf install -y python3 python3-pip openvpn wireguard-tools which sudo bind-utils
    print_success "Dependencies installed with dnf"
}

install_deps_pacman() {
    print_step "Installing dependencies with pacman..."
    sudo pacman -Syu --noconfirm python python-pip openvpn wireguard-tools which sudo bind
    print_success "Dependencies installed with pacman"
}

install_python_deps() {
    print_step "Installing Python dependencies..."
    pip3 install --user pystray Pillow
    print_success "Python dependencies installed"
}

create_desktop_entry() {
    print_step "Creating desktop entry..."
    local desktop_file="$HOME/.local/share/applications/vpn-manager.desktop"
    cat > "$desktop_file" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=VPN Manager
Comment=A simple VPN manager for Linux
Exec=$SCRIPT_DIR/vpn_manager.py
Icon=$SCRIPT_DIR/assets/icon.svg
Terminal=false
Categories=Network;System;Settings;
EOF
    chmod +x "$desktop_file"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$HOME/.local/share/applications"
    fi
    print_success "Desktop entry created"
}

create_uninstall_script() {
    print_step "Creating uninstall script..."
    cat > "$SCRIPT_DIR/uninstall.sh" <<'EOF'
#!/bin/bash
rm -f "$HOME/.local/share/applications/vpn-manager.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications"
fi
rm -rf "$HOME/.config/vpn-manager" "$HOME/.local/share/vpn-manager"
echo "VPN Manager uninstalled"
EOF
    chmod +x "$SCRIPT_DIR/uninstall.sh"
    print_success "Uninstall script created"
}

display_summary() {
    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
    echo ""
    echo "Run: ./vpn_manager.py or use desktop entry"
    echo "Configs: ~/.config/vpn-manager/profiles.json"
    echo "Logs: ~/.local/share/vpn-manager/logs/"
    echo "Uninstall: ./uninstall.sh"
    echo ""
}

check_python() {
    print_step "Checking Python..."
    if ! command -v python3 >/dev/null 2>&1; then
        print_error "Python 3 not installed"
        exit 1
    fi
    version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
    if [ "$version" -lt "3.8" ]; then
        print_error "Python 3.8+ required (found: $version)"
        exit 1
    fi
    print_success "Python $version found"
}

check_pip() {
    print_step "Checking pip..."
    if ! command -v pip3 >/dev/null 2>&1 && ! command -v pip >/dev/null 2>&1; then
        print_error "pip not installed"
        exit 1
    fi
    print_success "pip found"
}

main() {
    print_header
    echo ""

    check_python
    check_pip

    distro=$(detect_distro)
    print_step "Detected distribution: $distro"

    case "$distro" in
        ubuntu|debian|pop|linuxmint)
            install_deps_apt
            ;;
        fedora|rhel|centos)
            install_deps_dnf
            ;;
        arch|manjaro|endeavouros)
            install_deps_pacman
            ;;
        *)
            print_error "Unsupported distribution: $distro"
            echo ""
            echo "Choose an option:"
            echo "  1) Cancel installation"
            echo "  2) Continue with apt"
            echo "  3) Continue with dnf"
            echo "  4) Continue with pacman"
            echo ""
            read -p "Enter choice [1-4]: " choice
            case "$choice" in
                1)
                    echo "Installation cancelled"
                    exit 0
                    ;;
                2)
                    install_deps_apt
                    ;;
                3)
                    install_deps_dnf
                    ;;
                4)
                    install_deps_pacman
                    ;;
                *)
                    print_error "Invalid choice"
                    exit 1
                    ;;
            esac
            ;;
    esac

    install_python_deps
    create_desktop_entry
    create_uninstall_script
    display_summary
}

main "$@"
