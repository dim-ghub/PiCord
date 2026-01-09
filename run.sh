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

# Install dependencies only if not installed (using venv's python and pip)
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! python -c "import discord" 2>/dev/null; then
    echo -e "${YELLOW}Installing discord.py-self...${NC}"
    pip install -U git+https://github.com/dolfies/discord.py-self.git
else
    echo -e "${GREEN}✅ discord.py-self already installed${NC}"
fi

if ! python -c "import aiohttp" 2>/dev/null; then
    echo -e "${YELLOW}Installing aiohttp...${NC}"
    pip install -U aiohttp[speedups]
else
    echo -e "${GREEN}✅ aiohttp already installed${NC}"
fi

echo -e "${GREEN}✅ Dependencies ready${NC}"

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: main.py not found!${NC}"
    exit 1
fi

# Check if config.json exists, create default if not
if [ ! -f "config.json" ]; then
    echo -e "${YELLOW}⚠️  config.json not found, creating default configuration${NC}"
    # The default config.json will be created by git checkout or user can copy it
fi

# Check if .env file exists and has token, prompt for input if needed
if [ ! -f ".env" ] || [ ! -s ".env" ]; then
    echo -e "${YELLOW}⚠️  Discord token not found in .env file${NC}"
    echo -e "${BLUE}Please enter your Discord token:${NC}"
    read -s -p "Token: " DISCORD_TOKEN
    echo
    
    if [ -z "$DISCORD_TOKEN" ]; then
        echo -e "${RED}Error: No token provided!${NC}"
        exit 1
    fi
    
    # Create or update .env file with user input
    echo "TOKEN=$DISCORD_TOKEN" > .env
    echo -e "${GREEN}✅ Token saved to .env file successfully${NC}"
else
    echo -e "${GREEN}✅ Token already configured in .env${NC}"
fi

# Check if config.json is properly configured
if [ -f "config.json" ]; then
    echo -e "${GREEN}✅ Configuration file found${NC}"
else
    echo -e "${YELLOW}⚠️  Make sure config.json exists and is configured properly${NC}"
fi

# Run the bot
echo -e "${GREEN}Starting the bot...${NC}"
python main.py

# Deactivate virtual environment when done
deactivate