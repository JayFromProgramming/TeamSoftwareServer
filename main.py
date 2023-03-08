import json
import socket
import struct
import traceback

from loguru import logger as logging
import random
import netifaces
import aiohttp
import asyncio

import requests
from aiohttp import web
import sqlite3
import threading
import hashlib

from roommanager import RoomManager
from user import User

# Set the logging level to INFO

logging.add("logs/{time}.log", rotation="1 week", retention="1 hour", compression="zip", level=10)


def get_host_names():
    """
    Gets all the ip addresses that can be bound to
    """
    interfaces = []
    for interface in netifaces.interfaces():
        try:
            if netifaces.AF_INET in netifaces.ifaddresses(interface):
                for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                    if link["addr"] != "":
                        interfaces.append(link["addr"])
        except Exception as e:
            logging.debug(f"Error getting interface {interface}: {e}")
            pass
    return interfaces


def multicast_discovery(server_info, server_ip, server_port):
    """
    Multicast discovery to allow clients to easily find this server
    """
    logging.info("Starting multicast discovery")

    # Create the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # Setup UDP socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow multiple sockets to use the same port
    # sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)  # Limit multicast packets to local network
    # sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP,
    #                 1)  # Allow multicast packets to loop back to local host

    MCAST_GRP = socket.inet_aton("224.1.1.1")  # Set the multicast group

    # Bind to the port
    sock.bind(('', 5007))
    # Join the multicast group

    host = socket.gethostbyname(socket.gethostname())
    mreq = MCAST_GRP + socket.inet_aton(host)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    logging.info(f"Multicast discovery bound to MCAST_GRP 224.1.1.1 on port 5007")

    while True:
        try:
            data, address = sock.recvfrom(1024)
            logging.info(f"Received multicast discovery from {address}")
            msg = {
                "server_id": server_info[0],
                "host": server_ip,
                "port": server_port,
                "name": server_info[1],
            }
            sock.sendto(json.dumps(msg).encode(), address)
        except Exception as e:
            logging.debug(f"Error in multicast discovery: {e}")
            pass


class CustomLock:

    def __init__(self):
        self.lock = threading.Lock()
        self.lock_count = 0
        self.queued_lock_count = 0

    def acquire(self, blocking=True, timeout=-1):
        self.lock_count += 1
        # logging.debug(f"Acquiring lock #{self.lock_count} (Queued: {self.queued_lock_count})")
        self.queued_lock_count += 1
        acquired = self.lock.acquire(blocking, timeout)
        if acquired:
            # logging.debug(f"Acquired lock #{self.lock_count}")
            return True
        else:
            # logging.debug(f"Failed to acquire lock #{self.lock_count}")
            self.queued_lock_count -= 1
            return False

    def release(self):
        # logging.debug(f"Releasing lock #{self.lock_count} (Queued: {self.queued_lock_count})")
        self.queued_lock_count -= 1
        self.lock.release()


class ConcurrentDatabase(sqlite3.Connection):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = CustomLock()
        logging.info("Database initialized")

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
            web.get('/get_server_id', self.get_server_id),
            web.get('/create_user/{username}', self.create_user),
            web.get('/get_user/{user_id}', self.get_username),
            web.get('/login/{user_hash}', self.login),
            web.get('/get_rooms', self.room_manager.get_rooms),
            web.get('/get_games', self.room_manager.get_available_games),
            web.get('/room/get_state', self.room_manager.get_board_state),
            web.get('/room/has_changed', self.room_manager.has_room_changed),
            web.get('/room/get_saved_info/{game_id}', self.room_manager.get_save_game_info),

            web.post('/create_room', self.room_manager.create_room),
            web.post('/join_room', self.room_manager.join_room),
            web.post('/leave_room', self.room_manager.leave_room),
            web.post('/room/make_move', self.room_manager.post_move),
            web.post('/room/save_game', self.room_manager.save_game),
            web.post('/room/load_game', self.room_manager.load_game),
        ])
        self.webserver_address = get_host_names()
        self.webserver_port = 47672

        threading.Thread(target=self.room_manager.cleanup_rooms, daemon=True).start()
        threading.Thread(target=multicast_discovery,
                         args=(self.get_server_id_internal(), self.webserver_address, self.webserver_port),
                         daemon=True).start()
        self.runner = web.AppRunner(self.app)

    def run(self):
        logging.info("Starting webserver")
        web.run_app(self.app, host=self.webserver_address, port=self.webserver_port,
                    access_log=None)
        logging.error("Webserver stopped")

    def init_database(self):
        self.database.run(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER constraint table_name_pk primary key autoincrement, username TEXT, "
            "hash_id TEXT)")
        # Check if a server ID table exists and create it if it doesn't
        if not self.database.get("SELECT name FROM sqlite_master WHERE type='table' AND name='server_id'"):
            hash = hashlib.sha256(str(random.getrandbits(256)).encode()).hexdigest()
            server_name = input("Enter a name for this server: ")
            self.database.run("CREATE TABLE IF NOT EXISTS server_id (id TEXT, name TEXT)")
            self.database.run("INSERT INTO server_id VALUES (?, ?)", (hash, server_name))

    def get_server_id_internal(self):
        server_id = self.database.get("SELECT id FROM server_id")[0][0]
        server_name = self.database.get("SELECT name FROM server_id")[0][0]
        return server_id, server_name

    def get_server_id(self, request):
        server_id = self.database.get("SELECT id FROM server_id")[0][0]
        server_name = self.database.get("SELECT name FROM server_id")[0][0]
        return web.json_response({"server_id": server_id, "server_name": server_name}, status=200)

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
        if user is None:
            logging.info(f"User with hash {user_hash} not found")
            return web.json_response({"error": "User not found"}, status=404)
        logging.info(f"Logging in user {user.username} with id {user.hash_id}")
        response = web.json_response({"username": user.username}, status=200)
        response.set_cookie("user_id", str(user.hash_id))
        return response


if __name__ == '__main__':
    manager = main()
    manager.run()
