from asyncio import sleep
import json
import os
import logging
from datetime import datetime

from discord import Client, TextChannel
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
    if channel:
        prefix = config['bot']['prefix']
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
        if channel:
            prefix = config['bot']['prefix']
            command = config['commands']['collect']['command']
            message = f"{prefix} {command}"
            
            logger.info(f"Running collect command: {message}")
            await channel.send(message)
            logger.info(f"Collect command sent, waiting {config['timing']['response_wait_seconds']} seconds for response")
            
            await sleep(config['timing']['response_wait_seconds'])  # Wait for response
            await deposit(channel)  # Deposit your newly earned money





async def deposit(channel):
    await sleep(config['timing']['deposit_wait_seconds'])  # Wait for safety seconds
    prefix = config['bot']['prefix']
    message = f"{prefix} deposit all"
    
    logger.info(f"Running deposit command: {message}")
    await channel.send(message)
    logger.info("Deposit command sent successfully")


client = Client()  # Define client session

client = Client()  # Define client session


@client.event
async def on_ready():
    logger.info(f"Bot logged in as {client.user}")
    print(f"We have logged in as {client.user}")  # Let the user know that its running
    
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
