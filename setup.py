#!/usr/bin/env python3
"""
UnbelievaBoat-AUTO Setup Script
Creates virtual environment and installs dependencies
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error {description}: {e.stderr}")
        return False

def main():
    print("🚀 Setting up UnbelievaBoat-AUTO...")
    
    # Create virtual environment if it doesn't exist
    if not os.path.exists("venv"):
        if not run_command("python3 -m venv venv", "Creating virtual environment"):
            sys.exit(1)
    else:
        print("✅ Virtual environment already exists")
    
    # Install dependencies
    commands = [
        "source venv/bin/activate && pip install -U --force-reinstall git+https://github.com/dolfies/discord.py-self.git",
        "source venv/bin/activate && pip install -U aiohttp[speedups]"
    ]
    
    descriptions = [
        "Installing discord.py-self",
        "Installing aiohttp with speedups"
    ]
    
    for cmd, desc in zip(commands, descriptions):
        if not run_command(cmd, desc):
            sys.exit(1)
    
    print("✅ Setup completed successfully!")
    print("📝 Next steps:")
    print("   1. Replace 'TOKEN' in main.py with your Discord token")
    print("   2. Run './run.sh' to start the bot")

if __name__ == "__main__":
    main()