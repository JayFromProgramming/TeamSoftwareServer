from GameManagers.base_room import BaseRoom
import logging

logging = logging.getLogger(__name__)


class BattleShip(BaseRoom):
    playable = True

    class Ship:

        def __init__(self, size, x=None, y=None, direction=None):
            self.size = size
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
                "size": self.size,
                "x": self.x,
                "y": self.y,
                "direction": self.direction,
                "sunk": self.sunk,
                "placed": self.placed
            }

        def encode_enemy(self):
            return {
                "size": self.size,
                "sunk": self.sunk,
                "placed": self.placed
            }

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

    def __init__(self, database, host=None, name=None, starting_config=None, from_save=False, **kwargs):
        super().__init__(database, name, host, starting_config)
        self.database_init()
        if starting_config is None:
            starting_config = {}
        self.max_users = 2
        self.state = "Awaiting Boards..."
        self.board_size = starting_config["board_size"] if "board_size" in starting_config else 10
        ships = starting_config["ships"] if "ships" in starting_config else 5
        self.spectator_fog_of_war = starting_config[
            "spectator_fog_of_war"] if "spectator_fog_of_war" in starting_config else True

        self.boards = [self.Board(self.board_size, ships), self.Board(self.board_size, ships)]

        self.both_ready = False
        self.current_player = self.users[0] if len(self.users) > 0 else None
        self.winner = None

    def database_init(self):
        pass

    def user_join(self, user):
        user.join_room(self)
        if user in self.users:
            return
        if len(self.users) >= self.max_users:
            if self.allow_spectators:
                self.spectators.append(user)
        else:
            self.users.append(user)

    def user_leave(self, user):
        user.leave_room()
        if user in self.users:
            self.users.remove(user)
        elif user in self.spectators:
            self.spectators.remove(user)

    def frequent_update(self):
        return {
            "players": [user.encode() for user in self.users],
            "spectators": [user.encode() for user in self.spectators]
        }

    def get_game_info(self):
        info = super().get_game_info()
        info["board_size"] = self.board_size
        return info

    def get_board_state(self, user):
        if user in self.users:
            return {
                "state": self.state,
                "current_player": self.current_player.encode(),
                "your_move": True if user == self.current_player else False,
                "board": self.boards[self.users.index(user)].encode_friendly(),
                "enemy_board": self.boards[self.users.index(user) - 1].encode_enemy(),
                "allow_place_ships": self.boards[self.users.index(user)].ready() is False,
                "board_size": self.board_size,
            }
        elif user in self.spectators:
            if self.spectator_fog_of_war:
                return {
                    "state": self.state,
                    "current_player": self.current_player.user_id,
                    "board": self.boards[self.users.index(self.current_player)].encode_enemy(),
                    "enemy_board": self.boards[self.users.index(self.current_player) - 1].encode_enemy()
                }
            else:
                return {
                    "state": self.state,
                    "current_player": self.current_player.user_id,
                    "board": self.boards[self.users.index(self.current_player)].encode_friendly(),
                    "enemy_board": self.boards[self.users.index(self.current_player)].encode_friendly()
                }

    def post_move(self, user, move):

        for player in self.users + self.spectators:
            player.room_updated = True

        if not self.both_ready:
            logging.debug(move)
            if "placed_ships" not in move:
                return {"error": "No placement data"}
            for ship in move["placed_ships"]:
                ship_obj = self.boards[self.users.index(user)].get_ship(ship["size"])
                if not self.boards[self.users.index(user)].place_ship(ship_obj, ship["x"], ship["y"], ship["direction"]):
                    return {"error": "Invalid ship placement."}
                logging.info(f"User {user.username} placed a ship of size {ship['size']} at ({ship['x']}, {ship['y']})"
                                f" facing {ship['direction']}")
            if [board.ready() for board in self.boards] == [True, True]:
                self.state = "In Progress"
                self.both_ready = True
                self.current_player = self.users[0]
                logging.info(f"{self.room_id} both players ready, starting game")
        else:
            if user.hash_id != self.current_player.hash_id:
                logging.info(f"{user.username} tried to make a move out of turn.")
                return {"error": "It is not your turn."}

            if self.boards[self.users.index(user) - 1].is_hit(move["x"], move["y"]):
                logging.info(f"{user.username} hit ({move['x']}, {move['y']})")
                if self.boards[self.users.index(user) - 1].all_sunk():
                    self.state = "Game Over"
                    self.winner = user
                    logging.info(f"{user.username} won {self.room_id}")
                else:
                    self.current_player = self.users[self.users.index(user) - 1]

        return {"success": True}
