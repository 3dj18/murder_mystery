from game_setup.discord_helper import client, TOKEN, send_message, is_from_channel, create_private_channel
from game_setup.game_setup_utils import yaml_to_dict, generate_players, find_closest_name, get_alive_player_names, get_healers, get_killers

import os
import discord
from dotenv import load_dotenv

from collections import Counter
import random


load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# MURDERERS_CHANNEL_ID = int(os.getenv("MURDERERS_CHANNEL_ID"))
# HEALERS_CHANNEL_ID = int(os.getenv("HEALERS_CHANNEL_ID"))
ALL_PLAYERS_CHANNEL_ID = int(os.getenv("ALL_PLAYERS_CHANNEL_ID"))
KILLERS_CHANNEL = None
KILLERS_CHANNEL_ID = 0
HEALERS_CHANNEL = None
HEALERS_CHANNEL_ID = 0

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

players = []
round_number = 1

round_actions = {
    "kills": [],
    "heals": [],
    "murder_tie": None    # list of tied target names
}



def get_player_by_name(name: str):
    for player in players:
        if player.name == name:
            return player
    return None


async def send_to_channel(channel_id: int, message: str):
    channel = client.get_channel(channel_id)

    if channel is None:
        channel = await client.fetch_channel(channel_id)

    await channel.send(message)


async def resolve_round():
    global round_number

    kill_votes = round_actions["kills"]
    selected_kill = None

    if kill_votes:
        vote_counts = Counter(kill_votes)
        highest_vote_count = max(vote_counts.values())

        tied_targets = [
            target
            for target, count in vote_counts.items()
            if count == highest_vote_count
        ]

        if len(tied_targets) > 1 and round_actions["murder_tie"] is None:
            round_actions["murder_tie"] = tied_targets

            await send_to_channel(
                KILLERS_CHANNEL_ID,
                "The murderers did not agree.\n\n"
                f"Tied targets: {', '.join(tied_targets)}\n\n"
                "You have one more chance to agree. Submit again with "
                "`kill Player Name`."
            )

            round_actions["kills"].clear()
            return

        elif len(tied_targets) > 1 and round_actions["murder_tie"] is not None:
            selected_kill = random.choice(tied_targets)

            await send_to_channel(
                KILLERS_CHANNEL_ID,
                f"The murderers still did not agree. Random kill selected: {selected_kill}"
            )

        else:
            selected_kill = tied_targets[0]

        target = get_player_by_name(selected_kill)

        if target:
            target.is_alive = False

    for target_name in round_actions["heals"]:
        target = get_player_by_name(target_name)

        if target:
            target.is_alive = True
        selected_heal = target

    status_lines = []

    for player in players:
        status = "Alive" if player.is_alive else "Dead"
        status_lines.append(f"{player.name}: {status}")

    kill_result = (
        f"The murderers killed: {selected_kill}"
        if selected_kill
        else "The murderers did not kill anyone."
    )

    if selected_kill == selected_heal.name:
        kill_result = f'The murders attempted to kill {selected_kill}, However, the healer saved them!'

    await send_to_channel(
        ALL_PLAYERS_CHANNEL_ID,
        f"Round complete.\n\n{kill_result}\n\n" + "\n".join(status_lines)
    )

    round_actions["kills"].clear()
    round_actions["heals"].clear()
    round_actions["murder_tie"] = None

    round_number += 1

    await send_to_channel(
        ALL_PLAYERS_CHANNEL_ID,
        f"Round {round_number} has started."
    )

    await send_round_instructions()

@client.event
async def send_round_instructions():
    global players
    global KILLERS_CHANNEL
    global KILLERS_CHANNEL_ID
    global HEALERS_CHANNEL
    global HEALERS_CHANNEL_ID
    alive_players = get_alive_player_names(players)
    players_list = "\n".join(alive_players)

    await send_to_channel(
        KILLERS_CHANNEL_ID,
        f"Murderers: submit a kill with `kill Player Name`.\n Players Alive:\n {players_list}."
    )

    await send_to_channel(
        HEALERS_CHANNEL_ID,
        f"Healers: submit a heal with `heal Player Name`. \n Players Alive:\n {players_list}."
    )

async def get_discord_members(guild, game_players):
    members = []

    for player in game_players:
        member = guild.get_member(player.discord_name)

        if member is None:
            member = await guild.fetch_member(player.discord_name)

        members.append(member)

    return members


async def create_role_channel(guild, role_name, game_players, bot_member):
    members = await get_discord_members(guild, game_players)
    random_int = random.randint(0, 100)

    channel = await create_private_channel(
        guild=guild,
        channel_name=f"{role_name}-room_{random_int}",
        allowed_members=members,
        bot_member=bot_member,
    )

    return channel


@client.event
async def on_ready():
    global players
    global KILLERS_CHANNEL
    global KILLERS_CHANNEL_ID
    global HEALERS_CHANNEL
    global HEALERS_CHANNEL_ID

    print(f"Logged in as {client.user}")

    player_info = yaml_to_dict("player_info.yaml")
    players = generate_players(player_info)

    await send_to_channel(
        ALL_PLAYERS_CHANNEL_ID,
        ":ninja: Murder Mystery game started. :ninja:"
    )

    healers = get_healers(players)
    killers = get_killers(players)
    print(f"Healers: {', '.join(h.name for h in healers)}")
    print(f"Killers: {', '.join(k.name for k in killers)}")

    guild = client.guilds[0]
    bot_member = guild.me
    KILLERS_CHANNEL = await create_role_channel(
        guild=guild,
        role_name="murderers",
        game_players=killers,
        bot_member=bot_member,
    )
    KILLERS_CHANNEL_ID = KILLERS_CHANNEL.id

    HEALERS_CHANNEL = await create_role_channel(
        guild=guild,
        role_name="healers",
        game_players=healers,
        bot_member=bot_member,
    )
    HEALERS_CHANNEL_ID = HEALERS_CHANNEL.id

    await send_round_instructions()




@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()

    alive_names = get_alive_player_names(players)

    if message.channel.id == KILLERS_CHANNEL_ID:
        if content.lower().startswith("kill "):
            raw_target = content[5:].strip()

            closest_name = find_closest_name(alive_names, raw_target)

            if closest_name is None:
                await message.channel.send(
                    f"Could not find a close match for `{raw_target}`."
                )
                return

            round_actions["kills"].append(closest_name)

            await message.channel.send(
                f"Kill submitted: {closest_name}"
            )

    elif message.channel.id == HEALERS_CHANNEL_ID:
        if content.lower().startswith("heal "):
            raw_target = content[5:].strip()

            closest_name = find_closest_name(alive_names, raw_target)

            if closest_name is None:
                await message.channel.send(
                    f"Could not find a close match for `{raw_target}`."
                )
                return

            round_actions["heals"].append(closest_name)

            await message.channel.send(
                f"Heal submitted: {closest_name}"
            )

    elif message.channel.id == ALL_PLAYERS_CHANNEL_ID:
        if content.lower() == "resolve round":
            await resolve_round()


client.run(TOKEN)