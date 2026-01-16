#!/bin/bash

# PiCord Systemd Uninstaller
# Removes the systemd service and cleans up

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="picord"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${GREEN}PiCord Systemd Uninstaller${NC}"
echo -e "${BLUE}This will remove the PiCord systemd service${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   echo -e "${YELLOW}Usage: sudo ./uninstall_service.sh${NC}"
   exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}⚠️  PiCord service file not found at $SERVICE_FILE${NC}"
    echo -e "${BLUE}Service may not be installed or was already removed${NC}"
    exit 0
fi

# Stop the service if it's running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${YELLOW}Stopping PiCord service...${NC}"
    systemctl stop "$SERVICE_NAME"
fi

# Disable the service
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${YELLOW}Disabling PiCord service...${NC}"
    systemctl disable "$SERVICE_NAME"
fi

# Remove the service file
echo -e "${YELLOW}Removing service file...${NC}"
rm "$SERVICE_FILE"

# Reload systemd to recognize the removal
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload

echo -e "${GREEN}✅ PiCord service has been successfully removed!${NC}"
echo
echo -e "${BLUE}The bot will no longer start automatically on boot.${NC}"
echo -e "${YELLOW}To run the bot manually, use: ./run.sh${NC}"
echo
echo -e "${YELLOW}To reinstall: sudo ./install_service.sh${NC}"