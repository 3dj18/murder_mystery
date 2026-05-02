from classes.player import Player

class Healer(Player):

    def __init__(self, name: str, role: str, is_alive: bool, nfc_uuid: str):
        super().__init__(name, role, is_alive, nfc_uuid)

        self.heal_count = 0

    def heal_player(self, player: Player):
        player.is_alive = True
        self.heal_count += 1
        print(f"Player {player.name} was healed")