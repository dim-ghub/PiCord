#!/bin/bash

# PiCord Runner Script
# Optimized for Discord automation with proper virtual environment setup

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting PiCord...${NC}"

# Check if running on Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model)
    if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
        echo -e "${BLUE}🍓 Detected Raspberry Pi: $MODEL${NC}"
        # Set Raspberry Pi specific optimizations
        export PYTHONOPTIMIZE=1
        export GEVENT_MONKEY_PATCH=1
    fi
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created successfully${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if dependencies are already installed
DEPS_INSTALLED=false
if pip list 2>/dev/null | grep -q discord.py-self; then
    echo -e "${GREEN}✅ Dependencies already installed${NC}"
    DEPS_INSTALLED=true
fi

# Install/upgrade dependencies only if needed
if [ "$DEPS_INSTALLED" = false ]; then
    # Upgrade pip for better performance
    echo -e "${YELLOW}Upgrading pip...${NC}"
    pip install --upgrade pip
    
    # Install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
fi

# Check if bot.py exists
if [ ! -f "bot.py" ]; then
    echo -e "${RED}Error: bot.py not found!${NC}"
    exit 1
fi

# Check if bot_config.json exists
if [ ! -f "bot_config.json" ]; then
    echo -e "${RED}Error: bot_config.json not found!${NC}"
    exit 1
fi

# Check if .env file exists and has valid token, prompt for input if needed
TOKEN_VALID=false

if [ -f ".env" ] && [ -s ".env" ]; then
    # Extract token from .env file
    DISCORD_TOKEN=$(grep "^TOKEN=" .env | cut -d'=' -f2- | tr -d '\n' | tr -d '\r')
    
    # Check if token is not empty and looks valid (basic length check)
    if [ -n "$DISCORD_TOKEN" ] && [ ${#DISCORD_TOKEN} -gt 50 ]; then
        echo -e "${GREEN}✅ Token already configured in .env${NC}"
        TOKEN_VALID=true
    else
        echo -e "${YELLOW}⚠️  Invalid or empty token found in .env${NC}"
    fi
fi

if [ "$TOKEN_VALID" = false ]; then
    echo -e "${YELLOW}⚠️  Discord token not found or invalid${NC}"
    echo -e "${BLUE}Please enter your Discord token:${NC}"
    read -s -p "Token: " DISCORD_TOKEN
    echo
    
    if [ -z "$DISCORD_TOKEN" ]; then
        echo -e "${RED}Error: No token provided!${NC}"
        exit 1
    fi
    
    # Basic token validation
    if [ ${#DISCORD_TOKEN} -lt 50 ]; then
        echo -e "${RED}Error: Token appears to be too short (should be 50+ characters)${NC}"
        echo -e "${YELLOW}Please make sure you're using a valid Discord bot token${NC}"
        exit 1
    fi
    
    # Create or update .env file with user input
    echo "TOKEN=$DISCORD_TOKEN" > .env
    echo -e "${GREEN}✅ Token saved to .env file successfully${NC}"
fi

# Check if AutoBoat config exists
if [ ! -f "features/autoboat/config.json" ]; then
    echo -e "${YELLOW}⚠️  AutoBoat config not found, please configure features/autoboat/config.json${NC}"
fi

# Run the bot
echo -e "${GREEN}Starting PiCord...${NC}"
python bot.py

# Deactivate virtual environment when done
deactivate