from user import User
import hashlib


class BaseRoom:

    def __init__(self, host: User, name: str, password: str = None):
        self.host = host
        self.password = password
        self.users = []  # type: list[User]
        self.ai = []  # type: list[AI]
        self.name = name
        self.state = "Idle"
        self.room_id = hashlib.sha256(str(self.name).encode('utf-8')).hexdigest()

    def get_game_info(self):
        info = {
            "name": "Example Game",
            "score": "",
            "state": "Idle",
            "users": [],
            "password_protected": None,
            "joinable": None,
            "time_elapsed": "",
            "time_remaining": "",
        }
        return info

    def user_join(self, user):
        raise NotImplementedError

    def user_leave(self, user):
        raise NotImplementedError

    def ai_add(self):
        raise NotImplementedError

    def ai_remove(self):
        raise NotImplementedError

    def ai_move(self):
        raise NotImplementedError

    def get_users(self):
        raise NotImplementedError

    def get_board_state(self, user):
        raise NotImplementedError

    def post_move(self, user, move):
        raise NotImplementedError
