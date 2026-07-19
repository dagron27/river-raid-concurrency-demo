import random
from config import BOARD_WIDTH, BOARD_HEIGHT
from entities import Player, Obstacle, FuelDepot, Missile
import threading
import time
class GameLogic:
    
    def __init__(self):
        self.reset_game()
       
    def reset_game(self):
        self.player = Player(BOARD_WIDTH // 2, BOARD_HEIGHT - 1)
        self.obstacles = []
        self.missiles = []
        self.fuel_depots = []
        self.score = 0
        self.lives = 3
        self.fuel = 100
        self.game_running = True
        self.mutex_lock = threading.Lock()
        self.movement_thread = threading.Thread(target=self.move_obstacles)
        self.movement_thread.start()
    def update_game_state(self):
        if not self.game_running:
            if self.movement_thread.is_alive():
                self.movement_thread.join()
            return

        # Add new obstacles
        if random.random() < 0.2:
            self.obstacles.append(Obstacle(random.randint(0, BOARD_WIDTH - 1), 0, random.randint(-1,1)))

        # Add new fuel depots
        if random.random() < 0.05:
            self.fuel_depots.append(FuelDepot(random.randint(0, BOARD_WIDTH - 1), 0))


        # Decrease fuel
        self.fuel -= 1
        if self.fuel <= 0:
            self.lives -= 1
            self.fuel = 100
            if self.lives == 0:
                self.game_running = False

        self.score += 1

    def move_obstacles(self):
        while self.game_running:
            print("moveing Obstacles")
            with self.mutex_lock:
                print("in lock")

                #move missiles
                for missile in self.missiles:
                    missile.move()

                for obs in self.obstacles:
                    if (obs.x + obs.direction) < 0 or (obs.x + obs.direction) > (BOARD_WIDTH -1 ):
                        obs.direction = -obs.direction
                    obs.move()

                # Move fuel depots
                for depot in self.fuel_depots:
                    depot.move()

               
                
                self.check_collisions()
            print("out of lock")
            time.sleep(self.player.speed)
    def check_collisions(self):
        for obs in self.obstacles:
            if obs.x == self.player.x and obs.y == self.player.y:
                self.lives -= 1
                self.obstacles.remove(obs)
                if self.lives == 0:
                    self.game_running = False
                break

        for depot in self.fuel_depots:
            if depot.x == self.player.x and depot.y == self.player.y:
                self.fuel = min(100, self.fuel + 50)
                self.fuel_depots.remove(depot)

        for missile in self.missiles:
            for obs in self.obstacles:
                if missile.x == obs.x and missile.y == obs.y:
                    self.score += 10
                    self.obstacles.remove(obs)
                    self.missiles.remove(missile)
                    break

        self.obstacles = [obs for obs in self.obstacles if obs.y < BOARD_HEIGHT]
        self.missiles = [missile for missile in self.missiles if missile.y >= 0]
        self.fuel_depots = [depot for depot in self.fuel_depots if depot.y < BOARD_HEIGHT]
