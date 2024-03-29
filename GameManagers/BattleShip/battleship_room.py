import random
import threading
import time

from GameManagers.base_room import BaseRoom
from loguru import logger as logging

try:
    from .board import Board
    from .ship import Ship
    from .ai import BattleShipAI
except SyntaxError:
    pass


class BattleShip(BaseRoom):
    playable = True

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
            "spectator_fog_of_war"] if "spectator_fog_of_war" in starting_config else False
        self.spectator_fog_of_war = False
        # Check if the AI was able to be imported
        if "BattleShipAI" in globals():
            self.ai_enable = starting_config["ai_enable"] if "ai_enable" in starting_config else True
        else:
            logging.warning("BattleShip AI could not be imported. AI disabled.")
            self.ai_enable = False

        self.boards = [Board(self.board_size, ships), Board(self.board_size, ships)]

        self.both_ready = False
        self.current_player = self.users[0] if len(self.users) > 0 else None
        self.winner = None
        self.game_over = False

    def database_init(self):
        pass

    def user_join(self, user):
        user.join_room(self)
        if user in self.users:
            return
        if len(self.users) >= self.max_users:
            self.spectators.append(user)
            return
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

    """
    Example of a board state:
    {
        "state": "Awaiting Boards...",
        "current_player": playerObject,
        "your_move": True,
        "board": boardObject(no_fog_of_war),
        "enemy_board": boardObject(fog_of_war),
        "allow_place_ships": True,
        "board_size": 10,
    }
    """
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
                    "current_player": self.current_player.encode(),
                    "board": self.boards[0].encode_friendly(),
                    "enemy_board": self.boards[1].encode_friendly(),
                    "board_size": self.board_size,
                    "allow_place_ships": False,
                    "your_move": False,
                }
            else:
                return {
                    "state": self.state,
                    "current_player": self.current_player.encode(),
                    "board": self.boards[0].encode_friendly(),
                    "enemy_board": self.boards[1].encode_friendly(),
                    "board_size": self.board_size,
                    "allow_place_ships": False,
                    "your_move": False
                }

    def get_board(self, user):
        if user in self.users:
            return self.boards[self.users.index(user)]
        return None

    def ai_thread(self):
        ai_exceptions = 0
        while not self.game_over:
            try:
                if isinstance(self.current_player, BattleShipAI):
                    # logging.info(self.users[1])
                    move = self.current_player.get_ai_move(self.boards[0])
                    logging.info(move)
                    self.post_move(self.users[1], move)
            except Exception as e:
                ai_exceptions += 1
                logging.exception(e)
                if ai_exceptions > 5:
                    self.game_over = True
                    self.winner = self.users[0]
                    self.users[1].online = False
                    for player in self.users + self.spectators:
                        player.room_updated = True
                    self.state = "[red]AI Error[/red]"
                    break
            time.sleep(random.uniform(0.5, 1.5))

    def post_move(self, user, move):

        if len(self.users) == 1 and self.ai_enable:
            self.users.append(BattleShipAI(self.boards[1], self))
            self.current_player = self.users[0]
            threading.Thread(target=self.ai_thread, daemon=True).start()

        for player in self.users + self.spectators:
            player.room_updated = True

        if not self.both_ready:
            logging.debug(move)
            if "placed_ships" not in move:
                return {"error": "No placement data"}
            for ship in move["placed_ships"]:
                ship_obj = self.boards[self.users.index(user)].get_ship(ship["id"])
                if not self.boards[self.users.index(user)].place_ship(ship_obj, ship["x"], ship["y"],
                                                                      ship["direction"]):
                    return {"error": "Invalid ship placement."}
                logging.info(f"User {user.username} placed a ship of size {ship['size']} at ({ship['x']}, {ship['y']})"
                             f" facing {ship['direction']}")
            if [board.ready() for board in self.boards] == [True, True]:
                self.state = "In Progress"
                self.both_ready = True
                self.current_player = self.users[0]
                logging.info(f"{self.room_id} both players ready, starting game")
        else:
            if user.user_id != self.current_player.user_id:
                logging.info(f"{user.username} tried to make a move out of turn.")
                return {"error": "It is not your turn."}

            if len(self.users) == 2:
                self.current_player = self.users[1] if self.current_player == self.users[0] else self.users[0]
            else:
                self.current_player = self.users[0]

            # Check if the move has already been made
            if self.get_board(self.current_player).board[move["x"]][move["y"]] != 0:
                self.current_player = self.users[1] if self.current_player == self.users[0] else self.users[0]
                return {"error": "You have already made this move."}

            if self.get_board(self.current_player).is_hit(move["x"], move["y"]):
                logging.info(f"{user.username} hit ({move['x']}, {move['y']})")
                if self.get_board(self.current_player).all_sunk():
                    self.state = "Game Over"
                    self.game_over = True
                    self.winner = user
                    logging.info(f"{user.username} won {self.room_id}")

        return {"success": True}
