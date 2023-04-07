from GameManagers.base_room import BaseRoom
import logging


class Checkers(BaseRoom):

    playable = True

    def __init__(self, database, host=None, name=None, starting_config=None, from_save=False, **kwargs):
        super().__init__(database, name, host, starting_config)
        if starting_config is None:
            starting_config = {}

        self.state = "Idle"
        self.board = []
        self.create_board()
        self.max_users = 2

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

    '''
    0 = No piece
    1 = Red Normal Piece
    2 = Red King Piece
    3 = Black Normal Piece
    4 = Black King Piece
    '''
    def create_board(self):
        self.board = [[0 for _ in range(8)] for _ in range(8)]
        for i in range(3):
            for j in range(1, 8, 2):
                self.board[i][j] = 3

        for i in range(3):
            for j in range(0, 8, 2):
                self.board[7 - i][j] = 1

        for i in range(8):
            self.board[1][i] = 3 if self.board[1][i] == 0 else 0
            self.board[6][i] = 1 if self.board[1][i] == 0 else 0

    def get_board_state(self, user):
        return {
            "your_color": 0 if user == self.users[0] else 1 if user in self.users else None,
            "current_player": 0 if self.current_player == self.users[0] else 1,
            "board": self.board,
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
        if f is not None and (move[0], move[1]) not in f:
            return 1

        if self.board[move[2]][move[3]] != 0:
            return 2

        if abs(move[0] - move[2]) == 1:
            self.make_move(move, None)
            self.toggle_current_player()
            return 0

        mid = ((move[2] + move[0]) / 2, (move[3] + move[1]) / 2)
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

    '''
    Checking if a piece can move legally
    (please dont try to understand this code, i really hope it works because debugging this will be a bitch)
    '''
    def can_move(self, i, j):
        chu = self.board[i][j]
        good = 0
        if chu in [1, 2]:
            tempi = i - 1
            if i > -1:
                if j + 1 < 8 and self.board[tempi][j + 1] == 0:
                    good = 1 if good == 0 else good
                elif j - 1 >= 0 and self.board[tempi][j - 1] == 0:
                    good = 1 if good == 0 else good

                if j + 2 < 8 and tempi - 1 > -1 and self.board[tempi][j + 1] in [3, 4] and self.board[tempi - 1][j + 2] == 0:
                    good = 2

                if j - 2 >= 0 and tempi - 1 > -1 and self.board[tempi][j - 1] in [3, 4] and self.board[tempi - 1][j - 2] == 0:
                    good = 2
            tempi += 2
            if chu == 2 and tempi < 8:
                if j + 1 < 8 and self.board[tempi][j + 1] == 0:
                    good = 1 if good == 0 else good
                if j - 1 >= 0 and self.board[tempi][j - 1] == 0:
                    good = 1 if good == 0 else good

                if j + 2 < 8 and tempi + 1 < 8 and self.board[tempi][j + 1] in [3, 4] and self.board[tempi + 1][j + 2] == 0:
                    good = 2

                if j - 2 >= 0 and tempi + 1 < 8 and self.board[tempi][j - 1] in [3, 4] and self.board[tempi + 1][j - 2] == 0:
                    good = 2
        else:
            tempi = i + 1
            if tempi < 8:
                if j + 1 < 8 and self.board[tempi][j + 1] == 0:
                    good = 1 if good == 0 else good
                elif j - 1 >= 0 and self.board[tempi][j - 1] == 0:
                    good = 1 if good == 0 else good

                if j + 2 < 8 and tempi + 1 < 8 and self.board[tempi][j + 1] in [1, 2] and self.board[tempi + 1][j + 2] == 0:
                    good = 2

                if j - 2 >= 0 and tempi + 1 < 8 and self.board[tempi][j - 1] in [1, 2] and self.board[tempi + 1][j - 2] == 0:
                    good = 2
            tempi -= 2
            if chu == 4 and i > -1:
                if j + 1 < 8 and self.board[tempi][j + 1] == 0:
                    good = 1 if good == 0 else good
                if j - 1 >= 0 and self.board[tempi][j - 1] == 0:
                    good = 1 if good == 0 else good

                if j + 2 < 8 and tempi - 1 > -1 and self.board[tempi][j + 1] in [1, 2] and self.board[tempi - 1][j + 2] == 0:
                    good = 2

                if j - 2 >= 0 and tempi - 1 > -1 and self.board[tempi][j - 1] in [1, 2] and self.board[tempi - 1][j - 2] == 0:
                    good = 2
        return good

    '''
    Checking to see if a user won the game
    '''
    def check_win_conditions(self, user):
        chu = 1 if self.users[1] == user else 3

        for i in range(8):
            for j in range(8):
                if self.board[i][j] in [chu, chu + 1]:
                    if self.can_move(i, j) > 0:
                        return False

        return True
    '''
    Making a list of forced moves for a user, if any
    '''
    def forced_moves(self, user):
        moves = []
        nums = [1, 2] if self.users[0] == user else [3, 4]

        for i in range(8):
            for j in range(8):
                if self.board[i][j] in nums:
                    if self.can_move(i, j) == 2 and (i, j) not in moves:
                        moves.append((i, j))

        return None

    '''
    Physically making the move on the server board
    '''
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


'''
Only meant for testing the board
'''
if __name__ == '__main__':
    c = Checkers(None)
    c.create_board()
    l = c.flip_board()
    for i in l:
        print(i)
