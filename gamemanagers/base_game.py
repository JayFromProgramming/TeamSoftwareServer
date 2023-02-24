

class BaseGame:

    def __init__(self):
        self.host = None  # type: User
        self.users = []  # type: list[User]
        self.ai = []  # type: list[AI]
        raise NotImplementedError("BaseGame is an abstract class and cannot be instantiated.")

    def get_game_info(self):
        example = {
            "name": "Example Game",
            "time_elapsed": "",
            "time_remaining": "",
            "score": "",
            "state": "Idle"
        }
        raise NotImplementedError

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

    def get_game_state(self, user):
        raise NotImplementedError

    def post_move(self, user, move):
        raise NotImplementedError

