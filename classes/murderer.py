from classes.player import Player

class Murderer(Player):
    def __init__(self, name: str, role: str, is_alive: bool, nfc_uuid: str):
        super().__init__(name, role, is_alive, nfc_uuid)
        self.murder_count = 0



    def attempt_to_kill_player(self, player: Player):
        player.is_alive = False
        self.murder_count += 1
        print(f"Player {player.name} was killed")