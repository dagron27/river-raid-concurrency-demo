# client/test_client.py

from river_run.client.network.network import ClientNetwork

if __name__ == "__main__":
    client = ClientNetwork()
    client.connect()

    # Send a command to start the game
    print(1)
    start_message = {"action": "start"}
    print(2)
    client.send_message(start_message)

    # Receive server response
    print(3)
    response = client.receive_message()
    print(4)
    print(f"Server response: {response}")

    # Send an update command
    print(5)
    update_message = {"action": "update", "command": "move player"}
    print(6)
    client.send_message(update_message)

    # Receive server response
    print(7)
    response = client.receive_message()
    print(8)
    print(f"Server response: {response}")

    update_message = {"action": "Client program closed"}
    print(9)
    client.send_message(update_message)

    client.close()
