#!/bin/bash

# PiCord Systemd Installer
# Sets up PiCord as a systemd service for automatic startup on boot

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the absolute path of the current directory
PICORD_DIR=$(pwd)
SERVICE_NAME="picord"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${GREEN}PiCord Systemd Installer${NC}"
echo -e "${BLUE}This will set up PiCord to start automatically on boot${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   echo -e "${YELLOW}Usage: sudo ./install_service.sh${NC}"
   exit 1
fi

# Check if we're in the PiCord directory
if [ ! -f "bot.py" ] || [ ! -f "run.sh" ]; then
    echo -e "${RED}Error: This script must be run from the PiCord directory${NC}"
    echo -e "${YELLOW}Please cd to the PiCord directory and run: sudo ./install_service.sh${NC}"
    exit 1
fi

# Create the systemd service file
echo -e "${YELLOW}Creating systemd service file...${NC}"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=PiCord Discord Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$(logname)
Group=$(logname)
WorkingDirectory=$PICORD_DIR
ExecStart=/bin/bash $PICORD_DIR/run.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=picord

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$PICORD_DIR

# Environment
HOME=/home/$(logname)

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Service file created at $SERVICE_FILE${NC}"

# Set proper permissions
chmod 644 "$SERVICE_FILE"

# Reload systemd to recognize the new service
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Enable the service to start on boot
echo -e "${YELLOW}Enabling PiCord service to start on boot...${NC}"
systemctl enable "$SERVICE_NAME"

# Check if service is already running and stop it before starting
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${YELLOW}Stopping existing PiCord service...${NC}"
    systemctl stop "$SERVICE_NAME"
fi

# Start the service
echo -e "${YELLOW}Starting PiCord service...${NC}"
systemctl start "$SERVICE_NAME"

# Wait a moment and check status
sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✅ PiCord service is now running!${NC}"
else
    echo -e "${RED}❌ Failed to start PiCord service${NC}"
    echo -e "${YELLOW}Check status with: systemctl status $SERVICE_NAME${NC}"
    echo -e "${YELLOW}Check logs with: journalctl -u $SERVICE_NAME${NC}"
    exit 1
fi

# Show service status
echo -e "${BLUE}Service status:${NC}"
systemctl status "$SERVICE_NAME" --no-pager -l

echo
echo -e "${GREEN}🎉 Installation complete!${NC}"
echo -e "${BLUE}PiCord is now set up as a systemd service and will start automatically on boot.${NC}"
echo
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  Start service:   sudo systemctl start $SERVICE_NAME"
echo -e "  Stop service:    sudo systemctl stop $SERVICE_NAME"
echo -e "  Restart service: sudo systemctl restart $SERVICE_NAME"
echo -e "  Check status:    sudo systemctl status $SERVICE_NAME"
echo -e "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo -e "  Disable boot:    sudo systemctl disable $SERVICE_NAME"
echo
echo -e "${YELLOW}To uninstall: sudo ./uninstall_service.sh${NC}"