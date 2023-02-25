import logging
import random

import aiohttp
import asyncio

from aiohttp import web
import sqlite3
import threading

from roommanager import RoomManager
from user import User

logging.basicConfig(level=logging.INFO)


class CustomLock:

    def __init__(self):
        self.lock = threading.Lock()
        self.lock_count = 0
        self.queued_lock_count = 0

    def acquire(self, blocking=True, timeout=-1):
        self.lock_count += 1
        logging.debug(f"Acquiring lock #{self.lock_count} (Queued: {self.queued_lock_count})")
        self.queued_lock_count += 1
        acquired = self.lock.acquire(blocking, timeout)
        if acquired:
            logging.debug(f"Acquired lock #{self.lock_count}")
            return True
        else:
            logging.debug(f"Failed to acquire lock #{self.lock_count}")
            self.queued_lock_count -= 1
            return False

    def release(self):
        logging.debug(f"Releasing lock #{self.lock_count} (Queued: {self.queued_lock_count})")
        self.queued_lock_count -= 1
        self.lock.release()


class ConcurrentDatabase(sqlite3.Connection):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = CustomLock()

    def run(self, sql, *args, **kwargs):
        self.lock.acquire()
        cursor = super().cursor()
        cursor.execute(sql, *args)
        if kwargs.get("commit", True):
            try:
                super().commit()
            except sqlite3.OperationalError as e:
                logging.info(f"Database Error: Commit failed {e}")
        self.lock.release()
        return cursor

    def get(self, sql, *args):
        cursor = self.run(sql, *args)
        result = cursor.fetchall()
        cursor.close()
        return result


class main:

    def __init__(self):
        self.app = web.Application()
        self.database = ConcurrentDatabase("database.db")
        self.init_database()
        self.room_manager = RoomManager(self.database)
        self.app.add_routes([
            web.get('/create_user/{username}', self.create_user),
            web.get('/get_user/{user_id}', self.get_username),
            web.get('/login/{user_hash}', self.login),
            web.get('/get_rooms', self.room_manager.get_rooms),
            web.get('/get_games', self.room_manager.get_available_games),
            web.get('/room/get_state', self.room_manager.get_board_state),
            web.get('/room/has_changed', self.room_manager.has_room_changed),

            web.post('/create_room', self.room_manager.create_room),
            web.post('/join_room', self.room_manager.join_room),
            web.post('/leave_room', self.room_manager.leave_room),
            web.post('/room/make_move', self.room_manager.post_move),
        ])
        self.runner = web.AppRunner(self.app)
        self.webserver_address = "pi.wopr.loafclan.org"
        self.webserver_port = 47675

        self.runner = web.AppRunner(self.app)

    def run(self):
        logging.info("Starting webserver")
        web.run_app(self.app, host=self.webserver_address, port=self.webserver_port,
                    access_log=None)
        logging.error("Webserver stopped")

    def init_database(self):
        self.database.run("CREATE TABLE IF NOT EXISTS users (id INTEGER constraint table_name_pk primary key autoincrement, username TEXT, "
                          "hash_id TEXT)")

    """
    Give the user a cookie to store on their computer to identify them as a user
    """

    def create_user(self, request):
        username = request.match_info.get('username')
        user = self.room_manager.users.create_user(username)
        response = web.json_response({"user_id": user.hash_id}, status=200)
        response.set_cookie("user_id", str(user.hash_id))
        logging.info(f"Created user {user.username} with id {user.hash_id}")
        return response

    def get_username(self, request):
        user_id = request.match_info.get('user_id')
        user = self.room_manager.users.get_user_by_id(user_id)
        if user is None:
            print("User not found")
            return web.json_response({"error": "User not found"}, status=404)
        return web.json_response({"username": user.username}, status=200)

    def login(self, request):
        user_hash = request.match_info.get('user_hash')
        user = self.room_manager.users.get_user(user_hash)
        logging.info(f"Logging in user {user.username} with id {user.hash_id}")
        if user is None:
            return web.json_response({"error": "User not found"}, status=404)
        response = web.json_response({"username": user.username}, status=200)
        response.set_cookie("user_id", str(user.hash_id))
        return response


if __name__ == '__main__':
    manager = main()
    manager.run()
