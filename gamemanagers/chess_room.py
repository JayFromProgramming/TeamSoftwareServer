import chess

from gamemanagers.base_room import BaseRoom
import logging

logging = logging.getLogger(__name__)


class Chess(BaseRoom):

    def __init__(self, host, name, password=None):
        super().__init__(host, name, password)
        self.state = "Idle"
        self.board = chess.Board()
        self.max_users = 2
        self.time_elapsed = 0
        self.time_remaining = 0
        self.score = 0
        self.last_move = None
        self.current_player = self.users[0]

    def user_join(self, user):
        if len(self.users) >= self.max_users:
            raise ValueError("Room is full")
        user.join_room(self)
        self.users.append(user)

    def user_leave(self, user):
        user.leave_room()
        self.users.remove(user)

    def get_board_state(self, user):
        return {
            "your_color": "white" if user == self.users[0] else "black",
            "current_player": self.current_player,
            "board": self.board.fen(),
            "last_move": self.last_move
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
        else:
            return False

    def post_move(self, user, move):
        if user != self.current_player:
            logging.info(f"User {user.username} tried to move out of turn")
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
        if self.check_win_conditions():
            return {"result": self.state}
        if len(self.users) == 2:
            self.current_player = self.users[1] if self.current_player == self.users[0] else self.users[0]
        else:
            self.current_player = self.users[0]

        for user in self.users:
            user.room_updated = True
