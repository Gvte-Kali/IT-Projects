#!/bin/bash

# VPN Manager - Installation Script
# =================================
# Simple installation script for VPN Manager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to print header
print_header() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "       VPN Manager Installation"
    echo "=========================================="
    echo -e "${NC}"
}

# Function to print step
print_step() {
    echo -e "${BLUE}[*] $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Function to detect Linux distribution
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

# Function to install system dependencies
install_system_deps() {
    local distro=$(detect_distro)
    
    print_step "Detecting Linux distribution: $distro"
    
    case "$distro" in
        ubuntu|debian|pop|linuxmint)
            print_step "Installing dependencies for Debian/Ubuntu..."
            sudo apt-get update
            sudo apt-get install -y \
                python3 \
                python3-pip \
                openvpn \
                wireguard-tools \
                sudo \
                dnsutils  # for dig (DNS leak detection)
            ;;
        fedora|rhel|centos)
            print_step "Installing dependencies for Fedora/RHEL..."
            if command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y \
                    python3 \
                    python3-pip \
                    openvpn \
                    wireguard-tools \
                    which \
                    sudo \
                    bind-utils  # for dig
            elif command -v yum >/dev/null 2>&1; then
                sudo yum install -y \
                    python3 \
                    python3-pip \
                    openvpn \
                    wireguard-tools \
                    which \
                    sudo \
                    bind-utils
            fi
            ;;
        arch|manjaro|endeavouros)
            print_step "Installing dependencies for Arch Linux..."
            sudo pacman -Syu --noconfirm \
                python \
                python-pip \
                openvpn \
                wireguard-tools \
                which \
                sudo \
                bind  # for dig
            ;;
        opensuse|suse)
            print_step "Installing dependencies for openSUSE..."
            sudo zypper install -y \
                python3 \
                python3-pip \
                openvpn \
                wireguard-tools \
                which \
                sudo \
                bind-utils
            ;;
        *)
            print_error "Unsupported Linux distribution: $distro"
            print_error "Please install the following dependencies manually:"
            echo "  - Python 3"
            echo "  - pip (Python package manager)"
            echo "  - OpenVPN"
            echo "  - WireGuard tools (wg-quick, wg)"
            echo "  - sudo"
            echo "  - bind-utils or dnsutils (for dig command)"
            exit 1
            ;;
    esac
    
    print_success "System dependencies installed"
}

# Function to install Python dependencies
install_python_deps() {
    print_step "Installing Python dependencies..."
    
    # Install pystray and Pillow for system tray support
    pip3 install --user pystray Pillow
    
    print_success "Python dependencies installed"
}

# Function to create desktop entry
create_desktop_entry() {
    print_step "Creating desktop entry..."
    
    local desktop_file="$HOME/.local/share/applications/vpn-manager.desktop"
    
    cat > "$desktop_file" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=VPN Manager
GenericName=VPN Connection Manager
Comment=A simple GUI application for managing VPN connections on Linux
Exec=$SCRIPT_DIR/vpn_manager.py
Icon=$SCRIPT_DIR/assets/icon.svg
Terminal=false
Categories=Network;System;Settings;
StartupWMClass=VPN Manager
EOF
    
    chmod +x "$desktop_file"
    
    # Update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$HOME/.local/share/applications"
    fi
    
    print_success "Desktop entry created at $desktop_file"
}

# Function to create uninstall script
create_uninstall_script() {
    print_step "Creating uninstall script..."
    
    cat > "$SCRIPT_DIR/uninstall.sh" <<'EOF'
#!/bin/bash

echo "Uninstalling VPN Manager..."

# Remove desktop entry
rm -f "$HOME/.local/share/applications/vpn-manager.desktop"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications"
fi

# Remove configuration
rm -rf "$HOME/.config/vpn-manager"
rm -rf "$HOME/.local/share/vpn-manager"

echo "VPN Manager uninstalled successfully"
EOF
    
    chmod +x "$SCRIPT_DIR/uninstall.sh"
    print_success "Uninstall script created at $SCRIPT_DIR/uninstall.sh"
}

# Function to display installation summary
display_summary() {
    echo ""
    print_header
    echo -e "${GREEN}Installation Summary:${NC}"
    echo ""
    echo "VPN Manager has been installed successfully!"
    echo ""
    echo "To run VPN Manager:"
    echo "  1. From this directory: ./vpn_manager.py"
    echo "  2. Or use the desktop entry: VPN Manager"
    echo ""
    echo "Configuration files:"
    echo "  - Profiles: ~/.config/vpn-manager/profiles.json"
    echo "  - Logs: ~/.local/share/vpn-manager/logs/"
    echo ""
    echo "To uninstall:"
    echo "  Run: ./uninstall.sh"
    echo ""
    print_header
}

# Main installation function
main() {
    print_header
    echo ""
    
    # Check Python version
    print_step "Checking Python version..."
    if ! command -v python3 >/dev/null 2>&1; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
    if [ "$python_version" -lt "3.8" ]; then
        print_error "Python 3.8 or higher is required (found: $python_version)"
        exit 1
    fi
    print_success "Python $python_version found"
    
    # Check pip
    print_step "Checking pip..."
    if ! command -v pip3 >/dev/null 2>&1 && ! command -v pip >/dev/null 2>&1; then
        print_error "pip is not installed"
        exit 1
    fi
    print_success "pip found"
    
    # Install system dependencies
    install_system_deps
    
    # Install Python dependencies
    install_python_deps
    
    # Create desktop entry
    create_desktop_entry
    
    # Create uninstall script
    create_uninstall_script
    
    # Display summary
    display_summary
}

# Run main installation
main "$@"
