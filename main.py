from asyncio import sleep
import json
import os
import logging
from datetime import datetime

from discord import (ApplicationCommandType, Client, Status, TextChannel)
from discord.ext import tasks

# This bot automatically starts when run and stops when exited

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def load_token():
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('TOKEN='):
                return line.split('=', 1)[1].strip()
    return None

config = load_config()

# Global variables for slash commands
work_slash_cmd = None
collect_slash_cmd = None
deposit_slash_cmd = None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@tasks.loop(minutes=config['commands']['work']['cooldown_minutes'])
async def auto_work():
    channel = client.get_channel(config['discord']['channel_id'])
    if channel and isinstance(channel, TextChannel):
        prefix = config['bot']['prefix']
        
        if prefix == "/":
            # Use slash commands
            if work_slash_cmd:
                logger.info(f"Running work slash command")
                await work_slash_cmd.__call__(channel=channel)
                logger.info(f"Work slash command executed, waiting {config['timing']['response_wait_seconds']} seconds for response")
                await sleep(config['timing']['response_wait_seconds'])  # Wait for response
                await deposit(channel)  # Deposit your newly earned money
            else:
                logger.error("Work slash command not found!")
        else:
            # Use prefix commands
            command = config['commands']['work']['command']
            message = f"{prefix} {command}"
            
            logger.info(f"Running work command: {message}")
            await channel.send(message)
            logger.info(f"Work command sent, waiting {config['timing']['response_wait_seconds']} seconds for response")
            
            await sleep(config['timing']['response_wait_seconds'])  # Wait for response
            await deposit(channel)  # Deposit your newly earned money


if config['commands']['collect']['enabled']:
    @tasks.loop(minutes=config['commands']['collect']['cooldown_minutes'])
    async def auto_collect():
        channel = client.get_channel(config['discord']['channel_id'])
        if channel and isinstance(channel, TextChannel):
            prefix = config['bot']['prefix']
            
            if prefix == "/":
                # Use slash commands
                if collect_slash_cmd:
                    logger.info(f"Running collect slash command")
                    await sleep(2)  # Wait a few seconds for safety
                    await collect_slash_cmd.__call__(channel=channel)
                    logger.info(f"Collect slash command executed, waiting {config['timing']['response_wait_seconds']} seconds for response")
                    await sleep(config['timing']['response_wait_seconds'])  # Wait for response
                    await deposit(channel)  # Deposit your newly earned money
                else:
                    logger.error("Collect slash command not found!")
            else:
                # Use prefix commands
                command = config['commands']['collect']['command']
                message = f"{prefix} {command}"
                
                logger.info(f"Running collect command: {message}")
                await channel.send(message)
                logger.info(f"Collect command sent, waiting {config['timing']['response_wait_seconds']} seconds for response")
                
                await sleep(config['timing']['response_wait_seconds'])  # Wait for response
                await deposit(channel)  # Deposit your newly earned money





async def deposit(channel):
    if not isinstance(channel, TextChannel):
        return
        
    prefix = config['bot']['prefix']
    
    if prefix == "/":
        # Use slash commands
        if deposit_slash_cmd:
            await sleep(config['timing']['deposit_wait_seconds'])  # Wait for safety seconds
            logger.info(f"Running deposit slash command")
            await deposit_slash_cmd.__call__(channel=channel, amount="all")
            logger.info("Deposit slash command executed successfully")
        else:
            logger.error("Deposit slash command not found!")
    else:
        # Use prefix commands
        await sleep(config['timing']['deposit_wait_seconds'])  # Wait for safety seconds
        message = f"{prefix} deposit all"
        
        logger.info(f"Running deposit command: {message}")
        await channel.send(message)
        logger.info("Deposit command sent successfully")


client = Client()  # Define client session

client = Client()  # Define client session


@client.event
async def on_ready():
    global work_slash_cmd, collect_slash_cmd, deposit_slash_cmd
    
    # Set bot status to idle and afk=True
    today_date = datetime.today()
    await client.change_presence(status=Status.idle,
                                  afk=True,
                                  idle_since=datetime(today_date.year, today_date.month, today_date.day))
    
    logger.info(f"Bot logged in as {client.user}")
    print(f"We have logged in as {client.user}")  # Let the user know that its running
    
    prefix = config['bot']['prefix']
    
    # If using slash commands, fetch the application commands
    if prefix == "/":
        logger.info("Using slash commands - fetching application commands...")
        channel = client.get_channel(config['discord']['channel_id'])
        if channel and isinstance(channel, TextChannel):
            try:
                application_commands = await channel.application_commands()
                logger.info(f"Found {len(application_commands)} application commands")
                
                # Fetch commands by ID if specified in config, otherwise by name matching
                for command in application_commands:
                    if command.type == ApplicationCommandType.chat_input:
                        # Match by ID first (more reliable)
                        if (config['commands']['work']['slash_command_id'] and 
                            command.id == config['commands']['work']['slash_command_id']):
                            work_slash_cmd = command
                            logger.info(f"Found work command by ID: {command.name}")
                        elif (config['commands']['collect']['slash_command_id'] and 
                              command.id == config['commands']['collect']['slash_command_id']):
                            collect_slash_cmd = command
                            logger.info(f"Found collect command by ID: {command.name}")
                        elif (config['commands']['deposit']['slash_command_id'] and 
                              command.id == config['commands']['deposit']['slash_command_id']):
                            deposit_slash_cmd = command
                            logger.info(f"Found deposit command by ID: {command.name}")
                        # Fallback to name matching if no IDs specified
                        elif not config['commands']['work']['slash_command_id'] and command.name.lower() == "work":
                            work_slash_cmd = command
                            logger.info(f"Found work command by name: {command.name}")
                        elif not config['commands']['collect']['slash_command_id'] and command.name.lower() == "collect":
                            collect_slash_cmd = command
                            logger.info(f"Found collect command by name: {command.name}")
                        elif not config['commands']['deposit']['slash_command_id'] and command.name.lower() == "deposit":
                            deposit_slash_cmd = command
                            logger.info(f"Found deposit command by name: {command.name}")
                
                if not work_slash_cmd:
                    logger.warning("Work slash command not found!")
                if config['commands']['collect']['enabled'] and not collect_slash_cmd:
                    logger.warning("Collect slash command not found!")
                if not deposit_slash_cmd:
                    logger.warning("Deposit slash command not found!")
                    
            except Exception as e:
                logger.error(f"Failed to fetch application commands: {e}")
        else:
            logger.error("Could not access the specified channel!")
    
    # Countdown before starting
    countdown = config['timing']['startup_countdown_seconds']
    logger.info(f"Starting automation in {countdown} seconds...")
    print(f"Starting bot in {countdown} seconds...")
    for i in range(countdown, 0, -1):
        print(f"{i}...")
        await sleep(1)
    
    # Start the automation tasks
    logger.info("Starting work automation...")
    auto_work.start()  # Starts work automation
    
    # Start collect automation if enabled
    if config['commands']['collect']['enabled']:
        logger.info("Starting collect automation...")
        auto_collect.start()  # Starts collect automation
    
    logger.info("✅ Bot automation started successfully!")
    print("✅ Bot automation started!")


token = load_token()
if not token:
    logger.error("Failed to load token from .env file")
    print("Error: Could not load Discord token. Please check your .env file.")
    exit(1)

logger.info("Starting Discord bot...")
client.run(token)
