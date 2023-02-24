from gamemanagers.base_room import BaseRoom


class TestRoom(BaseRoom):

    def __init__(self, host, name, password=None):
        super().__init__(host, name, password)

    def user_join(self, user):
        self.users.append(user)

    def user_leave(self, user):
        self.users.remove(user)

    def ai_add(self):
        pass

    def ai_remove(self):
        pass

    def ai_move(self):
        pass

    def get_users(self):
        return self.users

    def get_game_state(self, user):
        return {
            "name": self.name,
            "time_elapsed": self.time_elapsed,
            "time_remaining": self.time_remaining,
            "score": self.score,
            "state": self.state
        }

    def post_move(self, user, move):
        pass