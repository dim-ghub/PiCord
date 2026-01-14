import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

import discord
from discord.ext import tasks


class RaspberryBot:
    def __init__(self, config_path: str = "bot_config.json"):
        self.config = self.load_config(config_path)
        self.client = discord.Client()
        self.features = {}
        self.setup_logging()
        self.setup_events()
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file {config_path} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            sys.exit(1)
    
    def setup_logging(self):
        log_config = self.config.get("logging", {})
        level = getattr(logging, log_config.get("level", "INFO"))
        
        handlers = []
        if log_config.get("file"):
            handlers.append(logging.FileHandler(log_config["file"], mode='w'))
        if log_config.get("console", True):
            handlers.append(logging.StreamHandler())
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        self.logger = logging.getLogger(__name__)
    
    def load_token(self) -> str:
        token_file = self.config["discord"]["token_file"]
        try:
            with open(token_file, 'r') as f:
                for line in f:
                    if line.startswith('TOKEN='):
                        return line.split('=', 1)[1].strip()
        except FileNotFoundError:
            self.logger.error(f"Token file {token_file} not found!")
            return None
        return None
    
    def setup_events(self):
        @self.client.event
        async def on_ready():
            await self.on_ready()
        
        @self.client.event
        async def on_message(message):
            await self.handle_message(message)
    
    async def on_ready(self):
        self.logger.info(f"Bot logged in as {self.client.user}")
        print(f"✅ {self.config['bot']['name']} logged in as {self.client.user}")
        
        # Set bot status
        status_config = self.config.get("discord", {}).get("status", {})
        if status_config.get("type") == "idle":
            await self.client.change_presence(status=discord.Status.idle, afk=status_config.get("afk", False))
        
        # Load features
        await self.load_features()
        
        self.logger.info("✅ Bot started successfully!")
        print("✅ Bot is ready!")
    
    async def load_features(self):
        features_config = self.config.get("features", {})
        
        for feature_name, feature_config in features_config.items():
            if feature_config.get("enabled", False):
                try:
                    if feature_name == "autoboat":
                        from features.autoboat import AutoBoatFeature
                        feature = AutoBoatFeature(self.client, feature_config)
                        await feature.initialize()
                        self.features[feature_name] = feature
                        self.logger.info(f"✅ Loaded feature: {feature_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load feature {feature_name}: {e}")
    
    async def handle_message(self, message):
        if message.author == self.client.user:
            return
        
        prefix = self.config["bot"]["prefix"]
        if not message.content.startswith(prefix):
            return
        
        content = message.content[len(prefix):].strip()
        parts = content.split()
        
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if command == "start" and args:
            feature_name = args[0].lower()
            if feature_name in self.features:
                try:
                    await self.features[feature_name].start()
                    await message.reply(f"✅ Started {feature_name} feature!")
                except Exception as e:
                    await message.reply(f"❌ Failed to start {feature_name}: {e}")
            else:
                await message.reply(f"❌ Unknown feature: {feature_name}")
        elif command == "stop" and args:
            feature_name = args[0].lower()
            if feature_name in self.features:
                try:
                    await self.features[feature_name].stop()
                    await message.reply(f"✅ Stopped {feature_name} feature!")
                except Exception as e:
                    await message.reply(f"❌ Failed to stop {feature_name}: {e}")
            else:
                await message.reply(f"❌ Unknown feature: {feature_name}")
        elif command == "help":
            help_text = f"**{self.config['bot']['name']} Commands:**\n"
            help_text += f"`{prefix}start <feature>` - Start a feature\n"
            help_text += f"`{prefix}stop <feature>` - Stop a feature\n"
            help_text += f"`{prefix}help` - Show this help\n\n"
            help_text += "**Available features:**\n"
            for feature_name in self.features.keys():
                help_text += f"- {feature_name}\n"
            await message.reply(help_text)
    
    def run(self):
        token = self.load_token()
        if not token:
            self.logger.error("Failed to load Discord token!")
            print("Error: Could not load Discord token. Please check your .env file.")
            sys.exit(1)
        
        self.logger.info("Starting bot...")
        self.client.run(token)


if __name__ == "__main__":
    bot = RaspberryBot()
    bot.run()