# client/game/game_state.py
import threading
import queue
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GameState:
    def __init__(self, client):
        self.client = client
        self.update_queue = queue.Queue(maxsize=1)  # Limit queue size
        self.message_queue = queue.Queue(maxsize=20)  # Queue for player actions
        self.running = True
        self.last_update = time.time()  # Initialize last_update time
        self.update_interval = 0.15  # 50ms between updates

        #Send initial reset action to the server 
        self.send_action({"action": "reset_game"})
        time.sleep(0.1)

        # Start threads
        self._start_threads()

    def _start_threads(self):
        """Initialize and start the handler threads"""
        # Message handling thread
        self.message_thread = threading.Thread(target=self._message_handler)
        self.message_thread.daemon = True
        self.message_thread.start()
        
        # State update thread
        self.update_thread = threading.Thread(target=self._state_updater)
        self.update_thread.daemon = True
        self.update_thread.start()

    def _message_handler(self):
        """Handle all outgoing messages and their responses"""
        while self.running:
            try:
                # Process any pending messages
                try:
                    message = self.message_queue.get_nowait()
                    self.client.send_message(message)
                    response = self.client.receive_message()
                    
                    if response.get('status') == 'ok' and 'game_state' in response:
                        self._update_queue_put(response['game_state'])
                except queue.Empty:
                    time.sleep(0.01)
                    
            except Exception as e:
                logging.error(f"Message handling error: {e}")
                time.sleep(0.1)

    def _state_updater(self):
        """Periodically request game state updates"""
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_update >= self.update_interval:
                    self.client.send_message({"action": "get_game_state"})
                    
                    response = self.client.receive_message()
                    
                    if response.get('status') == 'ok' and 'game_state' in response:
                        self._update_queue_put(response['game_state'])
                        self.last_update = current_time
                    else:
                        logging.warning(f"Unexpected response or missing 'game_state': {response}")
                
            except KeyError as e:
                logging.error(f"State update error: Missing key {e}")
                logging.error(f"Message causing KeyError: {response}")
            except TypeError as e:
                logging.error(f"State update error: Type error {e}")
                logging.error(f"Message causing TypeError: {response}")
            except Exception as e:
                logging.error(f"State update error: Unexpected error {e}")
                logging.error(f"Message causing Unexpected error: {response}")
                time.sleep(0.1)
                
            time.sleep(0.01)

    def _update_queue_put(self, state):
        """Safely put a state update in the queue"""
        try:
            if self.update_queue.full():
                try:
                    self.update_queue.get_nowait()  # Remove old state
                except queue.Empty:
                    pass
            self.update_queue.put_nowait(state)
        except queue.Full:
            logging.warning("Update queue is full. Dropping the oldest state update.")

    def send_action(self, action_data):
        """Queue an action to be sent to the server with rate limiting"""
        retry_attempts = 3
        for _ in range(retry_attempts):
            try:
                self.message_queue.put_nowait(action_data)
                #logging.info(f"Action {action_data} queued to be sent.")
                return
            except queue.Full:
                logging.warning("Message queue is full. Retrying...")
                time.sleep(0.05)
        logging.warning("Message queue is full. Action is dropped after retries.")
        time.sleep(0.1)  # Add a small delay to prevent immediate retries

    def get_state_updates(self):
        """Get all pending state updates"""
        updates = []
        try:
            while True:
                updates.append(self.update_queue.get_nowait())
        except queue.Empty:
            pass
        return updates

    def stop(self):
        """Stop all threads and cleanup"""
        self.running = False
        try:
            self.send_action({"action": "quit_game"})
            time.sleep(0.1)  # Give threads time to clean up
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
