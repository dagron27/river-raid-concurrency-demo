# client/game/game_logic.py
import logging
from shared.config import BOARD_WIDTH, BOARD_HEIGHT
from shared.entities import Player, EnemyB, EnemyJ, EnemyH, FuelDepot, Missile

class GameLogic:
    def __init__(self, game_state):
        self.game_state = game_state
        self.reset_game()

    def reset_game(self):
        """Initialize or reset all game state"""
        try:
            self.player = Player(BOARD_WIDTH // 2, BOARD_HEIGHT - 1.5)
            self.enemies = []
            self.missiles = []
            self.fuel_depots = []
            self.score = 0
            self.lives = 3
            self.fuel = 100
            self.game_state = "running"
            logging.info("Game has been reset on client")
        except Exception as e:
            logging.warning(f"Warning in reset_game: {e}")

    def update_game_state(self, game_state):
        """Update game state with server data"""
        try:
            #logging.info(f"Updating game state with: {game_state}")
            # Update player position
            self.player.x = game_state['p']['x']
            self.player.y = game_state['p']['y']
            
            # Update basic game state
            self.score = game_state['s']
            self.lives = game_state['l']
            self.fuel = game_state['u']
            self.game_state = game_state['g']

            # Clear and update entities
            self.enemies.clear()
            self.missiles.clear()
            self.fuel_depots.clear()

            # Recreate enemies
            for enemy in game_state['e']:
                if enemy['t'] == 'B':
                    self.enemies.append(EnemyB(enemy['x'], enemy['y'], self))
                elif enemy['t'] == 'J':
                    self.enemies.append(EnemyJ(enemy['x'], enemy['y'], self))
                elif enemy['t'] == 'H':
                    self.enemies.append(EnemyH(enemy['x'], enemy['y'], self))

            # Recreate missiles
            for missile in game_state['m']:
                self.missiles.append(Missile(missile['x'], missile['y'], missile['t']))

            # Recreate fuel depots
            for depot in game_state['f']:
                self.fuel_depots.append(FuelDepot(depot['x'], depot['y']))
        except KeyError as e:
            logging.error(f"Key error in update_game_state: {e}")
        except Exception as e:
            logging.warning(f"Warning in update_game_state: {e}")

    def get_entity_at(self, x, y):
        """Get entity at specific coordinates"""
        try:
            # Check player
            if self.player.x == x and self.player.y == y:
                return self.player

            # Check enemies
            for enemy in self.enemies:
                if enemy.x == x and enemy.y == y:
                    return enemy

            # Check missiles
            for missile in self.missiles:
                if missile.x == x and missile.y == y:
                    return missile

            # Check fuel depots
            for depot in self.fuel_depots:
                if depot.x == x and depot.y == y:
                    return depot

            return None
        except Exception as e:
            logging.warning(f"Warning in get_entity_at: {e}")
            return None

    def is_position_occupied(self, x, y):
        """Check if position is occupied by any entity"""
        try:
            return self.get_entity_at(x, y) is not None
        except Exception as e:
            logging.warning(f"Warning in is_position_occupied: {e}")
            return False

    def is_valid_position(self, x, y):
        """Check if position is within game bounds"""
        try:
            return 0 <= x < BOARD_WIDTH and 0 <= y < BOARD_HEIGHT
        except Exception as e:
            logging.warning(f"Warning in is_valid_position: {e}")
            return False

    def get_game_state(self):
        """Get current game state for rendering"""
        try:
            return {
                'player': {
                    'x': self.player.x,
                    'y': self.player.y
                },
                'enemies': [{
                    'x': enemy.x,
                    'y': enemy.y,
                    'type': enemy.__class__.__name__[5]  # Extract B, J, or H from class name
                } for enemy in self.enemies],
                'missiles': [{
                    'x': missile.x,
                    'y': missile.y,
                    'type': missile.type
                } for missile in self.missiles],
                'fuel_depots': [{
                    'x': depot.x,
                    'y': depot.y
                } for depot in self.fuel_depots],
                'score': self.score,
                'lives': self.lives,
                'fuel': self.fuel,
                'game_state': self.game_state
            }
        except Exception as e:
            logging.warning(f"Warning in get_game_state: {e}")
            return {}
