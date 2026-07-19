# server/game/game_state.py
import threading
import logging
import time
from shared.config import BOARD_WIDTH, BOARD_HEIGHT
from shared.entities import Player

class GameState:
    """Manages the complete game state with thread safety and state validation"""
    
    # Game state constants
    STATE_RUNNING = "running"
    STATE_GAME_OVER = "game_over"
    
    # Game limits
    MAX_MISSILES = 30
    MAX_ENEMIES = 20
    MAX_FUEL_DEPOTS = 10
    
    def __init__(self):
        # Core state management
        self.state_lock = threading.RLock()
        
        # State change callbacks
        self.state_change_callbacks = []
        
        # Performance monitoring
        self.last_update_time = time.time()
        self.update_count = 0
        self.state_metrics = {
            'updates_per_second': 0,
            'entity_count': 0,
            'last_calculation_time': time.time()
        }
        
        # Initialize game state
        self.reset()

    def reset(self):
        """Reset game state to initial values"""
        with self.state_lock:
            try:
                # Reset player
                self.player = Player(BOARD_WIDTH // 2, BOARD_HEIGHT - 1.5)
                
                # Reset entity lists
                self.missiles = []
                self.fuel_depots = []
                self.enemies = []
                
                # Reset game metrics
                self.score = 0
                self.lives = 3
                self.fuel = 100
                self.game_state = self.STATE_RUNNING
                
                # Reset performance metrics
                self.last_update_time = time.time()
                self.update_count = 0
                
                logging.info("game_state: Game state reset successfully")
                self._notify_state_change("reset")
            except Exception as e:
                logging.error(f"game_state: Error during game state reset: {e}")

    def register_state_change_callback(self, callback):
        """Register a callback for state changes"""
        self.state_change_callbacks.append(callback)

    def _notify_state_change(self, change_type):
        """Notify registered callbacks of state changes"""
        for callback in self.state_change_callbacks:
            try:
                callback(change_type)
            except Exception as e:
                logging.error(f"game_state: Error in state change callback: {e}")

    def add_missile(self, missile):
        """Safely add a missile to the game state"""
        with self.state_lock:
            try:
                if self.is_game_over():
                    return
                    
                if len(self.missiles) < self.MAX_MISSILES:
                    self.missiles.append(missile)
                    logging.debug(f"game_state: Missile added at position ({missile.x}, {missile.y})")
                    self._notify_state_change("missile_added")
                else:
                    logging.warning("game_state: Maximum missile limit reached")
            except Exception as e:
                logging.error(f"game_state: Error adding missile: {e}")

    def add_enemy(self, enemy):
        """Safely add an enemy to the game state"""
        with self.state_lock:
            try:
                if self.is_game_over():
                    return
                    
                if len(self.enemies) < self.MAX_ENEMIES:
                    self.enemies.append(enemy)
                    logging.debug(f"game_state: Enemy type {enemy.type} added at ({enemy.x}, {enemy.y})")
                    self._notify_state_change("enemy_added")
                else:
                    logging.warning("game_state: Maximum enemy limit reached")
            except Exception as e:
                logging.error(f"game_state: Error adding enemy: {e}")

    def add_fuel_depot(self, depot):
        """Safely add a fuel depot to the game state"""
        with self.state_lock:
            try:
                if self.is_game_over():
                    return
                    
                if len(self.fuel_depots) < self.MAX_FUEL_DEPOTS:
                    self.fuel_depots.append(depot)
                    logging.debug(f"game_state: Fuel depot added at ({depot.x}, {depot.y})")
                    self._notify_state_change("fuel_added")
                else:
                    logging.warning("game_state: Maximum fuel depot limit reached")
            except Exception as e:
                logging.error(f"game_state: Error adding fuel depot: {e}")

    def remove_missile(self, missile):
        """Safely remove a missile from game state"""
        with self.state_lock:
            try:
                if missile in self.missiles:
                    self.missiles.remove(missile)
                    logging.debug("game_state: Missile removed")
                    self._notify_state_change("missile_removed")
            except Exception as e:
                logging.error(f"game_state: Error removing missile: {e}")

    def remove_enemy(self, enemy):
        """Safely remove an enemy from game state"""
        with self.state_lock:
            try:
                if enemy in self.enemies:
                    self.enemies.remove(enemy)
                    logging.debug(f"game_state: Enemy type {enemy.type} removed")
                    self._notify_state_change("enemy_removed")
            except Exception as e:
                logging.error(f"game_state: Error removing enemy: {e}")

    def remove_fuel_depot(self, depot):
        """Safely remove a fuel depot from game state"""
        with self.state_lock:
            try:
                if depot in self.fuel_depots:
                    self.fuel_depots.remove(depot)
                    logging.debug("game_state: Fuel depot removed")
                    self._notify_state_change("fuel_removed")
            except Exception as e:
                logging.error(f"game_state: Error removing fuel depot: {e}")

    def update_score(self, points):
        """Safely update the game score"""
        with self.state_lock:
            try:
                if self.is_game_over():
                    return
                    
                self.score += points
                logging.debug(f"game_state: Score updated to {self.score}")
                self._notify_state_change("score_updated")
            except Exception as e:
                logging.error(f"game_state: Error updating score: {e}")

    def update_fuel(self, amount):
        """Safely update fuel amount"""
        with self.state_lock:
            try:
                if self.is_game_over():
                    return
                    
                previous_fuel = self.fuel
                self.fuel = max(0, min(100, self.fuel + amount))
                
                if self.fuel != previous_fuel:
                    self._notify_state_change("fuel_updated")
                
                if self.fuel <= 0:
                    self._handle_fuel_depletion()
                    
            except Exception as e:
                logging.error(f"game_state: Error updating fuel: {e}")

    def _handle_fuel_depletion(self):
        """Handle what happens when fuel runs out"""
        try:
            self.update_lives(-1)
            
            if not self.is_game_over():
                self.fuel = 100
                logging.info(f"game_state: Lost life due to fuel depletion, {self.lives} remaining")
                self._notify_state_change("life_lost")
                
        except Exception as e:
            logging.error(f"game_state: Error handling fuel depletion: {e}")

    def update_lives(self, change):
        """Safely update lives"""
        try:
            if self.is_game_over():
                return
                
            self.lives = max(0, self.lives + change)
            
            if self.lives <= 0:
                self._trigger_game_over("Out of lives")
                
        except Exception as e:
            logging.error(f"game_state: Error updating lives: {e}")

    def _trigger_game_over(self, reason):
        """Handle transition to game over state"""
        try:
            self.game_state = self.STATE_GAME_OVER
            self.lives = 0
            logging.info(f"game_state: Game Over - {reason}")
            self._notify_state_change("game_over")
            
        except Exception as e:
            logging.error(f"game_state: Error triggering game over: {e}")

    def get_state(self):
        """Get the current game state for network transmission"""
        with self.state_lock:
            try:
                self._update_metrics()
                
                return {
                    "p": {
                        "x": self.player.x,
                        "y": self.player.y
                    },
                    "e": [{
                        "x": enemy.x,
                        "y": enemy.y,
                        "t": enemy.type
                    } for enemy in self.enemies],
                    "f": [{
                        "x": depot.x,
                        "y": depot.y
                    } for depot in self.fuel_depots],
                    "m": [{
                        "x": missile.x,
                        "y": missile.y,
                        "t": missile.missile_type
                    } for missile in self.missiles],
                    "s": self.score,
                    "l": self.lives,
                    "u": self.fuel,
                    "g": self.game_state
                }
            except Exception as e:
                logging.error(f"game_state: Error getting game state: {e}")
                return {}

    def _update_metrics(self):
        """Update performance metrics"""
        try:
            current_time = time.time()
            self.update_count += 1
            
            if current_time - self.state_metrics['last_calculation_time'] >= 1.0:
                self.state_metrics['updates_per_second'] = self.update_count
                self.state_metrics['entity_count'] = (
                    len(self.missiles) +
                    len(self.enemies) +
                    len(self.fuel_depots)
                )
                self.update_count = 0
                self.state_metrics['last_calculation_time'] = current_time
                
        except Exception as e:
            logging.error(f"game_state: Error updating metrics: {e}")

    def get_metrics(self):
        """Get current performance metrics"""
        with self.state_lock:
            return self.state_metrics.copy()

    def is_game_over(self):
        """Check if game is over"""
        return self.game_state == self.STATE_GAME_OVER

    def is_running(self):
        """Check if game is running"""
        return self.game_state == self.STATE_RUNNING