class ClientGameLogic:
    def __init__(self, client):
        """
        Initialize the GameLogic instance.
        :param client: An instance of ClientNetwork to handle communication.
        """
        self.client = client

    def start_game(self):
        """
        Handles starting and running the game logic.
        """
        try:
            # Send a command to start the game
            print(1)
            start_message = {"action": "start"}
            print(2)
            self.client.send_message(start_message)

            # Receive server response
            print(3)
            response = self.client.receive_message()
            print(4)
            print(f"Server response: {response}")

            # Send an update command
            print(5)
            update_message = {"action": "update", "command": "move player"}
            print(6)
            self.client.send_message(update_message)

            # Receive server response
            print(7)
            response = self.client.receive_message()
            print(8)
            print(f"Server response: {response}")

            # Notify the server that the client program is closed
            update_message = {"action": "Client program closed"}
            print(9)
            self.client.send_message(update_message)

        except Exception as e:
            print(f"An error occurred in the game logic: {e}")
