import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

import discord
from discord.ext import tasks


class PiCordBot:
    def __init__(self, config_path: str = "bot_config.json"):
        self.config_path = config_path
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
    
    def setup_config_watcher(self):
        """Setup file watcher for config hot reloading"""
        @tasks.loop(seconds=5)
        async def config_watcher():
            try:
                # Check main config
                current_mtime = Path(self.config_path).stat().st_mtime
                if hasattr(self, '_config_mtime') and current_mtime != self._config_mtime:
                    self.logger.info("🔄 Main config changed, reloading...")
                    self.config = self.load_config(self.config_path)
                    self._config_mtime = current_mtime
                    await self.reload_features_config()
                elif not hasattr(self, '_config_mtime'):
                    self._config_mtime = current_mtime
                
                # Check feature configs
                for feature_name, feature_config in self.features.items():
                    if hasattr(feature_config, 'config') and 'config_file' in feature_config.config:
                        feature_config_path = feature_config.config['config_file']
                        if Path(feature_config_path).exists():
                            feature_mtime = Path(feature_config_path).stat().st_mtime
                            feature_mtime_key = f'_{feature_name}_config_mtime'
                            
                            if hasattr(self, feature_mtime_key) and feature_mtime != getattr(self, feature_mtime_key):
                                self.logger.info(f"🔄 {feature_name} config changed, reloading...")
                                feature_config.feature_config = feature_config.load_feature_config()
                                setattr(self, feature_mtime_key, feature_mtime)
                            elif not hasattr(self, feature_mtime_key):
                                setattr(self, feature_mtime_key, feature_mtime)
                                
            except Exception as e:
                self.logger.error(f"Error in config watcher: {e}")
        
        config_watcher.start()
    
    async def reload_features_config(self):
        """Reload all feature configurations"""
        for feature_name, feature in self.features.items():
            if hasattr(feature, 'feature_config'):
                try:
                    feature.feature_config = feature.load_feature_config()
                    self.logger.info(f"✅ Reloaded {feature_name} config")
                except Exception as e:
                    self.logger.error(f"❌ Failed to reload {feature_name} config: {e}")
    
    async def on_ready(self):
        self.logger.info(f"Bot logged in as {self.client.user}")
        print(f"✅ {self.config['bot']['name']} logged in as {self.client.user}")
        self.setup_config_watcher()
        
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
                    elif feature_name == "ssh":
                        from features.ssh import RunFeature
                        feature = RunFeature(self.client, feature_config)
                        await feature.initialize()
                        self.features[feature_name] = feature
                        self.logger.info(f"✅ Loaded feature: {feature_name}")
                    elif feature_name == "settings":
                        from features.settings import SettingsFeature
                        feature = SettingsFeature(self.client, feature_config)
                        await feature.initialize()
                        self.features[feature_name] = feature
                        self.logger.info(f"✅ Loaded feature: {feature_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load feature {feature_name}: {e}")
    
    async def send_message(self, message, content, silent=False):
        if silent or self.config['bot'].get('silent', False):
            await message.delete()
            return
        await message.channel.send(content, reference=message)

    async def handle_message(self, message):
        # First, check if this is terminal input for an active SSH session (only for bot user)
        # But only if it doesn't start with the bot prefix
        if (message.author == self.client.user and 
            "ssh" in self.features and 
            not message.content.startswith(self.config["bot"]["prefix"])):
            ssh_feature = self.features["ssh"]
            terminal_handled = await ssh_feature.handle_terminal_input(message)
            if terminal_handled:
                return  # Message was handled by SSH terminal, don't process as bot command
        
        # For discord.py-self (user accounts), process messages from self
        # For regular bots, ignore self messages
        if message.author != self.client.user:
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
                    # Pass current channel to feature for fallback
                    self.features[feature_name].current_channel = message.channel
                    
                    # Check if a channel ID was provided
                    if len(args) > 1:
                        try:
                            channel_id = int(args[1])
                            override_channel = self.client.get_channel(channel_id)
                            if override_channel:
                                self.features[feature_name].override_channel = override_channel
                                self.logger.info(f"Using channel override: {channel_id}")
                            else:
                                await self.send_message(message, f"⚠️ Could not find channel {channel_id}, using current channel")
                        except ValueError:
                            await self.send_message(message, f"⚠️ Invalid channel ID format, using current channel")
                    
                    await self.features[feature_name].start()
                    
                    # For SSH, also start a terminal session
                    if feature_name == "ssh":
                        ssh_feature = self.features[feature_name]
                        await ssh_feature.start_terminal_session(message)
                    else:
                        await self.send_message(message, f"✅ Started {feature_name} feature!")
                except Exception as e:
                    await self.send_message(message, f"❌ Failed to start {feature_name}: {e}")
            else:
                await self.send_message(message, f"❌ Unknown feature: {feature_name}")
        elif command == "stop" and args:
            feature_name = args[0].lower()
            if feature_name in self.features:
                try:
                    await self.features[feature_name].stop()
                    await self.send_message(message, f"✅ Stopped {feature_name} feature!")
                except Exception as e:
                    await self.send_message(message, f"❌ Failed to stop {feature_name}: {e}")
            else:
                await self.send_message(message, f"❌ Unknown feature: {feature_name}")
        elif command == "help":
            help_text = f"**{self.config['bot']['name']} Commands:**\n"
            help_text += f"`{prefix}start <feature> [channel_id]` - Start a feature\n"
            help_text += f"`{prefix}stop <feature>` - Stop a feature\n"
            help_text += f"`{prefix}reload` - Reload configuration (auto-reloads on file change)\n"
            help_text += f"`{prefix}restart <feature>` - Restart a feature\n"
            help_text += f"`{prefix}help` - Show this help\n\n"
            help_text += "**Available features:**\n"
            for feature_name in self.features.keys():
                help_text += f"- {feature_name}\n"
            if "ssh" in self.features:
                help_text += "\n**SSH Terminal:** After starting with `.pc start ssh`, type commands without prefix"
            if "settings" in self.features:
                help_text += "\n**Settings:** Use `.pc setting list` or `.pc setting {key}={value}`"
            await self.send_message(message, help_text)
        elif command == "setting":
            # Handle settings commands
            if "settings" in self.features:
                settings_feature = self.features["settings"]
                await settings_feature.handle_settings_command(message, args)
            else:
                await self.send_message(message, "❌ Settings feature not available")
        elif command == "reload":
            try:
                self.config = self.load_config(self.config_path)
                await self.reload_features_config()
                await self.send_message(message, f"✅ Configuration reloaded successfully!")
                self.logger.info("🔄 Configuration manually reloaded")
            except Exception as e:
                await self.send_message(message, f"❌ Failed to reload config: {e}")
                self.logger.error(f"Failed to reload config: {e}")
        elif command == "restart":
            if args and args[0].lower() in self.features:
                feature_name = args[0].lower()
                try:
                    feature = self.features[feature_name]
                    was_running = feature.is_running if hasattr(feature, 'is_running') else False
                    
                    if was_running:
                        await feature.stop()
                        await asyncio.sleep(1)  # Brief pause
                    
                    await feature.initialize()
                    
                    if was_running:
                        await feature.start()
                    
                    await self.send_message(message, f"✅ Restarted {feature_name} feature!")
                    self.logger.info(f"🔄 Restarted {feature_name} feature")
                except Exception as e:
                    await self.send_message(message, f"❌ Failed to restart {feature_name}: {e}")
            else:
                await self.send_message(message, f"❌ Unknown feature: {args[0] if args else 'none specified'}")
    
    def run(self):
        token = self.load_token()
        if not token:
            self.logger.error("Failed to load Discord token!")
            print("Error: Could not load Discord token. Please check your .env file.")
            sys.exit(1)
        
        self.logger.info("Starting bot...")
        self.client.run(token)


if __name__ == "__main__":
    bot = PiCordBot()
    bot.run()