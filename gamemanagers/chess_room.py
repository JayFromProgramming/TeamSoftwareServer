import chess

from gamemanagers.base_room import BaseRoom


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
        self.current_player = None  # type: User # The user who's turn it is to move

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
        }

    def post_move(self, user, move):
        if user != self.current_player:
            return
        self.board.push_san(move)
        self.last_move = move
        self.current_player = self.users[1] if self.current_player == self.users[0] else self.users[0]
