# server/network/ssh_server.py
import os
import paramiko
import sys
import threading
import logging
from dotenv import load_dotenv
from shared.network_utils import serialize_message, deserialize_message
from server.game.game_manager import GameManager

# Ensure .env is loaded even if this module is imported before network.py
# calls load_dotenv() itself (load_dotenv() is safe to call more than once).
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),  # Log to a file named server.log
        logging.StreamHandler(sys.stdout)   # Also log to console
    ]
)

# Maximum size (bytes) a per-connection receive buffer may grow to while
# waiting for a newline-delimited message terminator. Prevents a client that
# never sends '\n' from growing memory unbounded (see handle_client below).
MAX_BUFFER_SIZE = 65536

# Password checked against on SSH auth. Must be configured via the
# RIVER_RAID_PASSWORD environment variable (e.g. in .env); if it is not set,
# the server fails closed and rejects all authentication attempts rather than
# falling back to accepting any credentials.
RIVER_RAID_PASSWORD = os.getenv("RIVER_RAID_PASSWORD")
if not RIVER_RAID_PASSWORD:
    _warning = (
        "ssh_server: RIVER_RAID_PASSWORD is not set. All SSH authentication "
        "attempts will be rejected until it is configured (e.g. in .env). "
        "The server will start but no client will be able to log in."
    )
    print(f"WARNING: {_warning}")
    logging.warning(_warning)

class SSHServer(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
        self.game_manager = GameManager()
        self.running = True
        self.buffer = ""
        
        # Start the game manager
        if not self.game_manager.running: 
            self.game_manager.start() 
            logging.info("ssh_server: Game manager started.")

    def check_channel_request(self, kind, chanid):
        logging.info(f"ssh_server: Channel request: {kind}")
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        logging.info(f"ssh_server: Authentication request: username={username}")
        if not RIVER_RAID_PASSWORD:
            logging.error(
                "ssh_server: Rejecting authentication for username="
                f"{username}: RIVER_RAID_PASSWORD is not configured."
            )
            return paramiko.AUTH_FAILED
        if password == RIVER_RAID_PASSWORD:
            return paramiko.AUTH_SUCCESSFUL
        logging.warning(f"ssh_server: Authentication failed for username={username}")
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        # Public-key auth is not backed by any authorized-key store in this
        # project, so it is disabled (fail closed) rather than accepted
        # unconditionally. Use password auth (RIVER_RAID_PASSWORD) instead.
        logging.info(f"ssh_server: Public key authentication request: username={username} (public-key auth disabled)")
        return paramiko.AUTH_FAILED

    def handle_client(self, channel):  # Ensure this method is correctly defined within the class
        try:
            #logging.info("ssh_server: Handling new client.")
            while True:
                data = channel.recv(2048).decode('utf-8')
                if not data:
                    logging.info("ssh_server: No more data from client. Closing connection.")
                    break

                self.buffer += data

                if '\n' not in self.buffer and len(self.buffer) > MAX_BUFFER_SIZE:
                    logging.error(
                        f"ssh_server: Buffer exceeded {MAX_BUFFER_SIZE} bytes without a "
                        "newline delimiter; closing connection to prevent unbounded growth."
                    )
                    break

                while '\n' in self.buffer:
                    message_str, self.buffer = self.buffer.split('\n', 1)
                    if message_str.strip():
                        try:
                            # Deserialize the message from the client
                            message = deserialize_message(message_str)
                            if message is None:
                                logging.error("ssh_server: Failed to deserialize message")
                                continue

                            # Process the message and prepare a response
                            if "actions" in message:
                                responses = []
                                for action in message["actions"]:
                                    response = self.game_manager.process_message(action)
                                    responses.append(response)
                                response_dict = {"status": "ok", "responses": responses}
                                response_str = serialize_message(response_dict) + '\n'
                            else:
                                response = self.game_manager.process_message(message)
                                response_dict = response
                                response_str = serialize_message(response) + '\n'

                            # Log the response before sending
                            if not response_dict.get('status') == 'ok' or 'game_state' not in response_dict:
                                logging.error(f"ssh_server: Response missing proper 'game_state' or 'ok' information: {response_dict}")

                            # Send the response back to the client
                            channel.send(response_str.encode('utf-8'))
                        except Exception as e:
                            logging.error(f"ssh_server: Error processing message: {e}")
        except Exception as e:
            logging.error(f"ssh_server: Error handling client: {e}")
        finally:
            logging.info("ssh_server: Stopping game manager and closing channel.")
            self.game_manager.stop()
            channel.close()
