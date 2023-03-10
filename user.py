import datetime
import hashlib
import random
import logging

logging = logging.getLogger(__name__)


class User:

    def __init__(self, database, new_user=False, username=None, hash_id=None):
        """
        Creates a new user object
        :param database: The database object
        :param new_user: Whether or not this is a new user
        :param username: The username of the user (Only used if new_user is True)
        :param hash_id: The hash_id of the user (Only used if new_user is False)
        """
        self.database = database
        self.username = None
        self.user_id = None
        self.hash_id = hash_id
        self.last_ping = datetime.datetime.fromtimestamp(0)

        self.current_room = None
        self.room_updated = False

        self.game_data_slot = None  # A variable that game rooms can use to store data for the user

        if new_user:
            self.username = username
            self._create_user()
        else:
            self._load_user()

    def _create_user(self):
        """
        Creates a new user in the database
        :return:
        """
        logging.info("Creating new user")
        self.hash_id = hashlib.sha256(random.getrandbits(256).to_bytes(32, "big")).hexdigest()
        self.database.run("INSERT INTO users VALUES (NULL, ?, ?)", (self.username, self.hash_id))
        self.user_id = self.database.get("SELECT last_insert_rowid()")[0][0]

    def _load_user(self):
        """
        Loads a user from the database
        :return:
        """
        user = self.database.get("SELECT * FROM users WHERE hash_id=?", (self.hash_id,))
        if len(user) == 0:
            raise Exception("User not found")
        user = user[0]
        self.username = user[1]
        self.user_id = user[0]

    def ping(self):
        """
        Updates the last ping time
        :return:
        """
        self.last_ping = datetime.datetime.now()

    def logout(self):
        """
        Logs out the user
        :return:
        """
        self.leave_room()
        self.last_ping = datetime.datetime.fromtimestamp(0)

    @property
    def online(self):
        """
        Returns whether or not the user is online
        :return:
        """
        return (datetime.datetime.now() - self.last_ping).total_seconds() < 30

    def join_room(self, room):
        """
        Joins a room
        :param room: The room object
        :return:
        """
        self.current_room = room
        self.room_updated = True

    def leave_room(self):
        """
        Leaves the current room
        :return:
        """
        self.current_room = None

    def __str__(self):
        return self.user_id

    def __repr__(self):
        return "User: " + self.username

    def encode(self):
        """
        Encodes the user object
        :return:
        """
        return {
            "username": self.username,
            "user_id": self.user_id,
            "online": self.online,
        }


class Users:

    def __init__(self, database):
        self.database = database
        self.users = {}
        self.load_users()

    def load_users(self):
        """
        Loads all users from the database
        :return:
        """
        logging.info("Loading users")
        for user in self.database.get("SELECT * FROM users"):
            self.users[user[2]] = User(self.database, hash_id=user[2])
        logging.info("Loaded {} users".format(len(self.users)))

    def get_user(self, hash_id):
        """
        Returns a user object
        :param hash_id: The hash_id of the user
        :return:
        """
        if hash_id in self.users:
            return self.users[hash_id]
        else:
            try:
                self.users[hash_id] = User(self.database, hash_id=hash_id)
            except Exception:
                return None
            return self.users[hash_id]

    def create_user(self, username):
        """
        Creates a new user
        :param username: The username of the new user
        :return:
        """
        user = User(self.database, new_user=True, username=username)
        self.users[user.hash_id] = user
        return user

    def get_all_users(self):
        """
        Returns a list of all users
        :return:
        """
        return self.users.values()

    def get_user_by_name(self, username):
        """
        Returns a user by their username
        :param username: The username of the user
        :return:
        """
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def get_user_by_id(self, user_id):
        """
        Returns a user by their user_id
        :param user_id: The user_id of the user
        :return:
        """
        for user in self.users.values():
            if user.user_id == user_id:
                return user
        return None

