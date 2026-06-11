import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN= os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(e)

    print(f"✅ Logged in as {bot.user}")
    
async def load_cogs():
    await bot.load_extension("cogs.economy")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())
