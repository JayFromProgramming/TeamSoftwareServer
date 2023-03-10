"""
Modified from the original code by Dirk Hoekstra (https://github.com/Dirk94/ChessAI)
"""

from GameAI.ChessAI import board
from GameAI.ChessAI import ai
from GameAI.ChessAI import pieces

import chess


class ChessAI:

    def __init__(self, room_board, current_room):
        self.room_board = room_board
        self.board = board.Board.new()

        self.username = "ChessAI"
        self.user_id = -1
        self.online = True

        self.current_room = current_room

    def encode(self):
        return {
            "username": self.username,
            "user_id": self.user_id,
            "online": self.online,
        }

    @staticmethod
    def convert_chess_move_to_board_move(chess_move: chess.Move):
        from_x = chess_move.from_square % 8
        from_y = chess_move.from_square // 8
        to_x = chess_move.to_square % 8
        to_y = chess_move.to_square // 8
        # For some reason the board is upside down from the ai's perspective, so we need to rotate the board
        from_x = 7 - from_x
        to_x = 7 - to_x
        from_y = 7 - from_y
        to_y = 7 - to_y
        return pieces.Move(from_x, from_y, to_x, to_y)

    @staticmethod
    def convert_board_move_to_chess_move(board_move: pieces.Move):
        from_square = board_move.xfrom + board_move.yfrom * 8
        to_square = board_move.xto + board_move.yto * 8
        # We also need to rotate the board back
        from_square = 63 - from_square
        to_square = 63 - to_square
        chess_move = chess.Move(from_square, to_square)
        return chess_move

    def update_player_move(self, move: chess.Move):
        move_obj = self.convert_chess_move_to_board_move(move)
        self.board.perform_move(move_obj)

    def get_ai_move(self):
        ai_move = ai.AI.get_ai_move(self.board, [])
        self.board.perform_move(ai_move)
        return self.convert_board_move_to_chess_move(ai_move).uci()
