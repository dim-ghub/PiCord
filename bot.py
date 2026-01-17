import asyncio
import json
import logging
import os
import subprocess
import sys
import socket
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

import discord
from discord.ext import tasks


class ResilientDiscordClient(discord.Client):
    """Custom Discord client with multi-gateway support"""
    
    def __init__(self, gateway_endpoints: list, **kwargs):
        super().__init__(**kwargs)
        self.gateway_endpoints = gateway_endpoints
        self.current_gateway_index = 0
    
    def get_next_gateway(self) -> str:
        """Get the next gateway URL to try"""
        gateway = self.gateway_endpoints[self.current_gateway_index]
        self.current_gateway_index = (self.current_gateway_index + 1) % len(self.gateway_endpoints)
        return f"wss://{gateway}/?v=10&encoding=json"


class PiCordBot:
    def __init__(self, config_path: str = "bot_config.json"):
        self.config_path = config_path
        self.config = self.load_config(config_path)
        
        self.gateway_endpoints = [
            "gateway-us-east1-c.discord.gg",
            "gateway-us-east1-b.discord.gg",
            "gateway-us-central1-a.discord.gg",
            "gateway-eu-west1-b.discord.gg"
        ]
        
        self.client = ResilientDiscordClient(self.gateway_endpoints)
        self.apps = {}
        self._config_mtime = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
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
    
    def load_token(self) -> Optional[str]:
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
                    await self.reload_apps_config()
                elif not hasattr(self, '_config_mtime'):
                    self._config_mtime = current_mtime
                
                # Check app configs
                for app_name, app_config in self.apps.items():
                    if hasattr(app_config, 'config') and 'config_file' in app_config.config:
                        app_config_path = app_config.config['config_file']
                        if Path(app_config_path).exists():
                            app_mtime = Path(app_config_path).stat().st_mtime
                            app_mtime_key = f'_{app_name}_config_mtime'
                            
                            if hasattr(self, app_mtime_key) and app_mtime != getattr(self, app_mtime_key):
                                self.logger.info(f"🔄 {app_name} config changed, reloading...")
                                app_config.feature_config = app_config.load_feature_config()
                                setattr(self, app_mtime_key, app_mtime)
                            elif not hasattr(self, app_mtime_key):
                                setattr(self, app_mtime_key, app_mtime)
                                
            except Exception as e:
                self.logger.error(f"Error in config watcher: {e}")
        
        config_watcher.start()
    
    async def reload_apps_config(self):
        """Reload all app configurations"""
        for app_name, app in self.apps.items():
            if hasattr(app, 'feature_config'):
                try:
                    app.feature_config = app.load_feature_config()
                    self.logger.info(f"✅ Reloaded {app_name} config")
                except Exception as e:
                    self.logger.error(f"❌ Failed to reload {app_name} config: {e}")
    
    async def on_ready(self):
        self.logger.info(f"Bot logged in as {self.client.user}")
        print(f"✅ {self.config['bot']['name']} logged in as {self.client.user}")
        self.setup_config_watcher()
        
        # Set bot status
        status_config = self.config.get("discord", {}).get("status", {})
        if status_config.get("type") == "idle":
            await self.client.change_presence(status=discord.Status.idle, afk=status_config.get("afk", False))
        
        # Load apps
        await self.load_apps()
        
        self.logger.info("✅ Bot started successfully!")
        print("✅ Bot is ready!")
    
    async def load_apps(self):
        apps_config = self.config.get("apps", {})
        
        for app_name, app_config in apps_config.items():
            if app_config.get("enabled", False):
                try:
                    if app_name == "autoboat":
                        from apps.autoboat import AutoBoatFeature
                        app = AutoBoatFeature(self.client, app_config)
                        await app.initialize()
                        self.apps[app_name] = app
                        self.logger.info(f"✅ Loaded app: {app_name}")
                    elif app_name == "ssh":
                        from apps.ssh import RunFeature
                        app = RunFeature(self.client, app_config)
                        await app.initialize()
                        self.apps[app_name] = app
                        self.logger.info(f"✅ Loaded app: {app_name}")
                    elif app_name == "settings":
                        from apps.settings import SettingsFeature
                        app = SettingsFeature(self.client, app_config)
                        await app.initialize()
                        self.apps[app_name] = app
                        self.logger.info(f"✅ Loaded app: {app_name}")
                    elif app_name == "updater":
                        from apps.updater import UpdaterFeature
                        app = UpdaterFeature(self.client, app_config)
                        await app.initialize()
                        self.apps[app_name] = app
                        self.logger.info(f"✅ Loaded app: {app_name}")
                    elif app_name == "panic":
                        from apps.panic import PanicFeature
                        app = PanicFeature(self.client, app_config)
                        await app.initialize()
                        self.apps[app_name] = app
                        self.logger.info(f"✅ Loaded app: {app_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load app {app_name}: {e}")
    
    async def send_message(self, message, content, silent=False):
        if silent or self.config['bot'].get('silent', False):
            await message.delete()
            return
        await message.channel.send(content, reference=message)

    async def handle_message(self, message):
        # First, check if this is terminal input for an active SSH session (only for bot user)
        # But only if it doesn't start with the bot prefix
        if (message.author == self.client.user and 
            "ssh" in self.apps and 
            not message.content.startswith(self.config["bot"]["prefix"])):
            ssh_feature = self.apps["ssh"]
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

        # Handle updater commands first
        if command == "update":
            if "updater" in self.apps:
                updater_app = self.apps["updater"]
                updater_app.current_channel = message.channel
                updater_app.override_channel = None
                await updater_app.handle_update_command(message)
            else:
                await self.send_message(message, "❌ Updater app not available")
        elif command == "status" and args and args[0].lower() == "git":
            if "updater" in self.apps:
                updater_app = self.apps["updater"]
                updater_app.current_channel = message.channel
                updater_app.override_channel = None
                await updater_app.handle_status_command(message)
            else:
                await self.send_message(message, "❌ Updater app not available")
        elif command == "start" and args:
            app_name = args[0].lower()
            if app_name in self.apps:
                try:
                    # Pass current channel to app for fallback
                    self.apps[app_name].current_channel = message.channel
                    
                    # Check if a channel ID was provided
                    if len(args) > 1:
                        try:
                            channel_id = int(args[1])
                            override_channel = self.client.get_channel(channel_id)
                            if override_channel:
                                self.apps[app_name].override_channel = override_channel
                                self.logger.info(f"Using channel override: {channel_id}")
                            else:
                                await self.send_message(message, f"⚠️ Could not find channel {channel_id}, using current channel")
                        except ValueError:
                            await self.send_message(message, f"⚠️ Invalid channel ID format, using current channel")
                    
                    await self.apps[app_name].start()
                    
                    # For SSH, also start a terminal session
                    if app_name == "ssh":
                        ssh_feature = self.apps[app_name]
                        await ssh_feature.start_terminal_session(message)
                    else:
                        await self.send_message(message, f"✅ Started {app_name} app!")
                except Exception as e:
                    await self.send_message(message, f"❌ Failed to start {app_name}: {e}")
            else:
                await self.send_message(message, f"❌ Unknown app: {app_name}")
        elif command == "stop" and args:
            app_name = args[0].lower()
            if app_name in self.apps:
                try:
                    await self.apps[app_name].stop()
                    await self.send_message(message, f"✅ Stopped {app_name} app!")
                except Exception as e:
                    await self.send_message(message, f"❌ Failed to stop {app_name}: {e}")
            else:
                await self.send_message(message, f"❌ Unknown app: {app_name}")
        elif command == "help":
            help_text = f"**{self.config['bot']['name']} Commands:**\n"
            help_text += f"`{prefix}update` - Update bot from git and restart\n"
            help_text += f"`{prefix}status git` - Check git status for updates\n"
            help_text += f"`{prefix}start <app> [channel_id]` - Start an app\n"
            help_text += f"`{prefix}stop <app>` - Stop an app\n"
            help_text += f"`{prefix}reload` - Reload configuration (auto-reloads on file change)\n"
            help_text += f"`{prefix}restart <app>` - Restart an app\n"
            help_text += f"`{prefix}panic` - 🚨 Immediately kill the bot process\n"
            help_text += f"`{prefix}help` - Show this help\n\n"
            help_text += "**Available apps:**\n"
            for app_name in self.apps.keys():
                help_text += f"- {app_name}\n"
            if "ssh" in self.apps:
                help_text += f"\n**SSH Terminal:** After starting with `{prefix}start ssh`, type commands without prefix"
            if "settings" in self.apps:
                help_text += f"\n**Settings:** Use `{prefix}setting list` or `{prefix}setting {{key}}={{value}}`"
                help_text += f"\n**App Settings:** Use `{prefix}setting-{{app}} list` or `{prefix}setting-{{app}} {{key}}={{value}}`"
            if "panic" in self.apps:
                help_text += f"\n⚠️ **Panic:** Use `{prefix}panic` to immediately kill the bot if needed"
            await self.send_message(message, help_text)
        elif command == "setting":
            # Handle settings commands
            if "settings" in self.apps:
                settings_feature = self.apps["settings"]
                await settings_feature.handle_settings_command(message, args, prefix)
            else:
                await self.send_message(message, "❌ Settings app not available")
        elif command.startswith("setting-"):
            # Handle app-specific settings commands
            if "settings" in self.apps:
                app_name = command[len("setting-"):].lower()
                settings_feature = self.apps["settings"]
                await settings_feature.handle_feature_settings_command(message, app_name, args, prefix)
            else:
                await self.send_message(message, "❌ Settings app not available")
        elif command == "reload":
            try:
                self.config = self.load_config(self.config_path)
                await self.reload_apps_config()
                await self.send_message(message, f"✅ Configuration reloaded successfully!")
                self.logger.info("🔄 Configuration manually reloaded")
            except Exception as e:
                await self.send_message(message, f"❌ Failed to reload config: {e}")
                self.logger.error(f"Failed to reload config: {e}")
        elif command == "restart":
            if args and args[0].lower() in self.apps:
                app_name = args[0].lower()
                try:
                    app = self.apps[app_name]
                    was_running = app.is_running if hasattr(app, 'is_running') else False
                    
                    if was_running:
                        await app.stop()
                        await asyncio.sleep(1)  # Brief pause
                    
                    await app.initialize()
                    
                    if was_running:
                        await app.start()
                    
                    await self.send_message(message, f"✅ Restarted {app_name} app!")
                    self.logger.info(f"🔄 Restarted {app_name} app")
                except Exception as e:
                    await self.send_message(message, f"❌ Failed to restart {app_name}: {e}")
            else:
                await self.send_message(message, f"❌ Unknown feature: {args[0] if args else 'none specified'}")
        elif command == "panic":
            if "panic" in self.apps:
                channel = message.channel
                await message.delete()  # Delete the panic command for safety
                await channel.send("🚨 **PANIC ACTIVATED** - Bot shutting down immediately!")
                panic_feature = self.apps["panic"]
                await panic_feature.panic()
            else:
                await self.send_message(message, "❌ Panic feature not available")
    
    def check_network_connectivity(self, host: str = "discord.com", port: int = 443, timeout: int = 5) -> bool:
        """Check if network connectivity to Discord is available"""
        try:
            socket.create_connection((host, port), timeout=timeout).close()
            return True
        except (socket.timeout, socket.error, OSError):
            return False
    
    def resolve_gateway_fallback(self, hostname: str) -> Optional[str]:
        """Resolve gateway hostname with multiple DNS fallback attempts"""
        for attempt in range(3):
            try:
                # Try system DNS first
                result = socket.gethostbyname(hostname)
                self.logger.info(f"Resolved {hostname} to {result} (attempt {attempt + 1})")
                return result
            except socket.gaierror:
                if attempt == 0:
                    # Try alternative DNS resolution methods
                    try:
                        # Try a different approach using subprocess to nslookup
                        result = subprocess.run(['nslookup', hostname], 
                                               capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            # Parse nslookup output for IP address
                            lines = result.stdout.split('\n')
                            for line in lines:
                                if 'Address:' in line and not line.startswith('Server:'):
                                    ip = line.split('Address:')[-1].strip()
                                    # Filter out invalid DNS server addresses like 127.0.0.53#53
                                    if ip and '.' in ip and not ip.startswith('127.0.0.') and not ip.startswith('::1'):
                                        self.logger.info(f"Resolved {hostname} to {ip} via nslookup")
                                        return ip
                    except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
                        self.logger.debug(f"Alternative DNS resolution failed: {e}")
                
                if attempt < 2:
                    self.logger.warning(f"DNS resolution attempt {attempt + 1} failed for {hostname}, retrying...")
                    time.sleep(1)
        
        self.logger.error(f"Failed to resolve {hostname} after 3 attempts")
        return None
    
    def exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        base_delay = 2.0
        max_delay = 300.0
        delay = min(base_delay ** attempt, max_delay)
        jitter = delay * 0.1 * (0.5 - (hash(str(attempt)) % 100) / 100)
        return delay + jitter
    
    def run(self):
        token = self.load_token()
        if not token:
            self.logger.error("Failed to load Discord token!")
            print("Error: Could not load Discord token. Please check your .env file.")
            sys.exit(1)
        
        self.logger.info("Starting bot...")
        
        # Enhanced connection handling with retries
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                # Check network connectivity first
                if not self.check_network_connectivity():
                    self.logger.error("Network connectivity check failed!")
                    delay = self.exponential_backoff(self.reconnect_attempts)
                    self.logger.info(f"Retrying connection in {delay:.1f} seconds...")
                    time.sleep(delay)
                    self.reconnect_attempts += 1
                    continue
                
                # Attempt to run the bot
                self.client.run(token)
                break
                
            except Exception as e:
                self.reconnect_attempts += 1
                self.logger.error(f"Connection attempt {self.reconnect_attempts} failed: {e}")
                
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    self.logger.error("Max reconnection attempts reached. Giving up.")
                    break
                
                delay = self.exponential_backoff(self.reconnect_attempts)
                self.logger.info(f"Retrying connection in {delay:.1f} seconds...")
                time.sleep(delay)


if __name__ == "__main__":
    bot = PiCordBot()
    bot.run()