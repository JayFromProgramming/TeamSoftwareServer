import datetime
from functools import wraps

from aiohttp import web
from aiohttp.abc import Request

from loguru import logger as logging


class BucketTypes:
    Global = "global"
    User = "user"
    Endpoint = "endpoint"


class Bucket:
    """
    A bucket is an object that stores the number of requests made in a certain time period by a certain source
    """

    def __init__(self, limit, per):
        self.limit = limit  # type: int
        self.per = per  # type: datetime.timedelta
        self.actors = {}

    def actor_acted(self, actor) -> bool:
        """
        Records an action by an actor
        :param actor: The actor
        :return: Returns True if the actor has exceeded the limit, False otherwise
        """
        if actor not in self.actors:
            self.actors.update({actor: {"count": 0, "time": datetime.datetime.now(), "blocked": False}})
            return False
        else:
            self.actors[actor]["count"] += 1
            self.actors[actor]["time"] = datetime.datetime.now()

            if self.actors[actor]["blocked"]:
                return True

            if (datetime.datetime.now() - self.actors[actor]["time"]) > self.per:
                self.actors[actor]["count"] = 0
                return False

            # If the actor has exceeded the limit by more than 3x the limit, permanently block them
            if self.actors[actor]["count"] > self.limit * 3:
                self.actors[actor]["blocked"] = True
                return True

            if self.actors[actor]["count"] > self.limit:
                return True

            return False


class RateLimit:
    """
    Creates a decorator that limits the rate of a function based on certain bucket types
    """

    class RateLimitExceeded(Exception):
        pass

    def __init__(self, limit=5, per=datetime.timedelta(seconds=30), bucket_type=BucketTypes.Global):
        self.bucket = Bucket(limit, per)
        self.bucket_type = bucket_type

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get information about the request
            request = args[1]  # type: Request
            # if not isinstance(request, Request):
            #     raise AttributeError("The first argument to a rate limited function must be a Request object")
            match self.bucket_type:
                case BucketTypes.Global:
                    if self.bucket.actor_acted("global"):
                        logging.warning(f"Rate limit exceeded for {request.remote}")
                        return web.json_response({"error": "Rate limit exceeded"}, status=429)
                # case BucketTypes.User:
                #     user = self.users.get_user(request.cookies.get("user_id"))
                #     if user is None:
                #         raise Exception("User not found")
                #     if self.bucket.actor_acted(user.user_id):
                #         raise self.RateLimitExceeded
                case BucketTypes.Endpoint:
                    if self.bucket.actor_acted(request.remote):
                        logging.warning(f"Rate limit exceeded for {request.remote}")
                        return web.json_response({"error": "Rate limit exceeded"}, status=429)
            return func(*args, **kwargs)

        return wrapper
