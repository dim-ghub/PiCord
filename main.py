from asyncio import sleep
import os

from discord import Client, TextChannel
from discord.ext import tasks

# This bot automatically starts when run and stops when exited

work_wait_time = 4  # Time in minutes between running the work command. Default: 421

target_channel_id = 1457866346858545234


@tasks.loop(minutes=work_wait_time)
async def auto_work():
    channel = client.get_channel(target_channel_id)
    if channel:
        await channel.send("u.u work")  # Run the work command
        await sleep(5)  # Wait for response
        await deposit(channel)  # Deposit your newly earned money





async def deposit(channel):
    await sleep(5)  # Wait 5 seconds for safety
    await channel.send("u.u deposit all")  # Run the deposit command


def load_token():
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('TOKEN='):
                return line.split('=', 1)[1].strip()
    return "TOKEN"

client = Client()  # Define client session


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")  # Let the user know that its running
    
    # 5 second countdown before starting
    print("Starting bot in 5 seconds...")
    for i in range(5, 0, -1):
        print(f"{i}...")
        await sleep(1)
    
    # Start the automation tasks
    auto_work.start()  # Starts work automation
    print("✅ Bot automation started!")


client.run(load_token())
