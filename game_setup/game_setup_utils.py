import random
import yaml
from classes.player import Player
from classes.healer import Healer
from classes.murderer import Murderer
from difflib import get_close_matches


ROLES = ['player', 'murder', 'healer']
MAX_HEALERS = 1
MAX_MURDERS = 2


def get_alive_player_names(players: list[Player]):
    return [player.name for player in players if player.is_alive]

def yaml_to_dict(path_to_file:str):
    with open(path_to_file, 'r') as file:
        return yaml.safe_load(file)


def get_random_role():
    return random.choice(ROLES)

def get_list_of_player_names(player_info: list):
    player_names = []
    for player_key in player_info:
        player_names.append(player_key.name)
    return player_names


def find_closest_name(names: list, input_val: str, cutoff: float = 0.3):
    lower_names = {name.lower(): name for name in names}

    matches = get_close_matches(input_val.lower(), lower_names.keys(), n=1, cutoff=cutoff)
    print(f"Closest match for '{input_val}': {matches[0]}")
    return lower_names[matches[0]] if matches else None

def generate_players(player_info: dict):
    list_players = []
    healer_count = 0
    murderer_count = 0

    total_players = len(player_info)

    required_special_roles = MAX_HEALERS + MAX_MURDERS

    if total_players < required_special_roles:
        raise ValueError(
            f"Not enough players. Need at least {required_special_roles}, "
            f"but only got {total_players}."
        )

    roles = (
            ["healer"] * MAX_HEALERS +
            ["murder"] * MAX_MURDERS +
            ["player"] * (total_players - required_special_roles)
    )

    random.shuffle(roles)

    for player_key, role in zip(player_info, roles):
        player_data = player_info[player_key]

        common_kwargs = {
            "name": player_data["name"],
            "role": role,
            "is_alive": True,
            "nfc_uuid": player_data["nfc_uuid"]
        }

        if role == "healer":
            list_players.append(Healer(**common_kwargs))
        elif role == "murder":
            list_players.append(Murderer(**common_kwargs))
        else:
            list_players.append(Player(**common_kwargs))

    return list_players

def get_player_from_list_by_name(player_list: list, name: str):
    for player in player_list:
        if player.name == name:
            return player
    return None

def start_round(players: list):
    print("Starting round...")

    kill_targets = []
    heal_targets = []
    current_player_names = get_list_of_player_names(players)

    murderers = [p for p in players if p.role == "murder"]
    healers = [p for p in players if p.role == "healer"]

    random.shuffle(murderers)
    random.shuffle(healers)

    for murderer in murderers:
        target = input(
            f"{murderer.name} is killing. Who do you want to kill? (name): "
        )
        true_target = find_closest_name(current_player_names, target)
        kill_targets.append((murderer, true_target))

    for healer in healers:
        heal = input(
            f"{healer.name} is healing. Do you want to heal? (y/n): "
        )

        if heal.lower() == "y":
            target = input("Which player do you want to heal? (name): ")
            true_target = find_closest_name(current_player_names, target)
            heal_targets.append((healer, true_target))
        else:
            print(f"{healer.name} chose not to heal")

    # Resolve kills first
    for murderer, target in kill_targets:
        murderer.attempt_to_kill_player(get_player_from_list_by_name(players, target))

    # Resolve heals second
    for healer, target in heal_targets:
        healer.heal_player(get_player_from_list_by_name(players, target))

    print("Round complete.")

    for player in players:
        player.return_status()

def get_killers(players: list):
    killers = []
    for player in players:
        if player.role == 'murder':
            killers.append(player)
    return killers

def get_healers(players: list):
    healers = []
    for player in players:
        if player.role == 'healer':
            healers.append(player)

    return healers