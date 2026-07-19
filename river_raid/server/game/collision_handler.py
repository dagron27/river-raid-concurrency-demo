import logging
from shared.config import SCALE, BOARD_WIDTH, BOARD_HEIGHT

class CollisionHandler:
    """Handles all collision detection and resolution in the game"""
    def __init__(self, game_state):
        self.game_state = game_state
        self.grid_size = 4  # Number of cells in each dimension
        self.grid_width = BOARD_WIDTH / self.grid_size
        self.grid_height = BOARD_HEIGHT / self.grid_size
        self.collision_grid = None
        
        # Performance tracking
        self.last_check_time = 0
        self.collision_count = 0

    def check_all_collisions(self):
        """Main collision detection method using two-phase spatial partitioning"""
        try:
            # Phase 1: Quick check if we need to proceed
            with self.game_state.state_lock:
                if self.game_state.game_state == self.game_state.STATE_GAME_OVER:
                    return
                
                # Take a snapshot of the game state
                enemies = list(self.game_state.enemies)  # Copy list
                missiles = list(self.game_state.missiles)
                fuel_depots = list(self.game_state.fuel_depots)
                player_x = self.game_state.player.x
                player_y = self.game_state.player.y
                
            # Phase 2: Build spatial partition grid (without lock)
            self.collision_grid = [[[] for _ in range(self.grid_size)] 
                                 for _ in range(self.grid_size)]
            
            # Populate grid with enemies
            for enemy in enemies:
                cell_x, cell_y = self._get_grid_cell(enemy.x, enemy.y)
                if 0 <= cell_x < self.grid_size and 0 <= cell_y < self.grid_size:
                    self.collision_grid[cell_y][cell_x].append(enemy)
            
            # Phase 3: Process different types of collisions
            # Get player's cell for vicinity checks
            player_cell = self._get_grid_cell(player_x, player_y)
            
            # Process collisions with appropriate locking
            with self.game_state.state_lock:
                # Check player-enemy collisions
                self._check_vicinity_collisions(player_cell)
                
                # Check missile-enemy collisions
                self._check_missile_collisions(missiles)
                
                # Check fuel depot collisions
                self._check_fuel_collisions(fuel_depots)
                
        except Exception as e:
            logging.error(f"collision_handler: Error in check_all_collisions: {e}")

    def _get_grid_cell(self, x, y):
        """Convert world coordinates to grid cell coordinates"""
        cell_x = int(x / self.grid_width)
        cell_y = int(y / self.grid_height)
        return (
            min(max(cell_x, 0), self.grid_size - 1),
            min(max(cell_y, 0), self.grid_size - 1)
        )

    def _check_vicinity_collisions(self, player_cell):
        """Check collisions in cells around the player"""
        try:
            cell_x, cell_y = player_cell
            
            # Check surrounding cells (including diagonal)
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    check_x = cell_x + dx
                    check_y = cell_y + dy
                    
                    if (0 <= check_x < self.grid_size and 
                        0 <= check_y < self.grid_size):
                        
                        # Check each enemy in this cell
                        for enemy in self.collision_grid[check_y][check_x]:
                            if self._is_colliding(self.game_state.player, enemy):
                                self._handle_player_enemy_collision(enemy)
                                
        except Exception as e:
            logging.error(f"collision_handler: Error in _check_vicinity_collisions: {e}")

    def _check_missile_collisions(self, missiles):
        """Check collisions between missiles and enemies"""
        try:
            for missile in missiles:
                if missile not in self.game_state.missiles:  # Skip if missile was already removed
                    continue
                    
                missile_cell = self._get_grid_cell(missile.x, missile.y)
                cell_x, cell_y = missile_cell
                
                # Check surrounding cells
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        check_x = cell_x + dx
                        check_y = cell_y + dy
                        
                        if (0 <= check_x < self.grid_size and 
                            0 <= check_y < self.grid_size):
                            
                            for enemy in self.collision_grid[check_y][check_x]:
                                if enemy in self.game_state.enemies:  # Verify enemy still exists
                                    if self._is_colliding(missile, enemy):
                                        self._handle_missile_enemy_collision(missile, enemy)
                                        break  # Break after first collision
                                    
        except Exception as e:
            logging.error(f"collision_handler: Error in _check_missile_collisions: {e}")

    def _check_fuel_collisions(self, fuel_depots):
        """Check collisions between player and fuel depots"""
        try:
            for depot in fuel_depots:
                if depot in self.game_state.fuel_depots:  # Verify depot still exists
                    if self._is_colliding(self.game_state.player, depot):
                        self._handle_fuel_collision(depot)
                    
        except Exception as e:
            logging.error(f"collision_handler: Error in _check_fuel_collisions: {e}")

    def _is_colliding(self, entity1, entity2):
        """Check collision between two entities using their dimensions"""
        try:
            # Get entity dimensions
            width1 = getattr(entity1, 'width', SCALE) / SCALE
            height1 = getattr(entity1, 'height', SCALE) / SCALE
            width2 = getattr(entity2, 'width', SCALE) / SCALE
            height2 = getattr(entity2, 'height', SCALE) / SCALE
            
            # Optimized AABB collision check
            return (entity1.x < entity2.x + width2 and
                    entity1.x + width1 > entity2.x and
                    entity1.y < entity2.y + height2 and
                    entity1.y + height1 > entity2.y)
                    
        except Exception as e:
            logging.error(f"collision_handler: Error in _is_colliding: {e}")
            return False

    def _handle_player_enemy_collision(self, enemy):
        """Handle collision between player and enemy"""
        try:
            if self.game_state.is_game_over():
                return
                
            self.game_state.update_lives(-1)
            self.game_state.remove_enemy(enemy)
                
        except Exception as e:
            logging.error(f"collision_handler: Error in _handle_player_enemy_collision: {e}")

    def _handle_missile_enemy_collision(self, missile, enemy):
        """Handle collision between missile and enemy"""
        try:
            self.game_state.update_score(10)
            self.game_state.remove_enemy(enemy)
            self.game_state.remove_missile(missile)
            logging.debug(f"collision_handler: Enemy destroyed! Score: {self.game_state.score}")
            
        except Exception as e:
            logging.error(f"collision_handler: Error in _handle_missile_enemy_collision: {e}")

    def _handle_fuel_collision(self, depot):
        """Handle collision between player and fuel depot"""
        try:
            self.game_state.update_fuel(50)
            self.game_state.remove_fuel_depot(depot)
            logging.debug(f"collision_handler: Fuel collected! Current fuel: {self.game_state.fuel}")
            
        except Exception as e:
            logging.error(f"collision_handler: Error in _handle_fuel_collision: {e}")