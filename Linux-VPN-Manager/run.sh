#!/bin/bash

# VPN Manager - Run Script
# ==========================
# Simple script to run VPN Manager

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Run the application
cd "$SCRIPT_DIR"
PYTHONPATH="$SCRIPT_DIR/src" python3 vpn_manager.py
