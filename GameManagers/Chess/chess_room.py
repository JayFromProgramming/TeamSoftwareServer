import datetime
import random
import threading
import time
import traceback

import chess
import chess.variant

from GameManagers.base_room import BaseRoom
from loguru import logger as logging

from .ai import ChessAI


class Chess(BaseRoom):
    playable = True

    def __init__(self, database, host=None, name=None, starting_config=None, from_save=False, **kwargs):
        super().__init__(database, name, host, starting_config)
        self.database_init()

        logging.bind(room=self.name)

        if starting_config is None:
            starting_config = {}

        if from_save:
            self.load_game(from_save, **kwargs)
        else:
            self.state = "Waiting..."
            self.variant = starting_config["chess_variant"] if "chess_variant" in starting_config else "chess_variant"
            match self.variant:
                case "Standard":
                    self.board = chess.Board()
                case "Chess960":
                    self.board = chess.Board(chess960=True)
                    self.board.set_chess960_pos(random.randint(0, 959))
                case "Suicide":
                    self.board = chess.variant.SuicideBoard()
                case "Crazyhouse":
                    self.board = chess.variant.CrazyhouseBoard()
                case "Three Check":
                    self.board = chess.variant.ThreeCheckBoard()
                case "Atomic":
                    self.board = chess.variant.AtomicBoard()
                case "Antichess":
                    self.board = chess.variant.AntichessBoard()
                case "Horde":
                    self.board = chess.variant.HordeBoard()
                case "King of the Hill":
                    self.board = chess.variant.KingOfTheHillBoard()
                case "Racing Kings":
                    self.board = chess.variant.RacingKingsBoard()
                case _:
                    self.board = chess.Board()

            self.max_users = 2

            self.timers_enabled = starting_config["timers_enabled"] if "timers_enabled" in starting_config else False
            self.move_timers = [datetime.timedelta(seconds=starting_config["white_time"] if "white_time" in starting_config else 5),
                                datetime.timedelta(seconds=starting_config["black_time"] if "black_time" in starting_config else 5)]
            self.time_added_per_move = \
                datetime.timedelta(seconds=starting_config["time_added_per_move"] if "time_added_per_move" in starting_config else 10)

            self.score = 0
            self.game_over = False
            self.last_move = None
            # self.spectators.append(self.users[0])
            # self.users = [ChessAI.ChessAI(self.board, self, chess.WHITE), ChessAI.ChessAI(self.board, self, chess.BLACK)]
            self.current_player = self.users[0]
            self.taken_pieces = {"white": [], "black": []}

        threading.Thread(target=self.timer_thread, daemon=True).start()
        # threading.Thread(target=self.chess_ai_thread, daemon=True).start()

    def database_init(self):
        # Create the table to save chess games if it doesn't exist
        self.database.run("CREATE TABLE IF NOT EXISTS chess_game_saves ("
                          "game_id TEXT PRIMARY KEY, board_epd TEXT, white_hash TEXT, black_hash TEXT, "
                          "current_player TEXT, last_move TEXT, white_time_remaining INTEGER, black_time_remaining INTEGER,"
                          "time_added_per_move INTEGER, timers_enabled BOOLEAN)")

    def user_join(self, user):
        # Check if the user is already in the room
        user.join_room(self)
        if user in self.users + self.spectators:
            return
        if len(self.users) >= self.max_users:
            self.spectators.append(user)
        else:
            self.users.append(user)

    def user_leave(self, user):
        user.leave_room()
        self.users.remove(user)

    def frequent_update(self):
        """
        Data that is sent to the client every second
        :return:
        """
        return {
            "players": [user.encode() for user in self.users],
            "spectators": [user.encode() for user in self.spectators],
            "move_timers": [timer.total_seconds() for timer in self.move_timers],
        }

    def get_board_state(self, user):
        return {
            "your_color": chess.WHITE if user == self.users[0] else chess.BLACK if user in self.users else None,
            "current_player": chess.WHITE if self.board.turn == chess.WHITE else chess.BLACK,
            "board": self.board.epd(hmvc=self.board.halfmove_clock, fmvn=self.board.fullmove_number),
            "last_move": str(self.last_move),
            "state": self.state,
            "timers_enabled": self.timers_enabled,
            "game_over": self.game_over,
            "variant": self.variant,
            "taken_pieces": self.taken_pieces
        }

    def check_win_conditions(self):
        if self.board.is_checkmate():
            self.state = "Checkmate"
            return True
        elif self.board.is_stalemate():
            self.state = "Stalemate"
            return True
        elif self.board.is_insufficient_material():
            self.state = "Insufficient Material"
            return True
        elif self.board.is_seventyfive_moves():
            self.state = "Seventyfive Moves"
            return True
        elif self.board.is_fivefold_repetition():
            self.state = "Fivefold Repetition"
            return True
        elif self.board.is_check():
            self.state = f"{self.current_player.username} is in check"
            return False

        # Run variant specific win conditions
        if self.variant != "Standard":
            if self.board.is_variant_win():
                self.state = "Variant Win"
                return True
            elif self.board.is_variant_loss():
                self.state = "Variant Loss"
                return True
            elif self.board.is_variant_draw():
                self.state = "Variant Draw"
                return True
        return False

    def timer_thread(self):
        """
        This function is called every second and updates the timers if they are enabled
        :return:
        """
        while self.timers_enabled:
            # Only start the timer after the first move
            if not self.board.move_stack:
                time.sleep(1)
                continue

            if self.move_timers[0] <= datetime.timedelta(seconds=0) or self.move_timers[1] <= datetime.timedelta(seconds=0):
                self.state = "Time Up"
                self.game_over = True
            else:
                self.move_timers[0] -= datetime.timedelta(seconds=1) if self.board.turn == chess.WHITE else datetime.timedelta()
                self.move_timers[1] -= datetime.timedelta(seconds=1) if self.board.turn == chess.BLACK else datetime.timedelta()
            time.sleep(1)

    def chess_ai_thread(self):
        """
        This function is called when a chess AI is playing in the room
        :note: The chess AI is always black aka user[1]
        :return:
        """
        ai_exceptions = 0
        while not self.game_over:
            try:
                if isinstance(self.current_player, ChessAI.ChessAI):
                    # self.last_move = self.board.peek()
                    # self.users[1].update_player_move(self.board.peek())
                    # start_time = time.time()
                    ai_move = self.current_player.get_ai_move(self.board)

                    logging.info(self.current_player.ai_move_debug())
                    self.post_move(self.current_player, ai_move)
            except Exception as e:
                logging.exception(e)
                ai_exceptions += 1
                if ai_exceptions >= 5:
                    self.state = "[red]AI Error[/red]"
                    self.game_over = True
                    self.users[1].online = False
                    for player in self.users + self.spectators:
                        player.room_updated = True
            else:
                ai_exceptions = 0
            # time.sleep(random.uniform(0.5, 2.5))  # Sleep for a random amount of time to make it seem more human

    def check_if_capture(self, move):
        """
        Checks if the move will capture a piece and adds it to the taken pieces list
        :param move: The move to check in UCI format
        :return:
        """
        move = chess.Move.from_uci(move)
        # Check if the move is valid
        if move not in self.board.legal_moves:
            return False
        if self.board.is_capture(move):
            # print(f"Move {move.uci()} is a capture")
            piece = self.board.piece_at(move.to_square)
            # Check for en passant
            if piece is None:
                # print(f"Move {move.uci()} is an en passant capture")
                piece = self.board.piece_at(move.to_square + (-8 if self.board.turn == chess.WHITE else 8))
            self.taken_pieces["white" if piece.color == chess.WHITE else "black"].append(piece.symbol())
            # print(f"Taken pieces are now {self.taken_pieces}")

    def post_move(self, user, move):
        # print(user.username, move)

        for player in self.users + self.spectators:
            player.room_updated = True

        # if len(self.users) < 2:
        #     return {"error": "not_enough_players"}

        if user.user_id != self.current_player.user_id:
            logging.info(f"User {user.username} tried to move out of turn, current player is "
                         f"{self.current_player.username}")
            return {"error": "out_of_turn"}

        try:
            self.check_if_capture(move)
            self.board.push_uci(move)
        except chess.IllegalMoveError:
            logging.info(f"User {user.username} tried to make an illegal move")
            return {"error": "illegal_move"}
        except chess.InvalidMoveError:
            logging.info(f"User {user.username} tried to make an invalid move")
            return {"error": "invalid_move"}
        except Exception as e:
            logging.info(f"User {user.username} cause an unknown error: {e}{traceback.format_exc()}")
            return {"error": "unknown_error"}

        self.last_move = move
        self.state = "In Progress"

        # Update the timers
        if self.timers_enabled:
            self.move_timers[0] += self.time_added_per_move if self.board.turn == chess.BLACK else datetime.timedelta()
            self.move_timers[1] += self.time_added_per_move if self.board.turn == chess.WHITE else datetime.timedelta()

        if len(self.users) == 2:
            self.current_player = self.users[1] if self.current_player == self.users[0] else self.users[0]
        else:
            # Add an AI player
            logging.info(f"Adding an AI player to room {self.room_id}")
            self.users.append(ChessAI.ChessAI(self.board, self, chess.BLACK))
            self.current_player = self.users[1]
            threading.Thread(target=self.chess_ai_thread, daemon=True).start()

        if self.check_win_conditions():
            self.game_over = True
            return {"result": "success"}

        time.sleep(1)

        return {"result": "success"}

    def save_game(self):
        """
        Saves the game to the database to be able to be loaded later
        :return:
        """
        self.database.run("INSERT INTO chess_game_saves VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (self.room_id, self.board.epd(hmvc=self.board.halfmove_clock,
                                                        fmvn=self.board.fullmove_number),
                           self.users[0].hash_id, self.users[1].hash_id if len(self.users) == 2 else None,
                           self.board.turn, self.last_move,
                           self.move_timers[0].total_seconds(), self.move_timers[1].total_seconds(),
                           self.time_added_per_move.total_seconds(), self.timers_enabled))
        self.database.run("INSERT INTO room_saves VALUES (?, ?, ?, ?)", (self.room_id, self.__class__.__name__, self.name, self.password))
        return {"room_id": self.room_id, "room_type": "chess"}

    @classmethod
    def get_save_game_info(cls, database, users, room_id):
        """
        Gets the info of a saved game
        :param database: The database to get the info from
        :param users: The users in the room
        :param room_id: The id of the room
        :return: A dictionary of the info
        """
        game = database.get("SELECT * FROM chess_game_saves WHERE game_id = ?", (room_id,))
        if len(game) == 0:
            raise ValueError("Game not found")
        game = game[0]
        user_list = [users.get_user(game[2]).encode()]
        if game[3] is not None:
            user_list.append(users.get_user(game[3]).encode())
        return {
            "room_id": room_id,
            "room_type": cls.__name__,
            "name": database.get("SELECT room_name FROM room_saves WHERE room_id = ?", (room_id,))[0],
            "password_protected": database.get("SELECT room_password FROM room_saves WHERE room_id = ?", (room_id,))[0],
            "users": user_list,
            "max_users": 2,
            "joinable": True,
            "current_player": chess.WHITE if game[4] == chess.WHITE else chess.BLACK
        }

    def load_game(self, game_id, users=None):
        game = self.database.get("SELECT * FROM chess_game_saves WHERE game_id = ?", (game_id,))
        if len(game) == 0:
            raise ValueError("Game not found")
        game = game[0]
        self.board = chess.Board()
        self.board.turn = game[4]
        self.board.set_epd(game[1])
        self.last_move = game[5]
        self.move_timers = [game[6], game[7]]
        self.time_added_per_move = game[8]
        self.timers_enabled = True if game[9] == 1 else False
        self.state = "In Progress"

        self.users = [users.get_user(game[2])]
        if game[3] is not None:
            self.users.append(users.get_user(game[3]))

        self.current_player = self.users[0] if self.board.turn == chess.WHITE else self.users[1]
