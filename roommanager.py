from aiohttp import web

from gamemanagers.test_room import TestRoom
from user import User, Users

import logging

logging = logging.getLogger(__name__)

class RoomManager:

    def __init__(self, database):
        self.database = database
        self.rooms = {}
        self.valid_room_types = {
            "testRoom": TestRoom
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
            room = self.valid_room_types[room_type](user, room_name, room_password)
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

    def join_room(self, request):
        pass

    def leave_room(self, request):
        pass

    def get_room_state(self, request):
        """
        Returns the state of a room
        :param request:
        :return:
        """

    def get_board_state(self, request):
        """
        Returns the state of a board from the user's perspective
        :param request:
        :return:
        """
        user = self.users.get_user(request.cookies["hash_id"])
        if user is None:
            return web.json_response({"error": "Invalid user"}, status=400)
        room = user.current_room
        if room is None:
            return web.json_response({"error": "User not in a room"}, status=400)
        room_state = room.get_board_state(user)
        return web.json_response(room_state, status=200)

    async def post_move(self, request):
        pass
