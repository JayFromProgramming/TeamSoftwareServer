from user import User
import hashlib


class BaseRoom:

    playable = False

    def __init__(self, database, name: str, host: User = None, password: str = None, from_save=None, **kwargs):
        self.database = database
        self.host = host
        if self.host is not None:
            self.host.join_room(self)
        self.password = password
        self.users = [self.host]  # type: list[User]
        self.spectators = []  # type: list[User]
        self.name = name
        self.state = "Idle"
        self.room_id = hashlib.sha256(str(self.name).encode('utf-8')).hexdigest()
        self.max_users = 0

    def get_game_info(self):
        """
        Get the information about the game
        :return: Returns a dictionary containing the information about the game, in a standard format
        """
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
        """
        Add a user to the room
        :param user:
        :return:
        """
        raise NotImplementedError

    def user_leave(self, user):
        """
        Remove a user from the room
        :param user:
        :return:
        """
        raise NotImplementedError

    def frequent_update(self):
        """
        Data that is sent to the client every second
        :return: A dictionary containing the data to send to the client
        """
        raise NotImplementedError

    def get_board_state(self, user):
        """
        Get the state of the board for a particular user
        :param user: The user to get the board state for
        :return: A dictionary containing the board state, in the format of the particular game
        """
        raise NotImplementedError

    def post_move(self, user, move):
        """
        Post a move to the game
        :param user: A user object representing the user who made the move
        :param move: The move that was made, in the format of the particular game
        :return:
        """
        raise NotImplementedError

    def save_game(self):
        """
        Save the game to the database
        :return: The hash of the room id
        """
        raise NotImplementedError

    @classmethod
    def get_save_game_info(cls, database, users, game_id):
        """
        Get the information about a saved game so it can be displayed in the load game menu
        :param database: The sqlite3 database object
        :param game_id: The hash of room id
        :param users: The users object to allow the function to get the username of the players
        :return: A dictionary containing the information about the game
        """
        raise NotImplementedError

    def load_game(self, game_id, users):
        """
        Load a game from the database
        :param game_id: The hash of the room id
        :return:
        """
        raise NotImplementedError

    def is_empty(self):
        raise NotImplementedError
