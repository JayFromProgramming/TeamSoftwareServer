import chess

from gamemanagers.base_room import BaseRoom
import logging

from user import User

logging = logging.getLogger(__name__)


class Chess(BaseRoom):

    def __init__(self, database, host, name, password=None, from_save=False):
        super().__init__(database, host, name, password)
        self.database_init()
        if from_save:
            self.load_game(from_save)
        else:
            self.state = "Idle"
            self.board = chess.Board()
            self.max_users = 2
            self.time_elapsed = 0
            self.time_remaining = 0
            self.score = 0
            self.last_move = None
            self.current_player = self.users[0]

    def database_init(self):
        # Create the table to save chess games if it doesn't exist
        self.database.execute("CREATE TABLE IF NOT EXISTS chess_game_saves ("
                              "game_id TEXT PRIMARY KEY, board_epd TEXT, white_hash TEXT, black_hash TEXT, "
                              "current_player TEXT, last_move TEXT, time_elapsed INTEGER, time_remaining INTEGER)")

    def user_join(self, user):
        user.join_room(self)
        if len(self.users) >= self.max_users:
            self.spectators.append(user)
        else:
            self.users.append(user)

    def user_leave(self, user):
        user.leave_room()
        self.users.remove(user)

    def frequent_update(self):
        """
        Data that is sent to the client every second
        :return:
        """
        return {
            "players": [user.encode() for user in self.users],
            "spectators": [user.encode() for user in self.spectators]
        }

    def get_board_state(self, user):
        return {
            "your_color": chess.WHITE if user == self.users[0] else chess.BLACK if user in self.users else None,
            "current_player": chess.WHITE if self.board.turn == chess.WHITE else chess.BLACK,
            "board": self.board.epd(hmvc=self.board.halfmove_clock, fmvn=self.board.fullmove_number),
            "last_move": str(self.last_move),
            "state": self.state,
            # "taken_pieces": self.taken_pieces
        }

    def check_win_conditions(self):
        if self.board.is_checkmate():
            self.state = "Checkmate"
            return True
        elif self.board.is_stalemate():
            self.state = "Stalemate"
            return True
        elif self.board.is_insufficient_material():
            self.state = "Insufficient Material"
            return True
        elif self.board.is_seventyfive_moves():
            self.state = "Seventyfive Moves"
            return True
        elif self.board.is_fivefold_repetition():
            self.state = "Fivefold Repetition"
            return True
        elif self.board.is_check():
            self.state = f"{self.current_player.username} is in check"
            return False
        else:
            return False

    def post_move(self, user, move):
        # print(user.username, move)

        for player in self.users + self.spectators:
            player.room_updated = True

        if user.user_id != self.current_player.user_id:
            logging.info(f"User {user.username} tried to move out of turn, current player is {self.current_player.username}")
            return {"error": "out_of_turn"}
        try:
            self.board.push_uci(move)
        except chess.IllegalMoveError:
            logging.info(f"User {user.username} tried to make an illegal move")
            return {"error": "illegal_move"}
        except chess.InvalidMoveError:
            logging.info(f"User {user.username} tried to make an invalid move")
            return {"error": "invalid_move"}
        except Exception as e:
            logging.info(f"User {user.username} cause an unknown error: {e}")
            return {"error": "unknown_error"}

        self.last_move = move
        self.state = "In Progress"

        # if self.board.is_capture(self.board.peek()):
        #     captured_piece = self.board.piece_at(self.board.peek().to_square)
        #
        #     logging.info(f"User {user.username} took a piece: {piece.symbol()},
        #     self.taken_pieces["white" if piece.color else "black"].append(piece.symbol())

        if len(self.users) == 2:
            self.current_player = self.users[1] if self.current_player == self.users[0] else self.users[0]
        else:
            self.current_player = self.users[0]

        if self.check_win_conditions():
            return {"result": self.state}

        return {"result": "success"}

    def save_game(self):
        """
        Saves the game to the database to be able to be loaded later
        :return:
        """
        self.database.execute("INSERT INTO chess_game_saves VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (self.room_id, self.board.epd(hmvc=self.board.halfmove_clock,
                                                            fmvn=self.board.fullmove_number),
                               self.users[0].hash_id, self.users[1].hash_id if len(self.users) == 2 else None,
                               self.board.turn, self.last_move, self.time_elapsed, self.time_remaining))
        self.database.execute("INSERT INTO room_saves VALUE (?, ?, ?)", (self.room_id, "chess", self.name))
        return {"room_id": self.room_id, "room_type": "chess"}

    def load_game(self, game_id):
        """
        Loads a game from the database
        :param game_id:
        :return:
        """
        game = self.database.execute("SELECT * FROM chess_game_saves WHERE game_id = ?", (game_id,)).fetchone()
        if game is None:
            raise ValueError("Game not found")
        self.board = chess.Board()
        self.board.turn = game[4]
        self.board.set_epd(game[1])
        self.last_move = game[5]
        self.time_elapsed = game[6]
        self.time_remaining = game[7]
        self.state = "In Progress"

        self.users = [User(self.database, new_user=False, hash_id=game[2]),
                      User(self.database, new_user=False, hash_id=game[3])]

    def is_empty(self):
        """
        Checks if any users have timed out and removes them from the room
        :return:
        """
        for user in self.users:
            if not user.online:
                self.user_leave(user)

        for spectator in self.spectators:
            if not spectator.online:
                self.user_leave(spectator)
