# client/network/network.py
import paramiko
import os
import time
import json
import logging
from dotenv import load_dotenv
from shared.network_utils import serialize_message, deserialize_message

load_dotenv()

class ClientNetwork:
    def __init__(self):
        self.host = os.getenv("CLIENT_HOST")
        self.port = int(os.getenv("CLIENT_PORT", 2200))
        self.username = os.getenv("CLIENT_USERNAME")
        self.key_filename = os.getenv("CLIENT_KEY_FILENAME")
        self.key_passphrase = os.getenv("CLIENT_KEY_PASSPHRASE")
        # Password used for SSH password authentication; must match the
        # server's RIVER_RAID_PASSWORD. Added alongside the server-side
        # auth fix -- the server no longer accepts public-key auth
        # unconditionally, so a real password is required to connect.
        self.password = os.getenv("RIVER_RAID_PASSWORD")
        self.ssh_client = paramiko.SSHClient()

    def connect(self):
        logging.info("Establishing SSH connection to server...")
        try:
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # Public-key auth is intentionally never attempted here: the
            # server's check_auth_publickey always fails closed (see
            # ssh_server.py), so a key-based attempt can never succeed
            # server-side. Passing key_filename to paramiko also triggers an
            # unrelated bug where the modern "OPENSSH PRIVATE KEY" format
            # (ssh-keygen's default since OpenSSH 7.8) gets misidentified as
            # a DSA key during auto-detection, raising
            # "q must be exactly 160, 224, or 256 bits long" instead of
            # falling through to password auth. look_for_keys/allow_agent
            # are also disabled so no ambient key on the machine running the
            # client is tried either -- password is the only auth method
            # this server supports.
            self.ssh_client.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                look_for_keys=False,
                allow_agent=False,
            )
            self.channel = self.ssh_client.get_transport().open_session()
            self.buffer = ""
            logging.info("SSH connection established.")
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            logging.error(f"Connection Error - Details: {str(e)}")
            logging.error(f"Host: {self.host}, Port: {self.port}")
            raise
        except Exception as e:
            logging.error(f"Failed to establish SSH connection: {str(e)}")
            raise

    def send_message(self, message):
        message_json = serialize_message(message) + '\n'
        #logging.info(f"Sending message: {message_json.strip()}")  # Remove '\n' from log
        self.channel.send(message_json.encode('utf-8'))

    def receive_message(self):
        while True:
            try:
                part = self.channel.recv(2048).decode('utf-8')
                self.buffer += part
                
                while '\n' in self.buffer:
                    message, self.buffer = self.buffer.split('\n', 1)
                    if message.strip():
                        try:
                            deserialized_message = json.loads(message)
                            if deserialized_message.get('status') == 'ok':
                                if 'game_state' in deserialized_message:
                                    # Handle direct game_state
                                    game_state = deserialized_message['game_state']
                                    return deserialized_message
                                elif 'responses' in deserialized_message and len(deserialized_message['responses']) > 0:
                                    # Handle nested game_state
                                    nested_response = deserialized_message['responses'][0]
                                    if 'game_state' in nested_response:
                                        return nested_response
                                else:
                                    logging.warning(f"Received 'ok' status but no 'game_state' key found. Full message: {deserialized_message}")
                            else:
                                logging.warning(f"Unexpected status in message: {deserialized_message.get('status')}. Full message: {deserialized_message}")
                        except json.JSONDecodeError as e:
                            logging.warning(f"Failed to decode message: {message[:25]}, Error: {e}")
                            continue
                        except ValueError as e:
                            logging.warning(f"Malformed message: {message[:25]}, Error: {e}")
                            continue
                    else:
                        logging.warning(f"Received invalid JSON message: {message[:25]}")
            except Exception as e:
                logging.error(f"Error receiving message: {e}")
                time.sleep(0.1)
        return None

    def close(self):
        logging.info("Closing SSH connection.")
        self.channel.close()
        self.ssh_client.close()
