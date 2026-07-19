# server/game/game_manager.py
import os 
import threading
import queue
import time
import logging
import signal
from server.game.game_state import GameState
from server.game.game_loops import GameLoops
from server.game.entity_manager import EntityManager

class GameManager:
    """Manages game state, threads, and overall game flow"""
    def __init__(self):
        logging.info("game_manager: Initialized")
        # Core game components
        self.shared_state = GameState()
        self.running = False
        self.game_running = False
        self.thread_lock = threading.Lock()
        # Reduced queue size and added rate limiting
        self.input_queue = queue.Queue(maxsize=20)  # Reduced from 100
        self.MAX_INPUTS_PER_SECOND = 30  # Rate limit
        self.last_input_time = time.time()
        self.input_interval = 1.0 / self.MAX_INPUTS_PER_SECOND

        # Thread monitoring
        self.thread_health = {}
        self.last_thread_check = {}
        self.thread_restart_attempts = {}
        self.MAX_RESTART_ATTEMPTS = 3
        self.THREAD_CHECK_INTERVAL = 5.0  # Seconds

        # Initialize managers and threads
        self._setup_managers_and_threads()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle termination signals (e.g., Ctrl+C)"""
        logging.info(f"game_manager: Caught signal {sig}. Exiting gracefully...")
        self.quit_game()

    def _setup_managers_and_threads(self):
        """Initialize managers and setup all threads"""
        # Initialize managers
        self.game_loops = GameLoops(self.shared_state)
        self.entity_manager = EntityManager(self.shared_state)

        # Create main threads
        self.threads = {
            'collision': threading.Thread(
                target=self.game_loops.collision_loop,
                args=(self._is_game_running,)
            ),
            'state': threading.Thread(
                target=self.game_loops.state_loop,
                args=(self._is_game_running,)
            ),
            'input': threading.Thread(
                target=self._input_loop
            ),
            'monitor': threading.Thread(
                target=self._monitor_threads
            )
        }

        # Initialize thread health monitoring
        for thread_name in self.threads:
            self.thread_health[thread_name] = True
            self.last_thread_check[thread_name] = time.time()
            self.thread_restart_attempts[thread_name] = 0

        # Set all threads as daemon
        for thread in self.threads.values():
            thread.daemon = True

    def start(self):
        """Start game manager and all threads"""
        logging.info("game_manager: Running Start function")
        if not self.running:
            self.running = True
            self.game_running = True

            # Start monitoring thread first
            if not self.threads['monitor'].is_alive():
                self.threads['monitor'].start()
                logging.info("game_manager: Started monitor thread")

            # Start core game threads
            for name, thread in self.threads.items():
                if name != 'monitor' and not thread.is_alive():
                    thread.start()
                    logging.info(f"game_manager: Started {name} thread")

            # Start entity management threads
            self.entity_manager.start_movement_threads()
            logging.info("game_manager: Game manager started successfully")

    def stop(self):
        """Stop game manager and cleanup all threads"""
        logging.info("game_manager: Stopping game manager...")

        self.running = False
        self.game_running = False

        # Stop entity manager threads
        self.entity_manager.stop_movement_threads()

        # Wait for all threads to finish
        for name, thread in self.threads.items():
            if thread.is_alive():
                logging.info(f"game_manager: Waiting for {name} thread to finish...")
                thread.join(timeout=5.0)  # Give threads 5 seconds to finish
                if thread.is_alive():
                    logging.warning(f"game_manager: {name} thread did not finish cleanly")
                else:
                    logging.info(f"game_manager: Stopped {name} thread successfully")
            else:
                logging.info(f"game_manager: {name} thread was not running")

        logging.info("game_manager: Game manager stopped successfully")

    def quit_game(self):
        """Gracefully stop the game and exit"""
        self.stop()
        logging.info("game_manager: Application closed successfully")
        os._exit(0)

    def _monitor_threads(self):
        """Monitor thread health and restart if necessary"""
        while self.running:
            try:
                current_time = time.time()
                
                for name in list(self.threads.keys()):  # Create a copy of keys to iterate
                    if name == 'monitor':
                        continue
                        
                    thread = self.threads.get(name)
                    if thread and not thread.is_alive():
                        if self.thread_restart_attempts[name] < self.MAX_RESTART_ATTEMPTS:
                            logging.warning(f"game_manager: Thread - {name} - died, attempting restart...")
                            self._restart_thread(name)
                        else:
                            logging.error(f"game_manager: Thread - {name} - failed to restart {self.MAX_RESTART_ATTEMPTS} times")
                            self.stop()
                            return
                            
                    # Reset restart count if thread has been running for a while
                    if current_time - self.last_thread_check.get(name, 0) > self.THREAD_CHECK_INTERVAL:
                        self.thread_restart_attempts[name] = 0
                        self.last_thread_check[name] = current_time
                        
                time.sleep(1.0)
            except Exception as e:
                logging.error(f"Error in monitor thread: {e}")
                time.sleep(1.0)

    def _restart_thread(self, thread_name):
        """Restart a failed thread with synchronization"""
        with self.thread_lock:  # Protect thread restart process
            self.thread_restart_attempts[thread_name] += 1
            
            # Wait for old thread to fully terminate
            if self.threads[thread_name].is_alive():
                self.threads[thread_name].join(timeout=0.5)
            
            # Create new thread based on type
            if thread_name == 'collision':
                new_thread = threading.Thread(
                    target=self.game_loops.collision_loop,
                    args=(self._is_game_running,)
                )
            elif thread_name == 'state':
                new_thread = threading.Thread(
                    target=self.game_loops.state_loop,
                    args=(self._is_game_running,)
                )
            elif thread_name == 'input':
                new_thread = threading.Thread(
                    target=self._input_loop
                )
            
            new_thread.daemon = True
            self.threads[thread_name] = new_thread
            self.thread_health[thread_name] = True
            self.last_thread_check[thread_name] = time.time()
            
            # Add small delay before starting new thread
            time.sleep(0.1)
            new_thread.start()
            
            logging.info(f"game_manager: Thread - {thread_name} - restarted (attempt {self.thread_restart_attempts[thread_name]})")

    def _input_loop(self):
        """Handle input queue processing with rate limiting"""
        while self.running:
            try:
                # Rate limiting
                current_time = time.time()
                if current_time - self.last_input_time < self.input_interval:
                    time.sleep(self.input_interval - (current_time - self.last_input_time))

                # Process input
                message = self.input_queue.get(timeout=0.05)
                with self.shared_state.state_lock:
                    if message["action"] == "reset_game":
                        self._handle_reset()
                    elif self.shared_state.game_state == GameState.STATE_RUNNING:
                        self._handle_action(message)
                        self.last_input_time = time.time()
                        
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error in input loop: {e}")
                if not self.thread_health['input']:
                    break
        logging.info("game_loops: Input loop has stopped")

    def _handle_reset(self):
        """Handle game reset"""
        try:
            self.shared_state.reset()
            self.game_running = True
            logging.info("Game reset successfully")
        except Exception as e:
            logging.error(f"Error during game reset: {e}")

    def _handle_action(self, message):
        """Handle game actions"""
        try:
            if message["action"] == "move":
                self.shared_state.player.move(message["direction"])
            elif message["action"] == "shoot":
                missile = self.shared_state.player.shoot()
                self.shared_state.add_missile(missile)
        except Exception as e:
            logging.error(f"Error handling action: {e}")

    def process_message(self, message):
        """Process incoming messages with rate limiting"""
        try:
            current_time = time.time()
            if current_time - self.last_input_time < self.input_interval:
                # Skip if too soon
                return {"status": "ok", "game_state": self.shared_state.get_state()}

            if message == {'action': 'reset_game'}:
                self._handle_reset()
            else:
                try:
                    self.input_queue.put(message, timeout=0.1)  # Short timeout
                    self.last_input_time = current_time
                except queue.Full:
                    logging.warning("Input queue full, dropping message")
                    
            return {"status": "ok", "game_state": self.shared_state.get_state()}
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return {"status": "error", "message": "Invalid request."}

    def _is_game_running(self):
        """Check if game is running"""
        return self.game_running