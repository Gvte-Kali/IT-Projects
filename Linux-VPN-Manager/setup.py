#!/usr/bin/env python3
"""
VPN Manager - Setup Script

This script is used to install VPN Manager as a Python package.
"""

from setuptools import setup, find_packages
import os

# Read version from file
VERSION = "1.0.0"

# Read requirements
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read long description from README
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="linux-vpn-manager",
    version=VERSION,
    description="A cross-distribution GUI application for managing VPN connections on Linux",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LinuxVPNManager Team",
    author_email="",
    url="https://github.com/Gvte-Kali/IT-Projects/tree/main/Linux-VPN-Manager",
    packages=find_packages(),
    package_data={
        "linux_vpn_manager": ["assets/*"],
    },
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "vpn-manager=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Security",
        "Topic :: System :: Networking",
        "Environment :: X11 Applications :: Qt",
    ],
    keywords="vpn openvpn wireguard linux gui qt",
    project_urls={
        "Bug Reports": "https://github.com/Gvte-Kali/IT-Projects/issues",
        "Source": "https://github.com/Gvte-Kali/IT-Projects/tree/main/Linux-VPN-Manager",
    },
)
