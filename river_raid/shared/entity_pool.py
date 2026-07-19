# shared/entity_pool.py
import threading
import queue
import logging
from shared.entities import EnemyB, EnemyJ, EnemyH, FuelDepot, Missile

class EntityPool:
    """Thread-safe object pool with optimized synchronization"""
    def __init__(self, max_size=20):
        self.max_size = max_size
        self.pools = {
            'B': queue.Queue(max_size),
            'J': queue.Queue(max_size),
            'H': queue.Queue(max_size),
            'fuel': queue.Queue(max_size),
            'missile': queue.Queue(max_size * 2)  # More missiles needed
        }
        self.single_lock = threading.Lock()

    def _create_entity(self, entity_type, x, y, game_logic=None):
        """Create a new entity based on type"""
        if entity_type == 'B':
            return EnemyB(x, y, game_logic)
        elif entity_type == 'J':
            return EnemyJ(x, y, game_logic)
        elif entity_type == 'H':
            return EnemyH(x, y, game_logic)
        elif entity_type == 'fuel':
            return FuelDepot(x, y)
        elif entity_type == 'missile':
            return Missile(x, y, "straight")

    def acquire(self, entity_type, x, y, game_logic=None):
        """Get an entity with optimized locking"""
        with self.single_lock:
            try:
                entity = self.pools[entity_type].get_nowait()
                # Reset entity state
                entity.x = x
                entity.y = y
                entity.running = True
                if hasattr(entity, 'game_logic'):
                    entity.game_logic = game_logic
                logging.debug(f"Reused {entity_type} from pool")
                return entity
            except queue.Empty:
                # Create new if pool is empty
                entity = self._create_entity(entity_type, x, y, game_logic)
                logging.debug(f"Created new {entity_type}")
                return entity

    def release(self, entity):
        """Return entity to pool with optimized locking"""
        entity_type = None
        
        # Determine entity type
        if isinstance(entity, EnemyB):
            entity_type = 'B'
        elif isinstance(entity, EnemyJ):
            entity_type = 'J'
        elif isinstance(entity, EnemyH):
            entity_type = 'H'
        elif isinstance(entity, FuelDepot):
            entity_type = 'fuel'
        elif isinstance(entity, Missile):
            entity_type = 'missile'

        if entity_type:
            with self.single_lock:
                try:
                    self.pools[entity_type].put_nowait(entity)
                    logging.debug(f"Released {entity_type} to pool")
                except queue.Full:
                    logging.debug(f"Pool full for {entity_type}, discarding entity")
                    pass  # Let it be garbage collected