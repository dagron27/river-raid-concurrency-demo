# server/game/entity_manager.py
import logging
import random
import time
import threading
from shared.config import BOARD_WIDTH, BOARD_HEIGHT
from shared.entity_pool import EntityPool

class EntityManager:
    """Manages all game entities, their movement threads, and entity pooling"""
    def __init__(self, game_state):
        self.game_state = game_state
        self.entity_pool = EntityPool(max_size=20)

        # Spawn rates and weights
        self.SPAWN_RATES = {
            'enemies': {
                'B': 0.07,  # Boat
                'J': 0.05,  # Jet
                'H': 0.03   # Helicopter
            },
            'fuel': 0.2
        }

        # Timing controls
        self.spawn_cooldowns = {
            'B': 1.0,    # Time between boat spawn attempts
            'J': 1.5,    # Time between jet spawn attempts
            'H': 2.0,    # Time between helicopter spawn attempts
            'fuel': 3.0  # Time between fuel depot spawn attempts
        }
        self.last_spawn_time = {
            'B': 0,
            'J': 0,
            'H': 0,
            'fuel': 0
        }
        
        # Movement timing
        self.movement_interval = 0.2  # Base movement update interval
        self.missile_interval = 0.1   # Missile movement update interval
        self.fuel_interval = 0.2      # Fuel depot movement interval
        self.running = True
        
        # Create threads
        self.movement_threads = {
            'H': threading.Thread(target=self._h_movement_loop),
            'J': threading.Thread(target=self._j_movement_loop),
            'B': threading.Thread(target=self._b_movement_loop),
            'spawner': threading.Thread(target=self._spawner_loop),
            'missiles': threading.Thread(target=self._missile_loop),
            'fuel': threading.Thread(target=self._fuel_loop)
        }

    def start_movement_threads(self):
        """Start all movement threads"""
        for name, thread in self.movement_threads.items():
            if not thread.is_alive():
                thread.daemon = True
                thread.start()
                time.sleep(0.1)  # Small delay to ensure thread starts properly
                logging.info(f"entity_manager: Started {name} thread")

    def stop_movement_threads(self):
        """Stop all movement threads"""
        self.running = False
        
        for name, thread in self.movement_threads.items():
            if thread.is_alive():
                thread.join(timeout=1.0)
                if thread.is_alive():
                    logging.warning(f"entity_manager: {name} thread did not finish cleanly")
                else:
                    logging.info(f"entity_manager: Stopped {name} thread successfully")

    def release_entity(self, entity):
        """Centralized method to release entities back to the pool"""
        try:
            self.entity_pool.release(entity)
            logging.debug(f"entity_manager: Released {entity.type if hasattr(entity, 'type') else 'entity'} to pool")
        except Exception as e:
            logging.error(f"entity_manager: Error releasing entity to pool: {e}")

    def acquire_entity(self, entity_type, x, y, extra_args=None):
        """Centralized method to acquire entities from the pool"""
        try:
            entity = self.entity_pool.acquire(entity_type, x, y, *([extra_args] if extra_args else []))
            if entity:
                logging.debug(f"entity_manager: Acquired {entity_type} from pool")
            return entity
        except Exception as e:
            logging.error(f"entity_manager: Error acquiring {entity_type} from pool: {e}")
            return None

    def _process_entity_movement(self, entities, entity_type):
        """Generic entity movement processor with pool management"""
        moved_entities = []
        removed_entities = []
        
        for entity in entities:
            try:
                entity.move()
                if hasattr(entity, 'running') and not entity.running:
                    removed_entities.append(entity)
                    self.release_entity(entity)
                else:
                    moved_entities.append(entity)
            except Exception as e:
                logging.error(f"entity_manager: Error processing {entity_type} movement: {e}")
                removed_entities.append(entity)
                
        return moved_entities, removed_entities

    def _spawner_loop(self):
        """Enhanced spawner loop with pool management"""
        while self.running:
            try:
                current_time = time.time()
                
                # Enemy spawning
                for enemy_type, rate in self.SPAWN_RATES['enemies'].items():
                    if (current_time - self.last_spawn_time[enemy_type] >= self.spawn_cooldowns[enemy_type] and 
                        random.random() < rate):
                        
                        x = random.randint(0, int(BOARD_WIDTH) - 1)
                        enemy = self.acquire_entity(enemy_type, x, 0, self.game_state)
                        
                        if enemy:  # Only add if pool acquisition succeeded
                            with self.game_state.state_lock:
                                self.game_state.add_enemy(enemy)
                                self.last_spawn_time[enemy_type] = current_time
                            
            except Exception as e:
                logging.warning(f"entity_manager: Warning in spawner loop: {e}")
            time.sleep(0.1)

    def _h_movement_loop(self):
        """Helicopter movement loop with pool management"""
        while self.running:
            try:
                with self.game_state.state_lock:
                    h_enemies = [e for e in self.game_state.enemies if e.type == 'H']
                    _, removed = self._process_entity_movement(h_enemies, 'H')
                    for enemy in removed:
                        self.game_state.remove_enemy(enemy)
                        
            except Exception as e:
                logging.warning(f"entity_manager: Warning in H movement loop: {e}")
            time.sleep(self.movement_interval)

    def _j_movement_loop(self):
        """Jet movement loop with pool management"""
        while self.running:
            try:
                with self.game_state.state_lock:
                    j_enemies = [e for e in self.game_state.enemies if e.type == 'J']
                    _, removed = self._process_entity_movement(j_enemies, 'J')
                    for enemy in removed:
                        self.game_state.remove_enemy(enemy)
                        
            except Exception as e:
                logging.warning(f"entity_manager: Warning in J movement loop: {e}")
            time.sleep(self.movement_interval)

    def _b_movement_loop(self):
        """Boat movement loop with pool management"""
        while self.running:
            try:
                with self.game_state.state_lock:
                    b_enemies = [e for e in self.game_state.enemies if e.type == 'B']
                    _, removed = self._process_entity_movement(b_enemies, 'B')
                    for enemy in removed:
                        self.game_state.remove_enemy(enemy)
                        
            except Exception as e:
                logging.warning(f"entity_manager: Warning in B movement loop: {e}")
            time.sleep(self.movement_interval)

    def _missile_loop(self):
        """Missile movement loop with pool management"""
        while self.running:
            try:
                with self.game_state.state_lock:
                    missiles = self.game_state.missiles[:]
                    _, removed = self._process_entity_movement(missiles, 'missile')
                    for missile in removed:
                        self.game_state.remove_missile(missile)
                        self.release_entity(missile)
                        
            except Exception as e:
                logging.warning(f"entity_manager: Warning in missile loop: {e}")
            time.sleep(self.missile_interval)

    def _fuel_loop(self):
        """Fuel depot management with pool handling"""
        while self.running:
            try:
                with self.game_state.state_lock:
                    current_time = time.time()
                    
                    # Spawn new fuel depot if conditions are met
                    if (current_time - self.last_spawn_time['fuel'] >= self.spawn_cooldowns['fuel'] and
                        random.random() < self.SPAWN_RATES['fuel']):
                        x = random.randint(0, int(BOARD_WIDTH) - 1)
                        depot = self.acquire_entity('fuel', x, 0)
                        if depot:
                            self.game_state.add_fuel_depot(depot)
                            self.last_spawn_time['fuel'] = current_time

                    # Move existing fuel depots
                    for depot in self.game_state.fuel_depots[:]:
                        depot.move()
                        if depot.y >= BOARD_HEIGHT + 3:  # Beyond screen bounds
                            self.game_state.remove_fuel_depot(depot)
                            self.release_entity(depot)
                            
            except Exception as e:
                logging.warning(f"entity_manager: Warning in fuel loop: {e}")
            time.sleep(self.fuel_interval)

    def adjust_spawn_rates(self, difficulty_factor=1.0):
        """Adjust spawn rates based on difficulty"""
        try:
            self.SPAWN_RATES['enemies'] = {
                'B': min(0.2, 0.07 * difficulty_factor),
                'J': min(0.15, 0.05 * difficulty_factor),
                'H': min(0.1, 0.03 * difficulty_factor)
            }
            logging.info(f"entity_manager: Adjusted spawn rates with difficulty factor {difficulty_factor}")
        except Exception as e:
            logging.error(f"entity_manager: Error adjusting spawn rates: {e}")

    def reset(self):
        """Reset entity manager state"""
        try:
            # Reset spawn timers
            current_time = time.time()
            for entity_type in self.last_spawn_time:
                self.last_spawn_time[entity_type] = current_time
                
            # Clear entity pool
            self.entity_pool.clear()
            
            logging.info("entity_manager: Reset completed")
        except Exception as e:
            logging.error(f"entity_manager: Error during reset: {e}")