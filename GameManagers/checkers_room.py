from GameManagers.base_room import BaseRoom
import logging


class Checkers(BaseRoom):

    def __init__(self, database, host=None, name=None, config=None):
        super().__init__(database, name, host, config)
        if config == None:
            config = {}

        self.state = "Idle"
        # self.board = chess.Board(chess960=True).from_chess960_pos(random.randint(0, 959))
        self.board = []
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

    def get_board_state(self, user):
        return {
            "your_color": 0 if user == self.users[0] else 1 if user in self.users else None,
            "current_player": 0 if self.current_player == self.users[0] else 1,
            "board": [],
            "last_move": str(self.last_move),
            "game_over": self.game_over,
            # "taken_pieces": self.taken_pieces
        }

    def post_move(self, user, move):
        pass


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