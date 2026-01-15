import asyncio
import json
import logging
import subprocess
import os
from typing import Dict, Any, Optional

import discord
from discord import TextChannel


class RunFeature:
    def __init__(self, client: discord.Client, config: Dict[str, Any]):
        self.client = client
        self.config = config
        self.feature_config = self.load_feature_config()
        self.logger = logging.getLogger(f"{__name__}.Run")
        self.is_running = False
        
        # Terminal sessions management
        self.terminal_sessions = {}  # user_id -> session info
        self.first_command_processed = set()  # Track users whose first command was processed
        self.ssh_message_ids = set()  # Track SSH command message IDs to exclude from terminal processing
        
    def load_feature_config(self) -> Dict[str, Any]:
        config_path = self.config.get("config_file", "features/run/config.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Run config file {config_path} not found!")
            return {"timeout": 30}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in Run config: {e}")
            return {"timeout": 30}
    
    async def initialize(self):
        """Initialize the SSH feature"""
        self.logger.info("Initializing SSH feature...")
    
    async def start(self):
        """Start the SSH feature"""
        self.logger.info("SSH feature started - ready for terminal sessions")
        self.is_running = True
    
    def add_ssh_message_id(self, message_id: int):
        """Add SSH message ID to exclusion list"""
        self.ssh_message_ids.add(message_id)
        # Clean up old SSH message IDs (keep only last 50)
        if len(self.ssh_message_ids) > 50:
            old_ids = list(self.ssh_message_ids)[:-50]
            for old_id in old_ids:
                self.ssh_message_ids.discard(old_id)
    
    def get_bash_prompt(self, username: str, hostname: str, cwd: str) -> str:
        """Generate a realistic bash prompt"""
        # Get the shortened home directory
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        
        return f"[{username}@{hostname} {cwd}]$ "
    
    async def start_terminal_session(self, message: discord.Message) -> bool:
        """Start a new fake terminal session"""
        user_id = str(message.author.id)
        
        # Clean up any existing session for this user
        
        # Clean up any existing session for this user
        if user_id in self.terminal_sessions:
            await self.end_terminal_session(user_id)
        
        try:
            # Initialize session state
            username = os.environ.get('USER', os.environ.get('USERNAME', 'user'))
            hostname = os.environ.get('HOSTNAME', 'localhost')
            cwd = os.getcwd()
            
            # Store session info
            self.terminal_sessions[user_id] = {
                'username': username,
                'hostname': hostname,
                'cwd': cwd,
                'channel_id': message.channel.id,
                'created_at': asyncio.get_event_loop().time()
            }
            
            # Create initial terminal message as a reply
            prompt = self.get_bash_prompt(username, hostname, cwd)
            terminal_msg = await message.reply(
                "**🖥️ Terminal Session Started**\n"
                "Type commands normally. Type `exit` to end the session.\n"
                "```\n" +
                prompt +
                "```"
            )
            
            self.terminal_sessions[user_id]['message_id'] = terminal_msg.id
            self.terminal_sessions[user_id]['terminal_msg'] = terminal_msg
            
            self.logger.info(f"Started SSH terminal session for user {user_id}")
            return True
            
        except Exception as e:
            await message.channel.send(f"❌ Failed to start terminal session: {str(e)}")
            self.logger.error(f"Failed to start terminal session: {e}")
            return False
    
    async def end_terminal_session(self, user_id: str):
        """End a terminal session"""
        if user_id not in self.terminal_sessions:
            return
        
        try:
            session = self.terminal_sessions[user_id]
            
            # Update the message to show session ended
            if 'terminal_msg' in session:
                try:
                    await session['terminal_msg'].edit(content="**🖥️ Terminal Session Ended**")
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error ending terminal session: {e}")
        
        # Remove session data and reset first command tracking
        del self.terminal_sessions[user_id]
        self.first_command_processed.discard(user_id)
        
        self.logger.info(f"Ended SSH terminal session for user {user_id}")
    
    async def execute_command(self, message: discord.Message, command: str, session: dict) -> str:
        """Execute a single command and return the output"""
        timeout = self.feature_config.get("timeout", 30)
        
        try:
            # Check if command is allowed (basic security)
            allowed_commands = self.feature_config.get("allowed_commands", [])
            if allowed_commands and "*" not in allowed_commands:
                cmd_parts = command.split()
                if cmd_parts and cmd_parts[0] not in allowed_commands:
                    return f"❌ Command `{cmd_parts[0]}` is not allowed!"
            
            # Handle special commands
            if command.strip().lower() == 'exit':
                return "exit"
            
            # Handle cd command specially to preserve working directory
            if command.strip().startswith('cd '):
                return self.handle_cd_command(command, session)
            
            self.logger.info(f"Executing subprocess command: '{command}' in cwd: {session['cwd']}")
            
            # Execute command in the current working directory
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=session['cwd'],
                timeout=timeout
            )
            
            self.logger.info(f"Subprocess result: returncode={result.returncode}, stdout_len={len(result.stdout or '')}, stderr_len={len(result.stderr or '')}")
            
            # Prepare the output
            if result.returncode == 0:
                output = result.stdout.strip()
                if not output:
                    output = ""  # No output
                else:
                    # Clean up ANSI escape codes for cleaner display
                    import re
                    output = re.sub(r'\x1b\[[0-9;]*m', '', output)
            else:
                output = result.stderr.strip()
                if not output:
                    output = f"Command failed with exit code {result.returncode}"
                else:
                    output = f"❌ {output}"
            
            return output
            
        except subprocess.TimeoutExpired:
            timeout = self.feature_config.get("timeout", 30)
            return f"❌ Command timed out after {timeout} seconds"
        except Exception as e:
            self.logger.error(f"Exception in execute_command: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return f"❌ Error executing command: {str(e)}"
    
    def handle_cd_command(self, command: str, session: dict) -> str:
        """Handle cd command to update working directory"""
        try:
            # Parse the cd command
            parts = command.strip().split(maxsplit=1)
            if len(parts) < 2:
                # cd with no argument - go to home directory
                target_dir = os.path.expanduser("~")
            else:
                target_dir = parts[1]
            
            # Handle ~ expansion
            if target_dir.startswith('~'):
                target_dir = os.path.expanduser(target_dir)
            
            # Handle relative paths
            if not os.path.isabs(target_dir):
                target_dir = os.path.join(session['cwd'], target_dir)
            
            # Normalize the path
            target_dir = os.path.abspath(target_dir)
            
            # Check if directory exists
            if os.path.isdir(target_dir):
                session['cwd'] = target_dir
                return ""  # No output for successful cd
            else:
                return f"bash: cd: {target_dir}: No such file or directory"
                
        except Exception as e:
            return f"bash: cd: {str(e)}"
    
    async def handle_terminal_input(self, message: discord.Message) -> bool:
        """Handle input for an active terminal session"""
        user_id = str(message.author.id)
        
        if user_id not in self.terminal_sessions:
            return False
        
        # Skip SSH command messages completely
        if message.id in self.ssh_message_ids:
            self.logger.info(f"Skipping SSH message {message.id}")
            return True
        
        command = message.content
        
        try:
            # Skip SSH command messages completely
            if message.id in self.ssh_message_ids:
                self.logger.info(f"Skipping SSH message {message.id}")
                return True
            
            # Show command in terminal
            if user_id not in self.terminal_sessions:
                return False
            
            session = self.terminal_sessions.get(user_id)
            if not session:
                return False
                
            prompt = self.get_bash_prompt(session['username'], session['hostname'], session['cwd'])
            terminal_content = f"**🖥️ Terminal**\n```\n{prompt}{command}\n"
            
            # Execute command
            output = await self.execute_command(message, command, session)
            
            # Check for exit command
            if output == "exit":
                await self.end_terminal_session(user_id)
                # Don't delete the exit message
                return True
            
            # Add output to terminal display
            if output:
                terminal_content += output + "\n"
            
            # Add new prompt
            new_prompt = self.get_bash_prompt(session['username'], session['hostname'], session['cwd'])
            terminal_content += new_prompt + "```"
            
            # Update the terminal message
            if 'terminal_msg' in session:
                try:
                    await session['terminal_msg'].edit(content=terminal_content)
                except (discord.NotFound, discord.HTTPException) as e:
                    # Message was deleted or can't be edited, create a new one
                    try:
                        new_msg = await message.channel.send(terminal_content)
                        session['terminal_msg'] = new_msg
                        session['message_id'] = new_msg.id
                    except discord.HTTPException:
                        # If even that fails, just log it and continue
                        self.logger.error(f"Failed to update terminal message: {e}")
            
            # Skip deleting the first command of each session, delete exit, delete all others
            is_first_command = user_id not in self.first_command_processed
            is_exit_command = command.strip().lower() == 'exit'
            
            if not is_first_command and not is_exit_command:
                try:
                    await message.delete()
                except (discord.NotFound, discord.HTTPException) as e:
                    self.logger.debug(f"Failed to delete message {message.id}: {e}")
            
            # Mark that we've processed the first command
            if is_first_command:
                self.first_command_processed.add(user_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling terminal input: {e}")
            return False
    
