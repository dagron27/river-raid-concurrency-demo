import time
import logging
import threading
from server.game.collision_handler import CollisionHandler

class GameLoops:
    """Manages all game loop logic and timing"""
    def __init__(self, game_state):
        self.game_state = game_state
        self.collision_handler = CollisionHandler(game_state)
        
        # Timing constants
        self.FUEL_RATE = 3
        self.SCORE_RATE = 5
        self.COLLISION_CHECK_INTERVAL = 0.05
        self.STATE_UPDATE_INTERVAL = 0.15
        
        # Performance monitoring
        self.performance_stats = {
            'collision_time': 0,
            'state_time': 0,
            'frame_count': 0
        }
        self.stats_lock = threading.Lock()
        
        # Delta time tracking
        self.last_update_time = time.time()

    def collision_loop(self, running):
        """Main collision detection loop"""
        last_collision_time = time.time()
        
        while running():
            try:
                loop_start = time.time()
                
                with self.game_state.state_lock:
                    if not self.game_state.STATE_RUNNING:
                        time.sleep(self.COLLISION_CHECK_INTERVAL)
                        continue

                    # Calculate delta time
                    current_time = time.time()
                    delta_time = current_time - last_collision_time
                    last_collision_time = current_time
                    
                    # Perform collision detection
                    self.collision_handler.check_all_collisions()
                
                # Track performance
                with self.stats_lock:
                    self.performance_stats['collision_time'] = time.time() - loop_start
                    # logging.info("game_loops: Updated collision_time performance stat")
                    
                # Maintain consistent update rate
                elapsed = time.time() - loop_start
                if elapsed < self.COLLISION_CHECK_INTERVAL:
                    time.sleep(self.COLLISION_CHECK_INTERVAL - elapsed)
                    
            except Exception as e:
                logging.error(f"game_loops: Error in collision loop: {e}")
                time.sleep(self.COLLISION_CHECK_INTERVAL)

        logging.info("game_loops: Collision loop has stopped")

    def state_loop(self, running):
        """Main game state update loop"""
        fuel_counter = 0
        score_counter = 0
        frame_start_time = time.time()
        
        while running():
            try:
                loop_start = time.time()
                
                with self.game_state.state_lock:
                    if not self.game_state.STATE_RUNNING:
                        time.sleep(self.STATE_UPDATE_INTERVAL)
                        continue

                    # Calculate delta time for smooth updates
                    current_time = time.time()
                    delta_time = current_time - frame_start_time
                    frame_start_time = current_time

                    # Update game state
                    self._update_game_state(delta_time, fuel_counter, score_counter)
                    
                    # Update counters
                    fuel_counter = (fuel_counter + 1) % self.FUEL_RATE
                    score_counter = (score_counter + 1) % self.SCORE_RATE

                # Track performance
                with self.stats_lock:
                    self.performance_stats['state_time'] = time.time() - loop_start
                    self.performance_stats['frame_count'] += 1
                    # logging.info("game_loops: Updated state_time and frame_count performance stats")

                # Maintain update rate
                elapsed = time.time() - loop_start
                if elapsed < self.STATE_UPDATE_INTERVAL:
                    time.sleep(self.STATE_UPDATE_INTERVAL - elapsed)
                    
            except Exception as e:
                logging.error(f"game_loops: Error in state loop: {e}")
                time.sleep(self.STATE_UPDATE_INTERVAL)

        logging.info("game_loops: State loop has stopped")

    def _update_game_state(self, delta_time, fuel_counter, score_counter):
        """Update game state with delta time"""
        try:
            # First check if game is over
            if self.game_state.is_game_over():
                return  # Don't update anything if game is over

            # Update fuel
            if fuel_counter == 0:
                fuel_decrease = max(1, int(delta_time * self.FUEL_RATE))
                self.game_state.update_fuel(-fuel_decrease)

            # Update score
            if score_counter == 0:
                score_increase = max(1, int(delta_time * self.SCORE_RATE))
                self.game_state.update_score(score_increase)

            # Update entity positions based on delta time
            self._update_entity_positions(delta_time)
            
        except Exception as e:
            logging.error(f"game_loops: Error in _update_game_state: {e}")

    def _update_entity_positions(self, delta_time):
        """Update entity positions with interpolation"""
        try:
            # Update missile positions
            for missile in self.game_state.missiles:
                if hasattr(missile, 'velocity'):
                    missile.x += missile.velocity.x * delta_time
                    missile.y += missile.velocity.y * delta_time

            # Update enemy positions
            for enemy in self.game_state.enemies:
                if hasattr(enemy, 'velocity'):
                    enemy.x += enemy.velocity.x * delta_time
                    enemy.y += enemy.velocity.y * delta_time
                    
            # Update fuel depot positions
            for depot in self.game_state.fuel_depots:
                if hasattr(depot, 'velocity'):
                    depot.x += depot.velocity.x * delta_time
                    depot.y += depot.velocity.y * delta_time
                    
        except Exception as e:
            logging.error(f"game_loops: Error in _update_entity_positions: {e}")

    def get_performance_stats(self):
        """Get current performance statistics"""
        with self.stats_lock:
            return {
                'collision_time': self.performance_stats['collision_time'],
                'state_time': self.performance_stats['state_time'],
                'frame_count': self.performance_stats['frame_count'],
                'fps': self.performance_stats['frame_count'] / 
                       (time.time() - self.last_update_time)
            }

    def reset_performance_stats(self):
        """Reset performance tracking statistics"""
        with self.stats_lock:
            self.performance_stats = {
                'collision_time': 0,
                'state_time': 0,
                'frame_count': 0
            }
            self.last_update_time = time.time()
            # logging.info("game_loops: Performance stats reset")