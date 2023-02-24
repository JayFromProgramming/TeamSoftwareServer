import logging
import random

import aiohttp
import asyncio

from aiohttp import web
import sqlite3
import threading
import hashlib

logging.getLogger(__name__)


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
        self.app.add_routes([
            web.get('/get_cookie', self.get_cookie),
            web.get('/get_rooms', self.get_rooms),
        ])
        self.rooms = {}
        self.runner = web.AppRunner(self.app)
        self.webserver_address = "localhost"
        self.webserver_port = 8080
        self.init_database()

        self.runner = web.AppRunner(self.app)

    def run(self):
        logging.info("Starting webserver")
        web.run_app(self.app, host=self.webserver_address, port=self.webserver_port,
                    access_log=None)
        logging.error("Webserver stopped")

    def init_database(self):
        self.database.run("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, cookie TEXT, name TEXT)")

    """
    Give the user a cookie to store on their computer to identify them as a user
    """

    def get_cookie(self, request):
        # Generate a random cookie
        cookie = hashlib.sha256(str(random.random()).encode()).hexdigest()
        # Add the cookie to the database
        self.database.run("INSERT INTO users (cookie, name) VALUES (?, ?)", (cookie, "Anonymous"))
        # Return the cookie to the user
        return web.json_response({"cookie": cookie})

    """
    Get the rooms that currently exist
    """

    def get_rooms(self, request):
        return web.json_response(self.rooms)


if __name__ == '__main__':
    manager = main()
    manager.run()
