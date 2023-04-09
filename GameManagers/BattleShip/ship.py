class Ship:

    def __init__(self, id, size, x=None, y=None, direction='horizontal'):
        self.size = size
        self.id = id
        self.health = [True for _ in range(size)]
        self.x = x
        self.y = y
        self.direction = direction
        self.sunk = False
        self.placed = False

    def is_hit(self, x, y, is_shot):
        if self.direction == "horizontal":
            if self.x <= x < self.x + self.size and self.y == y:
                if is_shot:
                    self.health[x - self.x] = False
                    if not any(self.health):
                        self.sunk = True
                return True
        else:
            if self.y <= y < self.y + self.size and self.x == x:
                if is_shot:
                    self.health[y - self.y] = False
                    if not any(self.health):
                        self.sunk = True
                return True
        return False

    def encode_friendly(self):
        return {
            "id": self.id,
            "size": self.size,
            "x": self.x,
            "y": self.y,
            "direction": self.direction,
            "sunk": self.sunk,
            "placed": self.placed
        }

    def encode_enemy(self):
        return {
            "id": self.id,
            "size": self.size,
            "sunk": self.sunk,
            "placed": self.placed
        }
