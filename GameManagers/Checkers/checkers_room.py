from GameManagers.base_room import BaseRoom
import logging


class Checkers(BaseRoom):

    def __init__(self, database, host=None, name=None, config=None):
        super().__init__(database, name, host, config)
        if config is None:
            config = {}

        self.state = "Idle"
        self.board = []
        self.create_board()
        self.max_users = 2
        self.pieces = {}

        self.last_move = None
        self.current_player = self.users[0]

        self.game_over = False

    def user_leave(self, user):
        user.join_room(self)
        if user in self.users + self.spectators:
            return
        if len(self.users) >= self.max_users:
            self.spectators.append(user)
        else:
            self.users.append(user)

    def frequent_update(self):
        return {
            "players": [user.encode() for user in self.users],
            "spectators": [user.encode() for user in self.spectators],
        }

    """
    Flips the board in the event that player 2 wants to see the board from their prospective
    """
    def flip_board(self):
        f = [[0 for i in range(8)] for i in range(8)]

        for i in range(8):
            for j in range(8):
                f[i][j] = self.board[7 - i][7 - j]

        return f

    def toggle_current_player(self):
        self.current_player = self.users[0] if self.current_player == self.users[1] else self.users[1]

    # 0 None 1 red 2 redk 3 black 4 blackk
    def create_board(self):
        self.board = [[0 for i in range(8)] for i in range(8)]
        for i in range(3):
            for j in range(0, 8, 2):
                self.board[i][j] = 3

        for i in range(3):
            for j in range(1, 8, 2):
                self.board[7 - i][j] = 1

    def get_board_state(self, user):
        return {
            "your_color": 0 if user == self.users[0] else 1 if user in self.users else None,
            "current_player": 0 if self.current_player == self.users[0] else 1,
            "board": self.board if user == self.users[0] else self.flip_board(),
            "pieces": self.pieces,
            "last_move": str(self.last_move),
            "game_over": self.game_over,
        }

    '''
    Returns 0 if move was successful
    Returns 1 if there was a forced move
    Returns 2 if there was a piece blocking the move spot
    returns 3 if there was an invalid jump
    '''
    def check_move(self, user, move):
        move = list(map(int, move.split(' ')))
        f = self.forced_moves(user)
        if move not in f and f is not None:
            return 1

        if self.board[move[2]][move[3]] != 0:
            return 2

        if abs(move[0] - move[2]) == 1:
            self.make_move(move, None)
            self.toggle_current_player()
            return 0

        mid = (abs(move[0] - move[2]), abs(move[1] - move[3]))
        midp = self.board[mid[0]][mid[1]]

        if midp == 0:
            return 3
        if midp < 3 and self.current_player == self.users[0]:
            return 3
        if midp > 2 and self.current_player == self.users[1]:
            return 3

        self.make_move(move, mid)
        if self.forced_moves(user) is None:
            self.toggle_current_player()

        return 0


    def check_win_conditions(self, user):
        pass

    def forced_moves(self, user):
        return []

    def make_move(self, move, mid=None):
        self.board[move[2]][move[3]] = self.board[move[0]][move[1]]
        self.board[move[0]][move[1]] = 0

        if mid is not None:
            self.board[mid[0]][mid[1]] = 0

    def post_move(self, user, move):
        for player in self.users + self.spectators:
            player.room_updated = True

        if user.user_id != self.current_player.user_id:
            logging.info(
                f"User {user.username} tried to move out of turn, current player is {self.current_player.username}")
            return {"error": "out_of_turn"}

        res = self.check_move(user, move)
        if res == 1:
            return {"error": "forced_move"}
        if res == 2:
            return {"error": "blocked_destination"}

        #self.current_player = self.users[0] if self.current_player != self.users[0] else self.users[1]

        self.game_over = True if self.check_win_conditions(user) else self.game_over

        return {"result": "success"}

    def is_empty(self):
        all_offline = True
        for user in self.users:
            if user.online:
                all_offline = False

        for spectator in self.spectators:
            if not spectator.online:
                self.user_leave(spectator)

        return all_offline

    def user_join(self, user):
        # Check if the user is already in the room
        user.join_room(self)
        if user in self.users + self.spectators:
            return
        if len(self.users) >= self.max_users:
            self.spectators.append(user)
        else:
            self.users.append(user)


if __name__ == '__main__':
    c = Checkers(None)
    c.create_board()
    print(c.board)