import json
import logging
from typing import Dict, Any, Optional

import discord
from discord import Message


class SettingsFeature:
    def __init__(self, client: discord.Client, config: Dict[str, Any]):
        self.client = client
        self.config = config
        self.feature_config = self.load_feature_config()
        self.logger = logging.getLogger(f"{__name__}.Settings")
        self.is_running = False
        self.bot_config_path = "bot_config.json"
    
    def load_feature_config(self) -> Dict[str, Any]:
        config_path = self.config.get("config_file", "features/settings/config.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Settings config file {config_path} not found!")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in Settings config: {e}")
            return {}
    
    async def initialize(self):
        """Initialize the Settings feature"""
        self.logger.info("Initializing Settings feature...")
    
    async def start(self):
        """Start the Settings feature"""
        if self.is_running:
            self.logger.warning("Settings feature is already running!")
            return
        
        self.logger.info("Settings feature started")
        self.is_running = True
    
    async def stop(self):
        """Stop the Settings feature"""
        if not self.is_running:
            self.logger.warning("Settings feature is not running!")
            return
        
        self.logger.info("Stopping Settings feature...")
        self.is_running = False
    
    def load_bot_config(self) -> Dict[str, Any]:
        """Load the main bot configuration"""
        try:
            with open(self.bot_config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Bot config file {self.bot_config_path} not found!")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in bot config: {e}")
            return {}
    
    def save_bot_config(self, config: Dict[str, Any]) -> bool:
        """Save the main bot configuration"""
        try:
            with open(self.bot_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save bot config: {e}")
            return False
    
    def get_setting_value(self, config: Dict[str, Any], path: str) -> Any:
        """Get a setting value using dot notation (e.g., 'bot.prefix')"""
        keys = path.split('.')
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def set_setting_value(self, config: Dict[str, Any], path: str, value: Any) -> bool:
        """Set a setting value using dot notation (e.g., 'bot.prefix')"""
        keys = path.split('.')
        current = config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                return False
            current = current[key]
        
        # Set the final value
        final_key = keys[-1]
        current[final_key] = value
        return True
    
    def list_all_settings(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """List all available settings with their current values and descriptions"""
        settings = {}
        
        # Bot settings
        settings.update({
            "bot.prefix": str(config.get("bot", {}).get("prefix", ".pc ")),
            "bot.name": str(config.get("bot", {}).get("name", "PiCord")),
            "bot.version": str(config.get("bot", {}).get("version", "1.0.0")),
            "bot.silent": str(config.get("bot", {}).get("silent", False)),
        })
        
        # Discord settings
        discord_settings = config.get("discord", {})
        settings.update({
            "discord.token_file": str(discord_settings.get("token_file", ".env")),
            "discord.status.type": str(discord_settings.get("status", {}).get("type", "online")),
            "discord.status.afk": str(discord_settings.get("status", {}).get("afk", False)),
        })
        
        # Logging settings
        logging_settings = config.get("logging", {})
        settings.update({
            "logging.level": str(logging_settings.get("level", "INFO")),
            "logging.file": str(logging_settings.get("file", "bot.log")),
            "logging.console": str(logging_settings.get("console", True)),
        })
        
        # Feature enablement settings
        features = config.get("features", {})
        for feature_name, feature_config in features.items():
            settings[f"features.{feature_name}.enabled"] = str(feature_config.get("enabled", False))
            if "config_file" in feature_config:
                settings[f"features.{feature_name}.config_file"] = str(feature_config["config_file"])
        
        return settings
    
    async def handle_settings_command(self, message: Message, args: list) -> bool:
        """Handle settings commands"""
        if not args:
            return False
        
        subcommand = args[0].lower()
        
        if subcommand == "list":
            config = self.load_bot_config()
            settings = self.list_all_settings(config)
            
            response = "**🔧 Bot Settings:**\n"
            response += "Format: `{setting}={current_value}`\n\n"
            
            for setting_path, value in sorted(settings.items()):
                response += f"`{setting_path}` = `{value}`\n"
            
            response += "\n**Usage:** `.pc setting {setting}={new_value}`"
            response += "\n**Feature settings:** `.pc setting-{feature} list` or `.pc setting-{feature} {key}={value}`"
            
            await message.reply(response)
            return True
        
        elif '=' in subcommand:
            # Parse setting=value format
            try:
                setting_path, value = subcommand.split('=', 1)
                setting_path = setting_path.strip()
                value = value.strip()
                
                # Load current config
                config = self.load_bot_config()
                if not config:
                    await message.reply("❌ Failed to load bot configuration!")
                    return True
                
                # Get current value for comparison
                current_value = self.get_setting_value(config, setting_path)
                
                # Parse the value to appropriate type
                parsed_value = self.parse_setting_value(value, current_value)
                
                # Set the new value
                if self.set_setting_value(config, setting_path, parsed_value):
                    if self.save_bot_config(config):
                        self.logger.info(f"Setting changed: {setting_path} = {parsed_value}")
                        await message.reply(f"✅ Updated `{setting_path}` = `{parsed_value}`")
                    else:
                        await message.reply("❌ Failed to save configuration!")
                else:
                    await message.reply(f"❌ Invalid setting path: `{setting_path}`")
                
                return True
                
            except ValueError:
                await message.reply("❌ Invalid format! Use: `{setting}={value}`")
                return True
        
        else:
            await message.reply("❌ Unknown command! Use `list` or `{setting}={value}` format")
            return True
    
    async def handle_feature_settings_command(self, message: Message, feature_name: str, args: list) -> bool:
        """Handle feature-specific settings commands"""
        # Check if feature exists and is enabled
        main_config = self.load_bot_config()
        features_config = main_config.get("features", {})
        
        if feature_name not in features_config:
            await message.reply(f"❌ Feature `{feature_name}` not found in configuration!")
            return True
        
        feature_config = features_config[feature_name]
        if not feature_config.get("enabled", False):
            await message.reply(f"❌ Feature `{feature_name}` is not enabled!")
            return True
        
        config_file = feature_config.get("config_file")
        if not config_file:
            await message.reply(f"❌ Feature `{feature_name}` has no config file configured!")
            return True
        
        # Load feature config
        feature_settings = self.load_feature_config_file(config_file)
        if not feature_settings:
            await message.reply(f"❌ Failed to load config file for `{feature_name}`!")
            return True
        
        if not args:
            await message.reply(f"❌ Missing subcommand! Use `list` or `{{key}}={{value}}`")
            return True
        
        subcommand = args[0].lower()
        
        if subcommand == "list":
            response = f"**🔧 {feature_name.title()} Feature Settings:**\n"
            response += f"Config file: `{config_file}`\n"
            response += "Format: `{setting}={current_value}`\n\n"
            
            def flatten_dict(d, parent_key='', sep='.'):
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key, sep=sep).items())
                    else:
                        items.append((new_key, v))
                return dict(items)
            
            flat_settings = flatten_dict(feature_settings)
            
            for setting_path, value in sorted(flat_settings.items()):
                response += f"`{setting_path}` = `{value}`\n"
            
            response += f"\n**Usage:** `.pc setting-{feature_name} {{setting}}={{new_value}}`"
            
            await message.reply(response)
            return True
        
        elif '=' in subcommand:
            # Parse setting=value format
            try:
                setting_path, value = subcommand.split('=', 1)
                setting_path = setting_path.strip()
                value = value.strip()
                
                # Get current value for comparison
                current_value = self.get_setting_value(feature_settings, setting_path)
                
                # Parse the value to appropriate type
                parsed_value = self.parse_setting_value(value, current_value)
                
                # Set the new value
                if self.set_setting_value(feature_settings, setting_path, parsed_value):
                    if self.save_feature_config_file(config_file, feature_settings):
                        self.logger.info(f"Feature {feature_name} setting changed: {setting_path} = {parsed_value}")
                        await message.reply(f"✅ Updated `{feature_name}.{setting_path}` = `{parsed_value}`")
                    else:
                        await message.reply(f"❌ Failed to save {feature_name} configuration!")
                else:
                    await message.reply(f"❌ Invalid setting path: `{setting_path}` in {feature_name}")
                
                return True
                
            except ValueError:
                await message.reply("❌ Invalid format! Use: `{setting}={value}`")
                return True
        
        else:
            await message.reply("❌ Unknown command! Use `list` or `{setting}={value}` format")
            return True
    
    def load_feature_config_file(self, config_file: str) -> Dict[str, Any]:
        """Load a feature's configuration file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Feature config file {config_file} not found!")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in feature config {config_file}: {e}")
            return {}
    
    def save_feature_config_file(self, config_file: str, config: Dict[str, Any]) -> bool:
        """Save a feature's configuration file"""
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save feature config {config_file}: {e}")
            return False
    
    def parse_setting_value(self, value: str, current_value: Any) -> Any:
        """Parse a string value to the appropriate type based on current value"""
        if current_value is None:
            # If no current value, try to infer type
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            elif value.isdigit():
                return int(value)
            elif value.replace('.', '').isdigit():
                return float(value)
            else:
                return value
        
        # Convert based on current value type
        if isinstance(current_value, bool):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(current_value, int):
            return int(value)
        elif isinstance(current_value, float):
            return float(value)
        else:
            return value