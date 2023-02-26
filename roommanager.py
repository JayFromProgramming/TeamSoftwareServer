import time

from aiohttp import web

from gamemanagers.chess_room import Chess
from user import User, Users

import logging

logging = logging.getLogger(__name__)


class RoomManager:

    def __init__(self, database):
        self.database = database
        self.rooms = {}
        self.valid_room_types = {
            Chess.__name__: Chess
        }
        self.users = Users(self.database)

    async def create_room(self, request):
        """
        Creates a new room
        :param request: A web request
        :return:
        """
        logging.info(f"Room creation request: {request}")
        data = await request.json()
        room_type = data["room_type"] if "room_type" in data else None
        room_name = data["room_name"] if "room_name" in data else None
        room_password = data["room_password"] if "room_password" in data else None
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
            room = self.valid_room_types[room_type](self.database, user, room_name, room_password)
            self.rooms[room.room_id] = room
            logging.info(f"Created room: {room.room_id}")
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
        logging.info(f"Room list request: {request}")
        rooms = []
        try:
            for room in self.rooms.values():
                rooms.append(room.get_game_info())
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
        pass

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
        Returns the state of a room
        :param request:
        :return:
        """

    def has_room_changed(self, request):
        """
        Returns whether the room has changed since the last time the user checked
        :param request:
        :return:
        """
        logging.debug(f"Room change request: {request}")
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
            return web.json_response({"room_changed": True, "frequent_update": frequent_update})
        return web.json_response({"room_changed": False, "frequent_update": frequent_update})

    def get_board_state(self, request):
        """
        Returns the state of a board from the user's perspective
        :param request:
        :return:
        """
        logging.info(f"Board state request: {request}")
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
            return web.json_response({"error": "Invalid request"}, status=400)
        room = user.current_room
        if room is None:
            return web.json_response({"error": "User not in a room"}, status=402)
        try:
            # print(user.username, move)
            result = room.post_move(user, move)
            if 'error' in result:
                return web.json_response(result, status=400)
            else:
                return web.json_response(result, status=200)
        except Exception as e:
            logging.exception(f"Failed to post move: {e}")
            return web.json_response({"error": "Failed to post move"}, status=500)

    def cleanup_rooms(self):
        """
        Cleans up rooms that have no users
        :return:
        """
        while True:
            logging.info("Cleaning up rooms")
            to_delete = []
            for room in self.rooms.values():
                if room.is_empty():
                    logging.info(f"Deleting room {room.room_id}")
                    to_delete.append(room.room_id)
            for room_id in to_delete:
                self.rooms.pop(room_id)
            logging.info("Finished cleaning up rooms")
            time.sleep(30)
