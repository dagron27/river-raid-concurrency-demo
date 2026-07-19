# client/game/canvas_gui.py
import tkinter as tk
import logging
from shared.config import CANVAS_WIDTH, CANVAS_HEIGHT, SCALE

class GameCanvas(tk.Canvas):
    def __init__(self, parent, game_logic):
        super().__init__(parent, width=1000, height=950, bg="gray")
        self.game_logic = game_logic
        self.scale = SCALE  # Define scaling factor
        self.width = CANVAS_WIDTH
        self.height = CANVAS_HEIGHT
        self.pack()

    def update_canvas(self):
        try:
            self.delete("all")
            if self.game_logic.game_state == "running":
                # Draw player
                self._draw_entity(self.game_logic.player)

                # Draw fuel depots
                for depot in self.game_logic.fuel_depots:
                    self._draw_entity_circle(depot)

                # Draw missiles
                for missile in self.game_logic.missiles:
                    self._draw_missile(missile)

                # Draw enemies
                for enemy in self.game_logic.enemies:
                    self._draw_entity(enemy)

            else:
                self.display_game_over()
        except Exception as e:
            logging.warning(f"Warning in update_canvas: {e}")

    def _draw_entity(self, entity):
        """Draw a rectangular entity (player, enemies, fuel depots)"""
        try:
            self.create_rectangle(
                entity.x * self.scale,
                entity.y * self.scale,
                entity.x * self.scale + entity.width,
                entity.y * self.scale + entity.height,
                fill=entity.color
            )
        except Exception as e:
            logging.warning(f"Warning in _draw_entity: {e}")

    def _draw_entity_circle(self, entity): 
        """Draw a circular entity""" 
        try:
            center_x = entity.x * self.scale + entity.width / 2 
            center_y = entity.y * self.scale + entity.height / 2 
            radius = entity.width / 2 
            
            self.create_oval( 
                center_x - radius, 
                center_y - radius, 
                center_x + radius, 
                center_y + radius, 
                fill=entity.color
            )
        except Exception as e:
            logging.warning(f"Warning in _draw_entity_circle: {e}")
    
    def _draw_missile(self, missile):
        """Draw a missile as a vertical line"""
        try:
            center_x = missile.x * self.scale + (missile.width / 2)
            self.create_line(
                center_x,
                missile.y * self.scale,
                center_x,
                missile.y * self.scale + missile.height,
                fill=missile.color,
                width=missile.width
            )
        except Exception as e:
            logging.warning(f"Warning in _draw_missile: {e}")

    def display_game_over(self):
        """Display game over screen"""
        try:
            self.delete("all")
            self.create_text(
                self.width / 2,
                self.height / 2,
                text="Game Over",
                fill="red",
                font=("Helvetica", 100)
            )
        except Exception as e:
            logging.warning(f"Warning in display_game_over: {e}")