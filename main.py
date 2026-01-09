from asyncio import sleep
import json
import os

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


@tasks.loop(minutes=config['commands']['work']['cooldown_minutes'])
async def auto_work():
    channel = client.get_channel(config['discord']['channel_id'])
    if channel:
        prefix = config['bot']['prefix']
        command = config['commands']['work']['command']
        await channel.send(f"{prefix} {command}")  # Run the work command
        await sleep(config['timing']['response_wait_seconds'])  # Wait for response
        await deposit(channel)  # Deposit your newly earned money


if config['commands']['collect']['enabled']:
    @tasks.loop(minutes=config['commands']['collect']['cooldown_minutes'])
    async def auto_collect():
        channel = client.get_channel(config['discord']['channel_id'])
        if channel:
            prefix = config['bot']['prefix']
            command = config['commands']['collect']['command']
            await channel.send(f"{prefix} {command}")  # Run the collect command
            await sleep(config['timing']['response_wait_seconds'])  # Wait for response
            await deposit(channel)  # Deposit your newly earned money





async def deposit(channel):
    await sleep(config['timing']['deposit_wait_seconds'])  # Wait for safety seconds
    prefix = config['bot']['prefix']
    await channel.send(f"{prefix} deposit all")  # Run the deposit command


client = Client()  # Define client session

client = Client()  # Define client session


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")  # Let the user know that its running
    
    # Countdown before starting
    countdown = config['timing']['startup_countdown_seconds']
    print(f"Starting bot in {countdown} seconds...")
    for i in range(countdown, 0, -1):
        print(f"{i}...")
        await sleep(1)
    
    # Start the automation tasks
    auto_work.start()  # Starts work automation
    
    # Start collect automation if enabled
    if config['commands']['collect']['enabled']:
        auto_collect.start()  # Starts collect automation
    
    print("✅ Bot automation started!")


client.run(load_token())
