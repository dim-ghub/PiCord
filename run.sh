#!/bin/bash

# UnbelievaBoat-AUTO Runner Script
# This script sets up and runs the bot using Python virtual environment

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting UnbelievaBoat-AUTO...${NC}"

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

# Install/upgrade dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -U --force-reinstall git+https://github.com/dolfies/discord.py-self.git
pip install -U aiohttp[speedups]
echo -e "${GREEN}✅ Dependencies installed successfully${NC}"

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: main.py not found!${NC}"
    exit 1
fi

# Check if TOKEN is configured and prompt for input if needed
if grep -q '"TOKEN"' main.py; then
    echo -e "${YELLOW}⚠️  Discord token not found in main.py${NC}"
    echo -e "${BLUE}Please enter your Discord token:${NC}"
    read -s -p "Token: " DISCORD_TOKEN
    echo
    
    if [ -z "$DISCORD_TOKEN" ]; then
        echo -e "${RED}Error: No token provided!${NC}"
        exit 1
    fi
    
    # Replace TOKEN in main.py with user input
    sed -i "s/\"TOKEN\"/\"$DISCORD_TOKEN\"/" main.py
    echo -e "${GREEN}✅ Token configured successfully${NC}"
else
    echo -e "${GREEN}✅ Token already configured${NC}"
fi

# Run the bot
echo -e "${GREEN}Starting the bot...${NC}"
python main.py

# Deactivate virtual environment when done
deactivate