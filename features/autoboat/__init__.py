import asyncio
import json
import logging
from asyncio import sleep
from datetime import datetime
from typing import Dict, Any, Optional

import discord
from discord import ApplicationCommandType, Client, Status, TextChannel
from discord.ext import tasks


class AutoBoatFeature:
    def __init__(self, client: Client, config: Dict[str, Any]):
        self.client = client
        self.config = config
        self.feature_config = self.load_feature_config()
        self.logger = logging.getLogger(f"{__name__}.AutoBoat")
        
        # Global variables for slash commands
        self.work_slash_cmd = None
        self.collect_slash_cmd = None
        self.deposit_slash_cmd = None
        
        # Task references
        self.auto_work_task = None
        self.auto_collect_task = None
        
        self.is_running = False
    
    def load_feature_config(self) -> Dict[str, Any]:
        config_path = self.config.get("config_file", "features/autoboat/config.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"AutoBoat config file {config_path} not found!")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in AutoBoat config: {e}")
            return {}
    
    async def initialize(self):
        """Initialize the AutoBoat feature"""
        self.logger.info("Initializing AutoBoat feature...")
        
        # If using slash commands, fetch the application commands
        if self.feature_config.get('bot', {}).get('prefix') == "/":
            await self.fetch_slash_commands()
    
    async def fetch_slash_commands(self):
        """Fetch slash commands from Discord"""
        self.logger.info("Fetching slash commands...")
        channel = self.client.get_channel(self.feature_config['discord']['channel_id'])
        
        if not channel or not isinstance(channel, TextChannel):
            self.logger.error("Could not access the specified channel!")
            return
        
        try:
            application_commands = await channel.application_commands()
            self.logger.info(f"Found {len(application_commands)} application commands")
            
            # Fetch commands by ID if specified in config, otherwise by name matching
            for command in application_commands:
                if command.type == ApplicationCommandType.chat_input:
                    # Match by ID first (more reliable)
                    if (self.feature_config['commands']['work']['slash_command_id'] and 
                        command.id == self.feature_config['commands']['work']['slash_command_id']):
                        self.work_slash_cmd = command
                        self.logger.info(f"Found work command by ID: {command.name}")
                    elif (self.feature_config['commands']['collect']['slash_command_id'] and 
                          command.id == self.feature_config['commands']['collect']['slash_command_id']):
                        self.collect_slash_cmd = command
                        self.logger.info(f"Found collect command by ID: {command.name}")
                    elif (self.feature_config['commands']['deposit']['slash_command_id'] and 
                          command.id == self.feature_config['commands']['deposit']['slash_command_id']):
                        self.deposit_slash_cmd = command
                        self.logger.info(f"Found deposit command by ID: {command.name}")
                    # Fallback to name matching if no IDs specified
                    elif (not self.feature_config['commands']['work']['slash_command_id'] and 
                          command.name.lower() == "work"):
                        self.work_slash_cmd = command
                        self.logger.info(f"Found work command by name: {command.name}")
                    elif (not self.feature_config['commands']['collect']['slash_command_id'] and 
                          command.name.lower() == "collect"):
                        self.collect_slash_cmd = command
                        self.logger.info(f"Found collect command by name: {command.name}")
                    elif (not self.feature_config['commands']['deposit']['slash_command_id'] and 
                          command.name.lower() == "deposit"):
                        self.deposit_slash_cmd = command
                        self.logger.info(f"Found deposit command by name: {command.name}")
            
            if not self.work_slash_cmd:
                self.logger.warning("Work slash command not found!")
            if (self.feature_config['commands']['collect']['enabled'] and 
                not self.collect_slash_cmd):
                self.logger.warning("Collect slash command not found!")
            if not self.deposit_slash_cmd:
                self.logger.warning("Deposit slash command not found!")
                
        except Exception as e:
            self.logger.error(f"Failed to fetch application commands: {e}")
    
    async def start(self):
        """Start the AutoBoat automation"""
        if self.is_running:
            self.logger.warning("AutoBoat is already running!")
            return
        
        self.logger.info("Starting AutoBoat feature...")
        
        # Countdown before starting
        countdown = self.feature_config['timing']['startup_countdown_seconds']
        self.logger.info(f"Starting automation in {countdown} seconds...")
        
        for i in range(countdown, 0, -1):
            self.logger.info(f"{i}...")
            await sleep(1)
        
        # Start the automation tasks
        self.auto_work_task = tasks.loop(
            minutes=self.feature_config['commands']['work']['cooldown_minutes']
        )(self.auto_work)
        self.auto_work_task.start()
        self.logger.info("Started work automation")
        
        # Start collect automation if enabled
        if self.feature_config['commands']['collect']['enabled']:
            self.auto_collect_task = tasks.loop(
                minutes=self.feature_config['commands']['collect']['cooldown_minutes']
            )(self.auto_collect)
            self.auto_collect_task.start()
            self.logger.info("Started collect automation")
        
        self.is_running = True
        self.logger.info("✅ AutoBoat automation started successfully!")
    
    async def stop(self):
        """Stop the AutoBoat automation"""
        if not self.is_running:
            self.logger.warning("AutoBoat is not running!")
            return
        
        self.logger.info("Stopping AutoBoat feature...")
        
        if self.auto_work_task:
            self.auto_work_task.cancel()
            self.logger.info("Stopped work automation")
        
        if self.auto_collect_task:
            self.auto_collect_task.cancel()
            self.logger.info("Stopped collect automation")
        
        self.is_running = False
        self.logger.info("✅ AutoBoat automation stopped successfully!")
    
    async def auto_work(self):
        """Automated work task"""
        try:
            channel = self.client.get_channel(self.feature_config['discord']['channel_id'])
            if not channel or not isinstance(channel, TextChannel):
                return
            
            prefix = self.feature_config['bot']['prefix']
            
            if prefix == "/":
                # Use slash commands
                if self.work_slash_cmd:
                    self.logger.info("Running work slash command")
                    try:
                        await self.work_slash_cmd.__call__(channel=channel)
                        self.logger.info(f"Work slash command executed, waiting {self.feature_config['timing']['response_wait_seconds']} seconds for response")
                        await sleep(self.feature_config['timing']['response_wait_seconds'])
                        await self.deposit(channel)
                    except Exception as e:
                        self.logger.error(f"Failed to execute work slash command: {e}")
                else:
                    self.logger.error("Work slash command not found!")
            else:
                # Use prefix commands
                command = self.feature_config['commands']['work']['command']
                message = f"{prefix} {command}"
                
                self.logger.info(f"Running work command: {message}")
                try:
                    await channel.send(message)
                    self.logger.info(f"Work command sent, waiting {self.feature_config['timing']['response_wait_seconds']} seconds for response")
                    
                    await sleep(self.feature_config['timing']['response_wait_seconds'])
                    await self.deposit(channel)
                except Exception as e:
                    self.logger.error(f"Failed to send work command: {e}")
        except Exception as e:
            self.logger.error(f"Error in auto_work task: {e}")
    
    async def auto_collect(self):
        """Automated collect task"""
        try:
            channel = self.client.get_channel(self.feature_config['discord']['channel_id'])
            if not channel or not isinstance(channel, TextChannel):
                return
            
            prefix = self.feature_config['bot']['prefix']
            
            if prefix == "/":
                # Use slash commands
                if self.collect_slash_cmd:
                    self.logger.info("Running collect slash command")
                    await sleep(2)  # Wait a few seconds for safety
                    try:
                        await self.collect_slash_cmd.__call__(channel=channel)
                        self.logger.info(f"Collect slash command executed, waiting {self.feature_config['timing']['response_wait_seconds']} seconds for response")
                        await sleep(self.feature_config['timing']['response_wait_seconds'])
                        await self.deposit(channel)
                    except Exception as e:
                        self.logger.error(f"Failed to execute collect slash command: {e}")
                else:
                    self.logger.error("Collect slash command not found!")
            else:
                # Use prefix commands
                command = self.feature_config['commands']['collect']['command']
                message = f"{prefix} {command}"
                
                self.logger.info(f"Running collect command: {message}")
                try:
                    await channel.send(message)
                    self.logger.info(f"Collect command sent, waiting {self.feature_config['timing']['response_wait_seconds']} seconds for response")
                    
                    await sleep(self.feature_config['timing']['response_wait_seconds'])
                    await self.deposit(channel)
                except Exception as e:
                    self.logger.error(f"Failed to send collect command: {e}")
        except Exception as e:
            self.logger.error(f"Error in auto_collect task: {e}")
    
    async def deposit(self, channel: TextChannel):
        """Deposit earnings"""
        if not isinstance(channel, TextChannel):
            return
        
        prefix = self.feature_config['bot']['prefix']
        
        if prefix == "/":
            # Use slash commands
            if self.deposit_slash_cmd:
                await sleep(self.feature_config['timing']['deposit_wait_seconds'])
                self.logger.info("Running deposit slash command")
                try:
                    await self.deposit_slash_cmd.__call__(channel=channel, amount="all")
                    self.logger.info("Deposit slash command executed successfully")
                except Exception as e:
                    self.logger.error(f"Failed to execute deposit slash command: {e}")
            else:
                self.logger.error("Deposit slash command not found!")
        else:
            # Use prefix commands
            await sleep(self.feature_config['timing']['deposit_wait_seconds'])
            message = f"{prefix} deposit all"
            
            self.logger.info(f"Running deposit command: {message}")
            try:
                await channel.send(message)
                self.logger.info("Deposit command sent successfully")
            except Exception as e:
                self.logger.error(f"Failed to send deposit command: {e}")