from user import User
import hashlib


class BaseRoom:

    def __init__(self, host: User, name: str, password: str = None):
        self.host = host
        host.join_room(self)
        self.password = password
        self.users = [self.host]  # type: list[User]
        self.ai = []  # type: list[AI]
        self.name = name
        self.state = "Idle"
        self.room_id = hashlib.sha256(str(self.name).encode('utf-8')).hexdigest()

        self.max_users = 0

    def get_game_info(self):
        info = {
            "name": self.name,
            "type": self.__class__.__name__,
            "score": "",
            "state": self.state,
            "users": [user.encode() for user in self.users],
            "max_users": self.max_users,
            "password_protected": self.password is not None,
            "joinable": True,
            "time_elapsed": "",
            "time_remaining": "",
            "room_id": str(self.room_id)
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
