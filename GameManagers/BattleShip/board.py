class Board:

    def __init__(self, size, ships):
        self.size = size
        self.board = [[0 for _ in range(size)] for _ in range(size)]
        self.ships = [BattleShip.Ship(x + 1) for x in range(ships)]

    def get_ship(self, size):
        for ship in self.ships:
            if ship.size == size:
                return ship
        return None

    def place_ship(self, ship, x, y, direction):
        # Check if the ship is in bounds and not overlapping
        if x > self.size or y > self.size or 0 > x or 0 > y:
            return False

        if direction == "horizontal":
            if x + ship.size > self.size:
                return False
        else:
            if y + ship.size > self.size:
                return False

        # Check if the ship is overlapping with another ship
        for other_ship in self.ships:
            if other_ship.placed:
                # Use the 'is_hit' method to check each coordinate of the this ship
                for i in range(ship.size):
                    if direction == "horizontal":
                        if other_ship.is_hit(x + i, y, False):
                            return False
                    else:
                        if other_ship.is_hit(x, y + i, False):
                            return False

        # Place the ship
        ship.x = x
        ship.y = y
        ship.direction = direction
        ship.placed = True
        return True

    def is_hit(self, x, y):
        for ship in self.ships:
            if ship.is_hit(x, y, True):
                self.board[x][y] = 1
                return True
        self.board[x][y] = 2
        return False

    def encode_friendly(self):
        return {
            "board": self.board,
            "ships": [ship.encode_friendly() for ship in self.ships]
        }

    def encode_enemy(self):
        return {
            "board": self.board,
            "ships": [ship.encode_enemy() for ship in self.ships]
        }

    def ready(self):
        for ship in self.ships:
            if not ship.placed:
                return False
        return True

    def all_sunk(self):
        for ship in self.ships:
            if not ship.sunk:
                return False
        return True