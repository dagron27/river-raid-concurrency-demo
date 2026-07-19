# shared/entities.py
import random
import logging
from shared.config import SCALE, BOARD_WIDTH, BOARD_HEIGHT

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.fuel = 100
        self.lives = 3
        self.speed = 1
        self.missile_type = "straight"
        self.width = SCALE
        self.height = SCALE
        self.color = "blue"

    def move(self, direction):
        try:
            if direction == "left":
                self.x = max(0, self.x - 1)
            elif direction == "right":
                self.x = min(BOARD_WIDTH - 1, self.x + 1)
            elif direction == "accelerate":
                self.speed = min(3, self.speed + 1)
            elif direction == "decelerate":
                self.speed = max(1, self.speed - 1)
        except Exception as e:
            logging.warning(f"Warning in Player.move: {e}")

    def shoot(self):
        try:
            return Missile(self.x + 0.5, self.y - 1, self.missile_type)
        except Exception as e:
            logging.warning(f"Warning in Player.shoot: {e}")

    def switch_missile(self):
        try:
            self.missile_type = "guided" if self.missile_type == "straight" else "straight"
        except Exception as e:
            logging.warning(f"Warning in Player.switch_missile: {e}")

class Enemy:
    """Base enemy class"""
    def __init__(self, x, y, enemy_type, game_logic):
        self.x = x
        self.y = y
        self.type = enemy_type
        self.game_logic = game_logic
        self.running = True
        self.width = SCALE
        self.height = SCALE
        self.color = "red"

    def move(self):
        """Base movement method"""
        raise NotImplementedError("This method should be overridden by subclasses")

class EnemyB(Enemy):
    """Boat type enemy - moves horizontally and downward"""
    def __init__(self, x, y, game_logic):
        super().__init__(x, y, "B", game_logic)
        self.width = SCALE * 3
        self.height = SCALE
        self.color = "purple"
        self.vertical_direction = 1
        self.horizontal_direction = random.choice([-1, 0, 1])
        self.vertical_speed = 0.5
        self.horizontal_speed = random.uniform(0.3, 0.7)

    def move(self):
        """Move boat type enemy"""
        self.y += self.vertical_direction * self.vertical_speed
        self.x += self.horizontal_direction * self.horizontal_speed

        # Boundary checking
        if self.x < 0:  
            self.horizontal_direction = 1  
        elif self.x + 3 > BOARD_WIDTH:  
            self.horizontal_direction = -1  

        # Check if out of bounds
        if self.y > BOARD_HEIGHT + 3:
            self.running = False

class EnemyJ(Enemy):
    """Jet type enemy - moves straight down quickly"""
    def __init__(self, x, y, game_logic):
        super().__init__(x, y, "J", game_logic)
        self.width = SCALE * 1.5
        self.height = SCALE * 2
        self.color = "orange"
        self.direction = random.uniform(1, 2)

    def move(self):
        """Move jet type enemy"""
        self.y += self.direction
        if self.y > BOARD_HEIGHT + 3:
            self.running = False

class EnemyH(Enemy):
    """Helicopter type enemy - moves erratically"""
    def __init__(self, x, y, game_logic):
        super().__init__(x, y, "H", game_logic)
        self.width = SCALE * 2
        self.height = SCALE * 0.75
        self.color = "white"
        self.vertical_direction = random.choice([-1, 0, 1])
        self.horizontal_direction = random.choice([-1, 0, 1])
        self.vertical_speed = random.uniform(0.2, 0.8)
        self.horizontal_speed = random.uniform(0.2, 0.8)

    def move(self):
        """Move helicopter type enemy"""
        # Random direction changes
        if random.randrange(0, 10) > 7:
            self.vertical_direction = random.choice([-1, 0, 1])
            self.horizontal_direction = random.choice([-1, 0, 1])
            self.vertical_speed = random.uniform(0.2, 0.8)
            self.horizontal_speed = random.uniform(0.2, 0.8)
        
        # Move
        self.y += self.vertical_direction * self.vertical_speed
        self.x += self.horizontal_direction * self.horizontal_speed

        # Boundary checking
        if self.x < 0:
            self.horizontal_direction = 1  
        elif self.x + 2 > BOARD_WIDTH:  
            self.horizontal_direction = -1
        if self.y < 0:
            self.vertical_direction = 1   
        if self.y > BOARD_HEIGHT + 3: 
            self.running = False

class FuelDepot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = SCALE 
        self.height = SCALE * 0.75
        self.color = "green"

    def move(self):
        try:
            self.y += 1
            if self.y < BOARD_HEIGHT + 3: 
                self.running = False
        except Exception as e:
            logging.warning(f"Warning in FuelDepot.move: {e}")

class Missile:
    def __init__(self, x, y, missile_type):
        self.x = x
        self.y = y
        self.missile_type = missile_type
        self.width = SCALE * 0.05
        self.height = SCALE * 0.5
        self.color = "yellow"

    def move(self):
        try:
            self.y -= 1  # Straight missiles move up
            # Termination condition based on new limits (5 units above the top of the canvas) 
            if self.y < -3: 
                self.running = False
        except Exception as e:
            logging.warning(f"Warning in Missile.move: {e}")