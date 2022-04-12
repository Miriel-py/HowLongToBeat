# bot.py
"""Main bot file that instances and runs the bot and loads the extensions"""

import os

import discord
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DEBUG_MODE = True if os.getenv('DEBUG_MODE') == 'ON' else False


OWNER_ID = 619879176316649482
DEV_GUILDS = [730115558766411857,812650049565753355] # Secret Valley, Charivari


intents = discord.Intents.none()

if DEBUG_MODE:
    bot = commands.Bot(help_command=None, case_insensitive=True, intents=intents,
                       debug_guilds=DEV_GUILDS, owner_id=OWNER_ID)
else:
    bot = commands.Bot(help_command=None, case_insensitive=True, intents=intents,
                       owner_id=OWNER_ID)


EXTENSIONS = [
    'cogs.main',
]
if __name__ == '__main__':
    for extension in EXTENSIONS:
        bot.load_extension(extension)


bot.run(TOKEN)