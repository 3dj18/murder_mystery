import os
import discord
from dotenv import load_dotenv

from game_setup.game_setup_utils import (
    yaml_to_dict,
    generate_players,
    find_closest_name,
    get_alive_player_names,
    get_healers,
    get_killers
)

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

MURDERERS_CHANNEL_ID = int(os.getenv("MURDERERS_CHANNEL_ID"))
HEALERS_CHANNEL_ID = int(os.getenv("HEALERS_CHANNEL_ID"))
ALL_PLAYERS_CHANNEL_ID = int(os.getenv("ALL_PLAYERS_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

players = []
round_number = 1

round_actions = {
    "kills": [],
    "heals": []
}

