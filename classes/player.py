

class Player:
    def __init__(self, name: str, role: str, is_alive: bool, nfc_uuid: str, discord_name: str):
        self.name = name
        self.role = role
        self.is_alive = is_alive
        self.nfc_uuid = nfc_uuid
        self.discord_name = discord_name

    def return_status(self):
        if self.is_alive:
            print(f"{self.name} is alive")
        else:
            print(f"{self.name} is dead")
