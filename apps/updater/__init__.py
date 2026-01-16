import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
from typing import Dict, Any

import discord
from discord import Message


class UpdaterFeature:
    def __init__(self, client: discord.Client, config: Dict[str, Any]):
        self.client = client
        self.config = config
        self.feature_config = self.load_feature_config()
        self.logger = logging.getLogger(f"{__name__}.Updater")
        
        # Channel settings
        self.current_channel = None  # Fallback channel from command
        self.override_channel = None  # Explicit channel override
        
        self.is_running = False
    
    def load_feature_config(self) -> Dict[str, Any]:
        config_path = self.config.get("config_file", "apps/updater/config.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Updater config file {config_path} not found!")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in Updater config: {e}")
            return {}
    
    async def initialize(self):
        """Initialize Updater feature"""
        self.logger.info("Initializing Updater feature...")
    
    async def start(self):
        """Start Updater feature"""
        if self.is_running:
            self.logger.warning("Updater feature is already running!")
            return
        
        self.logger.info("Updater feature started")
        self.is_running = True
    
    async def stop(self):
        """Stop Updater feature"""
        if not self.is_running:
            self.logger.warning("Updater feature is not running!")
            return
        
        self.logger.info("Stopping Updater feature...")
        self.is_running = False
    
    async def handle_update_command(self, message: Message) -> bool:
        """Handle the update command"""
        try:
            # Check if we're in the right directory
            picord_dir = os.path.expanduser("~/PiCord")
            if not os.path.exists(picord_dir):
                await message.reply("❌ PiCord directory not found at ~/PiCord")
                return True
            
            await message.reply("🔄 Starting update process...")
            self.logger.info("Starting update process")
            
            # Change to PiCord directory
            original_dir = os.getcwd()
            os.chdir(picord_dir)
            
            try:
                # Perform git pull
                self.logger.info("Running git pull...")
                result = subprocess.run(
                    ["git", "pull"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    self.logger.info(f"Git pull successful: {result.stdout}")
                    await message.reply("✅ Code updated successfully!")
                    
                    # Check if there were any changes
                    if "Already up to date." in result.stdout:
                        await message.reply("ℹ️ No changes found - already up to date.")
                        return True
                    else:
                        await message.reply("🔄 Restarting bot to apply changes...")
                        await self.restart_bot(message)
                else:
                    self.logger.error(f"Git pull failed: {result.stderr}")
                    await message.reply(f"❌ Update failed: {result.stderr}")
                    return True
                    
            except subprocess.TimeoutExpired:
                await message.reply("❌ Update timed out after 30 seconds")
                self.logger.error("Git pull timed out")
                return True
            except Exception as e:
                await message.reply(f"❌ Update error: {str(e)}")
                self.logger.error(f"Update error: {e}")
                return True
            finally:
                # Restore original directory
                os.chdir(original_dir)
                
        except Exception as e:
            await message.reply(f"❌ Update process failed: {str(e)}")
            self.logger.error(f"Update process failed: {e}")
            return True
        
        return True
    
    async def restart_bot(self, message: Message):
        """Restart the bot script"""
        try:
            await message.reply("🔄 Killing current process and restarting...")
            
            # Get the current script path
            script_path = os.path.expanduser("~/PiCord/run.sh")
            
            # Give a moment for the message to be sent
            await asyncio.sleep(2)
            
            # Kill the current process and restart
            # Use os.execv to replace the current process
            try:
                # First, try to find the bot's process ID and kill it
                import psutil
                
                # Find our own process
                current_process = psutil.Process()
                parent_process = current_process.parent()
                
                if parent_process:
                    self.logger.info(f"Killing parent process {parent_process.pid}")
                    parent_process.kill()
                else:
                    self.logger.info("No parent process found, killing current process")
                    current_process.kill()
                
                # Start the new process
                self.logger.info(f"Starting new bot process: {script_path}")
                subprocess.Popen([script_path], cwd=os.path.expanduser("~/PiCord"))
                
            except ImportError:
                # Fallback if psutil is not available
                self.logger.info("psutil not available, using os.execv")
                os.execv("/bin/bash", ["/bin/bash", script_path])
                
        except Exception as e:
            self.logger.error(f"Failed to restart bot: {e}")
            if not self.is_bot_dying():
                await message.reply(f"❌ Failed to restart: {str(e)}")
    
    def is_bot_dying(self) -> bool:
        """Check if the bot is in the process of shutting down"""
        try:
            # Simple check - if we can't import modules we're probably dying
            import discord
            return True
        except:
            return False
    
    async def handle_status_command(self, message: Message) -> bool:
        """Handle the status command to check for updates"""
        try:
            picord_dir = os.path.expanduser("~/PiCord")
            original_dir = os.getcwd()
            os.chdir(picord_dir)
            
            try:
                # Check git status
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    if result.stdout.strip():
                        await message.reply("⚠️ Local changes detected. Please commit or stash changes before updating.")
                    else:
                        await message.reply("✅ Working directory is clean. Ready for updates.")
                
                # Check current branch and remote status
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    current_branch = result.stdout.strip()
                    
                    result = subprocess.run(
                        ["git", "log", "--oneline", "origin/main..HEAD", "--max-count=1"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        await message.reply(f"📤 Local commits ahead of remote on branch `{current_branch}`")
                    else:
                        result = subprocess.run(
                            ["git", "log", "--oneline", "HEAD..origin/main", "--max-count=1"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if result.returncode == 0 and result.stdout.strip():
                            await message.reply(f"📥 Remote updates available on branch `{current_branch}`")
                        else:
                            await message.reply(f"✅ Up to date on branch `{current_branch}`")
                            
            finally:
                os.chdir(original_dir)
                
        except Exception as e:
            await message.reply(f"❌ Status check failed: {str(e)}")
            self.logger.error(f"Status check failed: {e}")
        
        return True