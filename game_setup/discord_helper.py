import os
import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

CHANNEL_IDS = {
    "all": int(os.getenv("ALL_PLAYERS_CHANNEL_ID")),
    "murder": int(os.getenv("MURDERERS_CHANNEL_ID")),
    "healer": int(os.getenv("HEALERS_CHANNEL_ID")),
}

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


async def send_message(channel_key: str, message: str):
    channel_id = CHANNEL_IDS[channel_key]
    channel = client.get_channel(channel_id)

    if channel is None:
        channel = await client.fetch_channel(channel_id)

    await channel.send(message)


def is_from_channel(message: discord.Message, channel_key: str) -> bool:
    return message.channel.id == CHANNEL_IDS[channel_key]

async def send_to_channel(channel_id: int, message: str):
    channel = client.get_channel(channel_id)

    if channel is None:
        channel = await client.fetch_channel(channel_id)

    await channel.send(message)

async def create_private_channel(
    guild: discord.Guild,
    channel_name: str,
    allowed_members: list[discord.Member],
    bot_member: discord.Member,
):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
    }

    for member in allowed_members:
        overwrites[member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )

    channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        reason="Create private murder mystery channel",
    )

    return channel