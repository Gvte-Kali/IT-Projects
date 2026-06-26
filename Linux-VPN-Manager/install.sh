#!/bin/bash

# VPN Manager - Installation Script
# =================================
# This script installs VPN Manager with all required dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Some operations may require user-specific setup.${NC}"
fi

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
    echo -e "${GREEN}[✓] $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}[✗] $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif command_exists lsb_release; then
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
                python3-venv \
                openvpn \
                wireguard-tools \
                resolvconf \
                iproute2 \
                sudo
            ;;
        fedora|rhel|centos)
            print_step "Installing dependencies for Fedora/RHEL..."
            if command_exists dnf; then
                sudo dnf install -y \
                    python3 \
                    python3-pip \
                    openvpn \
                    wireguard-tools \
                    which \
                    sudo
            elif command_exists yum; then
                sudo yum install -y \
                    python3 \
                    python3-pip \
                    openvpn \
                    wireguard-tools \
                    which \
                    sudo
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
                sudo
            ;;
        opensuse|suse)
            print_step "Installing dependencies for openSUSE..."
            sudo zypper install -y \
                python3 \
                python3-pip \
                openvpn \
                wireguard-tools \
                which \
                sudo
            ;;
        *)
            print_error "Unsupported Linux distribution: $distro"
            print_error "Please install the following dependencies manually:"
            echo "  - Python 3"
            echo "  - pip (Python package manager)"
            echo "  - OpenVPN"
            echo "  - WireGuard tools (wg-quick, wg)"
            echo "  - sudo"
            echo "  - iproute2 (ip command)"
            exit 1
            ;;
    esac
    
    print_success "System dependencies installed"
}

# Function to create assets directory and icons
create_assets() {
    print_step "Creating assets..."
    
    # Create assets directory
    mkdir -p "$SCRIPT_DIR/assets"
    
    # Create simple SVG icons if they don't exist
    # Green circle icon (for connected)
    if [ ! -f "$SCRIPT_DIR/assets/green.png" ]; then
        # Create a simple green PNG using ImageMagick if available
        if command_exists convert; then
            convert -size 16x16 xc:none -fill green -draw "circle 8,8 8,1" "$SCRIPT_DIR/assets/green.png"
        else
            # Create a placeholder file
            echo "Placeholder green icon" > "$SCRIPT_DIR/assets/green.png"
        fi
    fi
    
    # Red circle icon (for disconnected)
    if [ ! -f "$SCRIPT_DIR/assets/red.png" ]; then
        if command_exists convert; then
            convert -size 16x16 xc:none -fill red -draw "circle 8,8 8,1" "$SCRIPT_DIR/assets/red.png"
        else
            echo "Placeholder red icon" > "$SCRIPT_DIR/assets/red.png"
        fi
    fi
    
    # Yellow circle icon (for connecting)
    if [ ! -f "$SCRIPT_DIR/assets/yellow.png" ]; then
        if command_exists convert; then
            convert -size 16x16 xc:none -fill yellow -draw "circle 8,8 8,1" "$SCRIPT_DIR/assets/yellow.png"
        else
            echo "Placeholder yellow icon" > "$SCRIPT_DIR/assets/yellow.png"
        fi
    fi
    
    # Main icon
    if [ ! -f "$SCRIPT_DIR/assets/icon.png" ]; then
        if command_exists convert; then
            # Create a simple VPN icon
            convert -size 64x64 xc:none -fill blue -draw "rectangle 10,20 54,44" "$SCRIPT_DIR/assets/icon.png"
        else
            echo "Placeholder icon" > "$SCRIPT_DIR/assets/icon.png"
        fi
    fi
    
    print_success "Assets created"
}

# Function to install Python dependencies
install_python_deps() {
    print_step "Installing Python dependencies..."
    
    # Create virtual environment (optional)
    if [ ! -d "$SCRIPT_DIR/.venv" ]; then
        print_step "Creating Python virtual environment..."
        python3 -m venv "$SCRIPT_DIR/.venv"
    fi
    
    # Install Python packages
    if [ -f "$SCRIPT_DIR/.venv/bin/pip" ]; then
        "$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    else
        pip3 install -r "$SCRIPT_DIR/requirements.txt"
    fi
    
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
Comment=A GUI application for managing VPN connections on Linux
Exec=$SCRIPT_DIR/main.py
Icon=$SCRIPT_DIR/assets/icon.png
Terminal=false
Categories=Network;System;Settings;
StartupWMClass=VPN Manager
EOF
    
    # Make desktop file executable
    chmod +x "$desktop_file"
    
    # Update desktop database
    if command_exists update-desktop-database; then
        update-desktop-database "$HOME/.local/share/applications"
    fi
    
    print_success "Desktop entry created at $desktop_file"
}

# Function to create systemd service (optional)
create_systemd_service() {
    print_step "Creating systemd service (optional)..."
    
    local service_file="/etc/systemd/system/vpn-manager.service"
    local install_dir="/opt/vpn-manager"
    
    # Check if we should install systemd service
    read -p "Install systemd service for automatic startup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping systemd service installation"
        return
    fi
    
    # Check if running as root for systemd installation
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Warning: systemd service installation requires root privileges${NC}"
        echo "Please run this script with sudo or install the service manually"
        return
    fi
    
    # Create installation directory
    mkdir -p "$install_dir"
    
    # Copy application files to installation directory
    cp -r "$SCRIPT_DIR"/{main.py,backend,frontend,assets,requirements.txt} "$install_dir/"
    
    # Copy the systemd service file
    if [ -f "$SCRIPT_DIR/vpn-manager.service" ]; then
        cp "$SCRIPT_DIR/vpn-manager.service" "$service_file"
    else
        # Fallback: create service file
        cat > "$service_file" <<EOF
[Unit]
Description=Linux VPN Manager
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $install_dir/main.py
WorkingDirectory=$install_dir
Restart=on-failure
RestartSec=5s
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/%i

# For systems with polkit or policykit
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%i/bus

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$install_dir /etc/vpn-manager /var/log/vpn-manager /run/user/%i

# Allow access to network configuration
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_SYS_ADMIN
AmbientCapabilities=CAP_NET_ADMIN

[Install]
WantedBy=multi-user.target
EOF
    fi
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable vpn-manager.service
    
    print_success "Systemd service installed and enabled"
    echo "To start the service, run: sudo systemctl start vpn-manager.service"
    echo "To check status, run: sudo systemctl status vpn-manager.service"
}

# Function to create uninstall script
create_uninstall_script() {
    print_step "Creating uninstall script..."
    
    cat > "$SCRIPT_DIR/uninstall.sh" <<'EOF'
#!/bin/bash

# VPN Manager - Uninstall Script

set -e

echo "Uninstalling VPN Manager..."

# Remove desktop entry
rm -f "$HOME/.local/share/applications/vpn-manager.desktop"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications"
fi

# Remove systemd service
if [ -f "/etc/systemd/system/vpn-manager.service" ]; then
    sudo systemctl stop vpn-manager.service 2>/dev/null || true
    sudo systemctl disable vpn-manager.service 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/vpn-manager.service"
    sudo systemctl daemon-reload
    echo "Systemd service removed"
fi

# Remove installation directory
if [ -d "/opt/vpn-manager" ]; then
    sudo rm -rf "/opt/vpn-manager"
    echo "Installation directory removed"
fi

# Remove user configuration
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
    echo "  1. From this directory: ./main.py"
    echo "  2. Or use the desktop entry: VPN Manager"
    echo ""
    echo "Configuration files:"
    echo "  - Connections: ~/.config/vpn-manager/connections.json"
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
    if ! command_exists python3; then
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
    if ! command_exists pip3 && ! command_exists pip; then
        print_error "pip is not installed"
        exit 1
    fi
    print_success "pip found"
    
    # Install system dependencies
    install_system_deps
    
    # Create assets
    create_assets
    
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
