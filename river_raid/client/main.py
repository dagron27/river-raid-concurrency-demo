from client.network.network import ClientNetwork
from client.game.game_manager import GameManager

if __name__ == "__main__":
    client = ClientNetwork()
    client.connect()

    app = GameManager(client)
    app.mainloop()

    client.close()
