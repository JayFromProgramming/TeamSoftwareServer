import datetime
import time

from aiohttp import web
import os

import Ratelimiter
from GameManagers.base_room import BaseRoom
from user import User, Users

from loguru import logger as logging

# Import all files in the gamemanagers folder
logging.info("Loading all room packages")
for directory in os.listdir("GameManagers"):
    if os.path.isdir(f"GameManagers/{directory}") and directory != "__pycache__":
        # Check if the package has an __init__.py file
        if os.path.isfile(f"GameManagers/{directory}/__init__.py"):
            logging.info(f"Loading package {directory}")
            try:
                exec(f"from GameManagers.{directory} import *")
            except Exception as e:
                logging.error(f"Failed to load package {directory}: {e}")
logging.info(f"Loaded {len(BaseRoom.__subclasses__())} room modules")


class RoomManager:

    def __init__(self, database):
        self.database = database
        self.database_init()
        self.rooms = {}

        self.valid_room_types = {}
        for room_type in BaseRoom.__subclasses__():
            if room_type.playable:
                logging.info(f"Found room type: {room_type.__name__}")
                self.valid_room_types[room_type.__name__] = room_type
            else:
                logging.info(f"Found non-playable room type: {room_type.__name__}")
        self.users = Users(self.database)

    def database_init(self):
        self.database.run("CREATE TABLE IF NOT EXISTS room_saves ("
                          "room_id TEXT PRIMARY KEY, room_type TEXT,"
                          " room_name TEXT, room_password TEXT)")

    async def create_room(self, request):
        """
        Creates a new room
        :param request: A web request
        :return:
        """
        logging.info(f"Room creation request from {request.remote}")
        data = await request.json()
        room_type = data["room_type"] if "room_type" in data else None
        room_name = data["room_name"] if "room_name" in data else None
        room_config = data["room_config"] if "room_config" in data else None
        cookie = request.cookies["hash_id"] if "hash_id" in request.cookies else None
        if cookie is None:
            logging.info(f"Missing cookie")
            return web.json_response({"error": "Missing Authentication"}, status=401)
        if room_type is None or room_name is None:
            logging.info(f"Missing room type or name: {room_type}, {room_name}")
            return web.json_response({"error": "Invalid request"}, status=400)
        if room_type not in self.valid_room_types:
            logging.info(f"Invalid room type: {room_type}")
            return web.json_response({"error": "Invalid room type"}, status=400)
        user = self.users.get_user(cookie)
        if user is None:
            logging.info(f"Invalid user: {cookie}")
            return web.json_response({"error": "Invalid user"}, status=400)
        try:
            room = self.valid_room_types[room_type](self.database, name=room_name, host=user, starting_config=room_config)
            self.rooms[room.room_id] = room
            logging.info(f"Created room: {room.room_id} with starting config: {room_config}")
            return web.json_response({"room_id": room.room_id})
        except Exception as e:
            logging.exception(f"Failed to create room: {e}")
            return web.json_response({"error": "Failed to create room"}, status=500)

    def get_rooms(self, request):
        """
        Returns a list of rooms over the request
        :param request: A web request
        :return:
        """
        logging.info(f"Room list request from {request.remote}")
        rooms = {"rooms": []}
        try:
            for room in self.rooms.values():
                rooms["rooms"].append(room.get_game_info())
        except Exception as e:
            logging.exception(f"Failed to get rooms: {e}")
            return web.json_response({"error": "Failed to get rooms"}, status=500)
        return web.json_response(rooms, status=200)

    async def join_room(self, request):
        logging.info(f"Room join request: {request}")
        data = await request.json()
        room_id = data["room_id"] if "room_id" in data else None
        room_password = data["room_password"] if "room_password" in data else None
        user_hash = request.cookies["hash_id"] if "hash_id" in request.cookies else None
        if user_hash is None:
            logging.info(f"Missing cookie")
            return web.json_response({"error": "Missing Authentication"}, status=401)
        if room_id is None:
            logging.info(f"Missing room id")
            return web.json_response({"error": "Invalid request"}, status=400)
        if room_id not in self.rooms:
            logging.info(f"Invalid room id: {room_id}")
            return web.json_response({"error": "Invalid room id"}, status=404)
        user = self.users.get_user(user_hash)
        if user is None:
            logging.info(f"Invalid user: {user_hash}")
            return web.json_response({"error": "Invalid user"}, status=400)
        if user.current_room is not None:
            # Check if the user is already in the room
            if user.current_room.room_id == room_id:
                return web.json_response({"room_id": room_id})
            # If the user is in a different room, leave it
            user.current_room.user_leave(user)
        try:
            room = self.rooms[room_id]
            if room.password is not None and room.password != room_password:
                logging.info(f"Invalid password: {room_password}")
                return web.json_response({"error": "Invalid password"}, status=401)
            room.user_join(user)
            logging.info(f"User {user.user_id} joined room {room.room_id}")
            return web.json_response({"room_id": room.room_id})
        except Exception as e:
            logging.exception(f"Failed to join room: {e}")
            return web.json_response({"error": "Failed to join room"}, status=500)

    def leave_room(self, request):
        """
        Called when a user wants to leave a room
        :param request:
        :return:
        """
        logging.info(f"Room leave request: {request}")
        if "user_hash" not in request.cookies:
            return web.json_response({"error": "Missing Authentication"}, status=401)
        user = self.users.get_user(request.cookies["user_hash"])
        if user is None:
            return web.json_response({"error": "Invalid user"}, status=401)
        if user.current_room is None:
            return web.json_response({"error": "User not in a room"}, status=400)
        try:
            user.current_room.user_leave(user)
            logging.info(f"User {user.user_id} left room {user.current_room.room_id}")
            return web.json_response({"success": True})
        except Exception as e:
            logging.exception(f"Failed to leave room: {e}")
            return web.json_response({"error": "Failed to leave room"}, status=500)

    def get_available_games(self, request):
        """
        Returns a list of available games
        :param request:
        :return:
        """
        games = []
        for game in self.valid_room_types.keys():
            games.append(game)
        return web.json_response(games, status=200)

    def get_room_state(self, request):
        """
        Returns the state of a room test
        :param request: A web request
        :return:
        """
        pass

    @Ratelimiter.RateLimit(limit=5, per=datetime.timedelta(minutes=1), bucket_type=Ratelimiter.BucketTypes.Endpoint)
    def has_board_changed(self, request):
        """
        Returns whether the room has changed since the last time the user checked
        :param request:
        :return:
        """
        # logging.debug(f"Room change request: {request}")
        if "user_hash" not in request.cookies:
            return web.json_response({"error": "Missing Authentication"}, status=401)
        user = self.users.get_user(request.cookies["user_hash"])
        if user is None:
            return web.json_response({"error": "Invalid user"}, status=400)
        room = user.current_room
        if room is None:
            return web.json_response({"error": "User not in a room"}, status=400)
        user.ping()
        frequent_update = room.frequent_update()
        if user.room_updated:
            user.room_updated = False
            return web.json_response({"changed": True, "frequent_update": frequent_update})
        return web.json_response({"changed": False, "frequent_update": frequent_update})

    def get_board_state(self, request):
        """
        Returns the state of a board from the user's perspective
        :param request:
        :return:
        """
        logging.info(f"Board state request from endpoint: {request.remote}")
        if "user_hash" not in request.cookies:
            return web.json_response({"error": "Missing Authentication"}, status=401)
        user = self.users.get_user(request.cookies["user_hash"])
        if user is None:
            logging.info(f"Invalid user: {request.cookies['user_hash']}")
            return web.json_response({"error": "Invalid user"}, status=400)
        room = user.current_room
        if room is None:
            logging.info(f"User not in a room")
            return web.json_response({"error": "User not in a room"}, status=402)
        room_state = room.get_board_state(user)
        return web.json_response(room_state, status=200)

    async def post_move(self, request):
        if "user_hash" not in request.cookies:
            return web.json_response({"error": "Missing Authentication"}, status=401)
        user = self.users.get_user(request.cookies["user_hash"])
        logging.info(f"Move request from {user.username}({user.user_id}): {request}")
        if user is None:
            return web.json_response({"error": "Invalid user"}, status=403)

        data = await request.json()
        move = data["move"] if "move" in data else None
        if move is None:
            logging.warning(f"Invalid move request: {data}")
            return web.json_response({"error": "Invalid request"}, status=400)
        room = user.current_room
        if room is None:
            logging.warning(f"User {user.user_id} not in a room")
            return web.json_response({"error": "User not in a room"}, status=402)
        try:
            result = room.post_move(user, move)
            if 'error' in result:
                logging.warning(f"Move result returned error: {result}")
                return web.json_response(result, status=501)
            else:
                return web.json_response(result, status=200)
        except Exception as e:
            logging.exception(f"Failed to post move: {e}")
            return web.json_response({"error": "Failed to post move"}, status=500)

    async def save_game(self, request):
        """
        Saves a game to the database so it can be loaded later
        :param request:
        :return:
        """
        if "user_hash" not in request.cookies:
            return web.json_response({"error": "Missing Authentication"}, status=401)
        user = self.users.get_user(request.cookies["user_hash"])
        logging.info(f"Save game request from {user.username}({user.user_id}): {request}")
        if user is None:
            return web.json_response({"error": "Invalid user"}, status=403)

        room = user.current_room
        if room is None:
            return web.json_response({"error": "User not in a room"}, status=402)
        try:
            result = room.save_game()
            if 'error' in result:
                return web.json_response(result, status=400)
            else:
                return web.json_response(result, status=200)
        except Exception as e:
            logging.exception(f"Failed to save game: {e}")
            return web.json_response({"error": "Failed to save game"}, status=500)

    async def load_game(self, request):
        """
        Loads a game from the database
        :param request:
        :return:
        """
        if "user_hash" not in request.cookies:
            return web.json_response({"error": "Missing Authentication"}, status=401)
        user = self.users.get_user(request.cookies["user_hash"])
        logging.info(f"Load game request from {user.username}({user.user_id}): {request}")
        if user is None:
            return web.json_response({"error": "Invalid user"}, status=403)

        data = await request.json()
        room_id = data["room_id"] if "room_id" in data else None
        if room_id is None:
            return web.json_response({"error": "Invalid request"}, status=400)

        result = self.database.get("SELECT * FROM room_saves WHERE room_id = ?", (room_id,))
        if len(result) == 0:
            return web.json_response({"error": "Game not found"}, status=404)
        result = result[0]
        # Create a game object using the data from the database
        game = self.valid_room_types[result[1]](self.database, name=result[2], password=result[3], from_save=result[0],
                                                users=self.users)
        self.rooms[game.room_id] = game
        game.user_join(user)
        return web.json_response({"room_id": game.room_id, "room_type": game.__class__.__name__}, status=200)

    def get_save_game_info(self, request):
        """
        Returns information about the user's saved games
        :param request:
        :return:
        """
        logging.info(f"Get save game info request: {request}")
        if "user_hash" not in request.cookies:
            return web.json_response({"error": "Missing Authentication"}, status=401)
        user = self.users.get_user(request.cookies["user_hash"])
        logging.info(f"Get save game info request from {user.username}({user.user_id}): {request}")
        if user is None:
            return web.json_response({"error": "Invalid user"}, status=403)

        game = request.match_info["game_id"]
        result = self.database.get("SELECT * FROM room_saves WHERE room_id = ?", (game,))
        if len(result) == 0:
            return web.json_response({"error": "Game not found"}, status=406)
        game = result[0]
        # Get the information about the game from its own table
        game_type = game[1]
        game_class = self.valid_room_types[game_type]
        game_info = game_class.get_save_game_info(self.database, self.users, game[0])
        return web.json_response(game_info, status=200)

    def cleanup_rooms(self):
        """
        Cleans up rooms that have no users
        :return:
        """
        while True:
            # logging.debug("Cleaning up rooms")
            to_delete = []
            for room in self.rooms.values():
                if room.is_empty():
                    logging.info(f"Deleting room {room.room_id}")
                    to_delete.append(room.room_id)
            for room_id in to_delete:
                self.rooms.pop(room_id)
            # logging.debug("Finished cleaning up rooms")
            time.sleep(30)
