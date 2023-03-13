"""
Modified from the original code by Dirk Hoekstra (https://github.com/Dirk94/ChessAI)
"""

# from GameAI.ChessAI import board
import time

from GameAI.ChessAI import ai

import chess


class ChessAI:

    def __init__(self, room_board, current_room):
        self.room_board = room_board
        self.ai = ai.AI()

        self.username = "ChessAI"
        self.user_id = -1
        self.online = True

        self.current_room = current_room
        self.last_ai_moves = []

    def encode(self):
        return {
            "username": self.username,
            "user_id": self.user_id,
            "online": self.online,
        }

    def get_last_move_debug(self):
        return self.ai.total_moves_checked

    def get_ai_move(self, board: chess.Board) -> str:
        move = self.ai.get_ai_move(board, self.last_ai_moves)
        # To prevent the AI from just moving the same piece back and forth we will check if the move is the same
        # as the last 2 moves. If it is we will get a new move.
        if move is None:
            # If the AI wasn't able to find a move with the move restriction we will try again without the restriction.
            move = self.ai.get_ai_move(board)
        self.last_ai_moves.append(move)
        if len(self.last_ai_moves) > 4:  # Only restrict a repeat of the last 4 moves.
            self.last_ai_moves.pop(0)
        return move.uci()
