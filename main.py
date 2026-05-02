from game_setup.game_setup_utils import generate_players,  yaml_to_dict, start_round

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    players = yaml_to_dict("game_setup/player_info.yaml")
    generated_players = generate_players(players)
    for i in generated_players:
        print(f"{i.name} : {i.role} : {i.is_alive} : {i.nfc_uuid}")
    start_round(generated_players)
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
