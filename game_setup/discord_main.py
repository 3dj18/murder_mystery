from pip._internal.models import target_python

from game_setup.discord_helper import client, TOKEN, send_message, is_from_channel, create_private_channel
from game_setup.game_setup_utils import yaml_to_dict, generate_players, find_closest_name, get_alive_player_names, get_healers, get_killers

import os
import discord
from dotenv import load_dotenv

from collections import Counter
import random
import asyncio


load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# MURDERERS_CHANNEL_ID = int(os.getenv("MURDERERS_CHANNEL_ID"))
# HEALERS_CHANNEL_ID = int(os.getenv("HEALERS_CHANNEL_ID"))
ALL_PLAYERS_CHANNEL_ID = int(os.getenv("ALL_PLAYERS_CHANNEL_ID"))
KILLERS_CHANNEL = None
KILLERS_CHANNEL_ID = 0
HEALERS_CHANNEL = None
HEALERS_CHANNEL_ID = 0

ROUND_TIME_LIMIT_SECONDS = 30
VOTE_TIME_LIMIT_SECONDS = 30

game_state = {
    "round_number": 0,
    "phase": "night",
    "kills": {},
    "heals": {},
    "votes": {},
    "night_task": None,
    "vote_task": None
}

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

async def resolve_day_vote():
    if game_state["phase"] != "day_vote":
        return

    game_state["phase"] = "results"

    if game_state["vote_task"]:
        game_state["vote_task"].cancel()
        game_state["vote_task"] = None

    votes = list(game_state["votes"].values())
    voted_out = None

    if votes:
        vote_counts = Counter(votes)
        highest_count = max(vote_counts.values())

        tied_targets = [
            target
            for target, count in vote_counts.items()
            if count == highest_count
        ]

        voted_out = random.choice(tied_targets)

        player = get_player_by_name(voted_out)

        if player:
            player.is_alive = False

        if voted_out:
            message = f"{voted_out} has been voted out"
        else:
            message = "No one was voted out"

        await send_to_channel(
            ALL_PLAYERS_CHANNEL_ID,
            message
        )

        game_state["round_number"] += 1
        await start_round()

def voting_complete():
    alive_players = [p for p in players if p.is_alive]
    return len(game_state["votes"]) >= len(alive_players)


async def vote_timer():
    await asyncio.sleep(VOTE_TIME_LIMIT_SECONDS)

    if game_state["phase"] == "day_vote":
        await send_to_channel(
            ALL_PLAYERS_CHANNEL_ID,
            "Voting timer expired. Resolve vote..."
        )

    await resolve_day_vote()


async def start_day_vote():
    game_state["phase"] = "day_vote"
    game_state["votes"].clear()

    alive_names = "\n".join(
        f"* {p.name}"
        for p in players
        if p.is_alive
    )

    await send_to_channel(
        ALL_PLAYERS_CHANNEL_ID,
        "Voting is now open.\n"
        "Vote someone out with 'vote Player Name'\n\n"
        f"Alive Players:\n{alive_names}"
    )

    if game_state["vote_task"]:
        game_state["vote_task"].cancel()

    game_state["vote_task"] = asyncio.create_task(vote_timer())


def night_actions_compete():
    global game_state
    alive_killers = [p for p in players if p.role == "murder" and p.is_alive]
    alive_healers = [p for p in players if p.role == "healer" and p.is_alive]

    killers_done = len(game_state["kills"]) >= len(alive_killers)
    healers_done = len(game_state["heals"]) >= len(alive_healers)

    return killers_done and healers_done

async def send_night_results(selected_kill):
    if selected_kill:
        killed_player = get_player_by_name(selected_kill)

        if killed_player and killed_player.is_alive:
            result = f"{selected_kill} was attacked but survived"
        else:
            result = f"{selected_kill} was killed"

    else:
        result = f"No one was killed"

    alive_names = "\n".join(
        f"* {p.name}"
        for p in players
        if p.is_alive
    )

    await send_to_channel(
        ALL_PLAYERS_CHANNEL_ID,
        f"{result}\n\nAlive Players:\n{alive_names}"
    )


async def resolve_night():
    if game_state["phase"] != "night":
        return

    game_state["phase"] = "results"

    current_task = asyncio.current_task()

    if game_state["night_task"] and game_state["night_task"] != current_task:
        game_state["night_task"].cancel()

    game_state["night_task"] = None

    selected_kill = None

    kill_votes = list(game_state["kills"].values())
    heal_targets = list(game_state['heals'].values())

    if kill_votes:
        vote_counts = Counter(kill_votes)
        highest_count = max(vote_counts.values())

        tied_targets = [
            target
            for target, count in vote_counts.items()
            if count == highest_count
        ]

        selected_kill = random.choice(tied_targets)

        target_player = get_player_by_name(selected_kill)

        if target_player:
            target_player.is_alive = False



        for heal_target in heal_targets:
            target_player = get_player_by_name(heal_target)

            if target_player:
                target_player.is_alive = True

    await send_night_results(selected_kill)
    print("Night resolved. Starting day vote...")
    await start_day_vote()

async def night_timer():
    await asyncio.sleep(ROUND_TIME_LIMIT_SECONDS)

    if game_state["phase"] == "night":
        await send_to_channel(
            ALL_PLAYERS_CHANNEL_ID,
            "Night Time expired. Resolving round..."
        )
        await resolve_night()

async def start_round():
    global game_state

    game_state["phase"] = "night"
    game_state["kills"].clear()
    game_state["heals"].clear()
    game_state["votes"].clear()

    await send_to_channel(
        ALL_PLAYERS_CHANNEL_ID, f"Round {game_state['round_number']} has started. Night Actions are open"
    )

    await send_round_instructions()

    if game_state["night_task"]:
        game_state["night_task"].cancel()
    game_state["night_task"] = asyncio.create_task(night_timer())

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

    round_number += 1

    await send_to_channel(
        ALL_PLAYERS_CHANNEL_ID,
        f"Round {round_number} has started."
    )

    await send_round_instructions()

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

    await start_round()




@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()

    alive_names = get_alive_player_names(players)

    if game_state["phase"] == "night":
        if message.channel.id == KILLERS_CHANNEL_ID:
            if content.lower().startswith("kill "):
                raw_target = content[5:].strip()

                closest_name = find_closest_name(alive_names, raw_target)

                if closest_name is None:
                    await message.channel.send(
                        f"Could not find a close match for `{raw_target}`."
                    )
                    return

                game_state["kills"][message.author.id] = closest_name

                await message.channel.send(
                    f"Kill submitted: {closest_name}"
                )

                if night_actions_compete():
                    await resolve_night()

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
                game_state["heals"][message.author.id] = closest_name

                await message.channel.send(
                    f"Heal submitted: {closest_name}"
                )

                if night_actions_compete():
                    await resolve_night()
    elif game_state["phase"] == "day_vote":
        if message.channel.id == ALL_PLAYERS_CHANNEL_ID:
            if content.lower().startswith("vote "):
                raw_target = content[5:].strip()
                closest_name = find_closest_name(alive_names, raw_target)

                if closest_name is None:
                    await message.channel.send(f"Could not find a close match for `{raw_target}`.")
                    return
                game_state["votes"][message.author.id] = closest_name

                await message.channel.send(
                    f"{message.author.display_name} voted for {closest_name}"
                )

                if voting_complete():
                    await resolve_day_vote()




client.run(TOKEN)