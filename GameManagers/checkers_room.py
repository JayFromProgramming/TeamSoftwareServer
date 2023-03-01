from GameManagers.base_room import BaseRoom
import logging


class Checkers(BaseRoom):

    def __init__(self, database, host=None, name=None, config=None):
        super().__init__(database, name, host, config)
        if config is None:
            config = {}

        self.state = "Idle"
        self.board = []
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
        return self.board

    def get_board_state(self, user):
        return {
            "your_color": 0 if user == self.users[0] else 1 if user in self.users else None,
            "current_player": 0 if self.current_player == self.users[0] else 1,
            "board": self.board if user == self.users[0] else self.flip_board(),
            "pieces": self.pieces,
            "last_move": str(self.last_move),
            "game_over": self.game_over,
        }

    def check_move(self, user, move):
        pass

    def check_win_conditions(self, user):
        pass

    def post_move(self, user, move):
        for player in self.users + self.spectators:
            player.room_updated = True

        if user.user_id != self.current_player.user_id:
            logging.info(
                f"User {user.username} tried to move out of turn, current player is {self.current_player.username}")
            return {"error": "out_of_turn"}

        try:
            self.check_move(user, move)

        except Exception as e:
            pass

        self.current_player = self.users[0] if self.current_player != self.users[0] else self.users[1]

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