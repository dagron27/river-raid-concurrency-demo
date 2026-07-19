# client/game/game_manager.py
import tkinter as tk
import logging
import time
import threading
import queue
from client.game.game_logic import GameLogic
from client.game.canvas_gui import GameCanvas
from client.game.game_state import GameState
from shared.config import WINDOW_HEIGHT, WINDOW_WIDTH

class GameManager(tk.Tk):
    def __init__(self, client):
        super().__init__()
        self.title("River Raid")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Initialize game state and logic
        self.game_state = GameState(client)
        self.game_logic = GameLogic(self.game_state)

        # Create canvas and GUI elements
        self.canvas = GameCanvas(self, self.game_logic)
        self.info_label = tk.Label(
            self, 
            text="Score: 0 | Lives: 3 | Fuel: 100",
            font=("Helvetica", 25)
        )
        self.info_label.pack()

        # State tracking
        self._reset_in_progress = False
        self._last_state_update = time.time()

        # Bind keyboard controls
        self.bind("<KeyPress-Left>", self.on_key_press)
        self.bind("<KeyRelease-Left>", self.on_key_release)
        self.bind("<KeyPress-Right>", self.on_key_press)
        self.bind("<KeyRelease-Right>", self.on_key_release)
        self.bind("<KeyPress-space>", self.on_key_press)
        self.bind("<KeyRelease-space>", self.on_key_release)
        self.bind("<Return>", lambda event: self.restart_game() if self.game_logic.game_state != "running" else None)
        self.bind("<q>", lambda event: self.quit_game())

        # Key state tracking and cooldowns
        self.keys_pressed = set()
        self.last_move_time = 0
        self.move_cooldown = 0.2  # 200ms cooldown for movement
        self.last_shoot_time = 0
        self.shoot_cooldown = 0.3  # 300ms cooldown for shooting

        # Configure window close behavior
        self.protocol("WM_DELETE_WINDOW", self.quit_game)

        # Set up game loop
        self.tick_rate = 20  # 50 FPS
        self.restart_game()
        self.game_loop()

    def on_key_press(self, event):
        """Handle key press events"""
        if self.game_logic.game_state == "running":
            self.keys_pressed.add(event.keysym)

    def on_key_release(self, event):
        """Handle key release events"""
        if event.keysym in self.keys_pressed:
            self.keys_pressed.remove(event.keysym)

    def game_loop(self):
        """Main game loop"""
        try:
            current_time = time.time()
            
            # Process state updates if not resetting
            if not self._reset_in_progress:
                updates = self.game_state.get_state_updates()
                if updates:
                    latest_state = updates[-1]
                    self.game_logic.update_game_state(latest_state)
                    self.canvas.update_canvas()
                    self._last_state_update = current_time

                    # Update game info display
                    self.info_label.config(
                        text=f"Score: {self.game_logic.score} | Lives: {self.game_logic.lives} | Fuel: {self.game_logic.fuel}",
                        font=("Helvetica", 25)
                    )

            # Handle key states for movement and shooting
            if "Left" in self.keys_pressed and current_time - self.last_move_time >= self.move_cooldown:
                self.last_move_time = current_time
                self.player_move("left")
            elif "Right" in self.keys_pressed and current_time - self.last_move_time >= self.move_cooldown:
                self.last_move_time = current_time
                self.player_move("right")

            if "space" in self.keys_pressed and current_time - self.last_shoot_time >= self.shoot_cooldown:
                self.last_shoot_time = current_time
                self.player_shoot()

        except Exception as e:
            logging.warning(f"Warning in game_loop: {e}")

        finally:
            # Schedule next frame
            self.after(self.tick_rate, self.game_loop)

    def player_move(self, direction):
        """Handle player movement input"""
        try:
            if not self._reset_in_progress:
                self.game_state.send_action({
                    "action": "move",
                    "direction": direction
                })
        except Exception as e:
            logging.warning(f"Warning in player_move: {e}")

    def player_shoot(self):
        """Handle player shoot input"""
        try:
            if not self._reset_in_progress:
                self.game_state.send_action({
                    "action": "shoot"
                })
        except Exception as e:
            logging.warning(f"Warning in player_shoot: {e}")

    def restart_game(self):
        """Handle game restart"""
        try:
            if self.game_logic.game_state != "running" and not self._reset_in_progress:
                self._reset_in_progress = True
                self.canvas.display_game_over()
                
                # Create and start reset thread
                self.reset_thread = threading.Thread(target=self._reset_server_state, daemon=True)
                self.reset_thread.start()
                
                # Schedule GUI update on main thread
                self.after(100, self._update_gui_after_reset)
                
        except Exception as e:
            logging.warning(f"Warning in restart_game: {e}")
            self._reset_in_progress = False

    def _reset_server_state(self):
        """Handle server communication in separate thread"""
        try:
            # Clear any pending state updates
            while not self.game_state.update_queue.empty():
                try:
                    self.game_state.update_queue.get_nowait()
                except queue.Empty:
                    break

            # Send reset command to server
            self.game_state.send_action({"action": "reset_game"})
            time.sleep(0.1)  # Wait for server reset
            
            # Reset local game state
            self.game_logic.reset_game()
            self._reset_completed = True
            
        except Exception as e:
            logging.warning(f"Warning in _reset_server_state: {e}")
            self._reset_completed = False

    def _update_gui_after_reset(self):
        """Update GUI elements on main thread"""
        try:
            if hasattr(self, '_reset_completed'):
                if self._reset_completed:
                    # Update GUI
                    self.info_label.config(
                        text="Score: 0 | Lives: 3 | Fuel: 100",
                        font=("Helvetica", 25)
                    )
                    self.canvas.update_canvas()
                    
                    # Cleanup
                    delattr(self, '_reset_completed')
                    self._reset_in_progress = False
                    
                else:
                    # Retry if reset wasn't completed
                    self.after(50, self._update_gui_after_reset)
            else:
                # Keep checking if reset is done
                self.after(50, self._update_gui_after_reset)
                
        except Exception as e:
            logging.warning(f"Warning in _update_gui_after_reset: {e}")
            self._reset_in_progress = False

    def quit_game(self):
        """Clean up and close the game"""
        try:
            logging.info("Shutting down game...")
            if hasattr(self, 'game_state'):
                # Stop the game state threads
                self.game_state.stop()
                
                # Wait for message thread to complete
                if hasattr(self.game_state, 'message_thread'):
                    self.game_state.message_thread.join(timeout=2.0)
                    if self.game_state.message_thread.is_alive():
                        logging.warning("Message thread did not terminate cleanly")
                
                # Wait for update thread to complete
                if hasattr(self.game_state, 'update_thread'):
                    self.game_state.update_thread.join(timeout=2.0)
                    if self.game_state.update_thread.is_alive():
                        logging.warning("Update thread did not terminate cleanly")
                
                # Clear queues
                while not self.game_state.message_queue.empty():
                    try:
                        self.game_state.message_queue.get_nowait()
                    except queue.Empty:
                        break
                        
                while not self.game_state.update_queue.empty():
                    try:
                        self.game_state.update_queue.get_nowait()
                    except queue.Empty:
                        break
                        
            # Destroy the window
            self.destroy()
            
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
            # Force destroy if cleanup fails
            self.destroy()