import random
import time

import chess
import numpy


class Heuristics:
    # The tables denote the points scored for the position of the chess pieces on the board.

    PAWN_TABLE = numpy.array([
        [0, 0, 0, 0, 0, 0, 0, 0],
        [5, 10, 10, -20, -20, 10, 10, 5],
        [5, -5, -10, 0, 0, -10, -5, 5],
        [0, 0, 0, 20, 20, 0, 0, 0],
        [5, 5, 10, 25, 25, 10, 5, 5],
        [10, 10, 20, 30, 30, 20, 10, 10],
        [50, 50, 50, 50, 50, 50, 50, 50],
        [100, 100, 100, 100, 100, 100, 100, 100]
    ])

    KNIGHT_TABLE = numpy.array([
        [-50, -40, -30, -30, -30, -30, -40, -50],
        [-40, -20, 0, 5, 5, 0, -20, -40],
        [-30, 5, 10, 15, 15, 10, 5, -30],
        [-30, 0, 15, 20, 20, 15, 0, -30],
        [-30, 5, 15, 20, 20, 15, 0, -30],
        [-30, 0, 10, 15, 15, 10, 0, -30],
        [-40, -20, 0, 0, 0, 0, -20, -40],
        [-50, -40, -30, -30, -30, -30, -40, -50]
    ])

    BISHOP_TABLE = numpy.array([
        [-20, -10, -10, -10, -10, -10, -10, -20],
        [-10, 5, 0, 0, 0, 0, 5, -10],
        [-10, 10, 10, 10, 10, 10, 10, -10],
        [-10, 0, 10, 10, 10, 10, 0, -10],
        [-10, 5, 5, 10, 10, 5, 5, -10],
        [-10, 0, 5, 10, 10, 5, 0, -10],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-20, -10, -10, -10, -10, -10, -10, -20]
    ])

    ROOK_TABLE = numpy.array([
        [-10, -5, 0, 5, 5, 0, -5, -10],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [5, 10, 10, 10, 10, 10, 10, 5],
        [0, 0, 0, 0, 0, 0, 0, 0]
    ])

    QUEEN_TABLE = numpy.array([
        [-20, -10, -10, -5, -5, -10, -10, -20],
        [-10, 0, 5, 0, 0, 0, 0, -10],
        [-10, 5, 5, 5, 5, 5, 0, -10],
        [0, 0, 5, 5, 5, 5, 0, -5],
        [-5, 0, 5, 5, 5, 5, 0, -5],
        [-10, 0, 5, 5, 5, 5, 0, -10],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-20, -10, -10, -5, -5, -10, -10, -20]
    ])

    piece_values = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 1500
    }

    @staticmethod
    def evaluate(board, ai_color):
        """
        Evaluates the board
        :param board:
        :param ai_color: The color of the AI
        :return:
        """

        if board.is_checkmate():
            if board.turn == ai_color:
                return -9999999
            else:
                return 9999999

        # Preform check evaluation

        material = Heuristics.get_material_score(board, ai_color)

        pawns = Heuristics.get_piece_position_score(board, chess.PAWN, Heuristics.PAWN_TABLE)
        knights = Heuristics.get_piece_position_score(board, chess.KNIGHT, Heuristics.KNIGHT_TABLE)
        bishops = Heuristics.get_piece_position_score(board, chess.BISHOP, Heuristics.BISHOP_TABLE)
        rooks = Heuristics.get_piece_position_score(board, chess.ROOK, Heuristics.ROOK_TABLE)
        queens = Heuristics.get_piece_position_score(board, chess.QUEEN, Heuristics.QUEEN_TABLE)

        if board.is_check():
            if board.turn == ai_color:  # AI is in check
                return -9999 + material + pawns + knights + bishops + rooks + queens
            else:
                return 99 + material + pawns + knights + bishops + rooks + queens

        return material + pawns + knights + bishops + rooks + queens

    # Returns the score for the position of the given type of piece.
    # A piece type can for example be: pieces.Pawn.PIECE_TYPE.
    # The table is the 2d numpy array used for the scoring. Example: Heuristics.PAWN_TABLE
    @staticmethod
    def get_piece_position_score(chess_board: chess.Board, piece_type, table):
        white = 0
        black = 0
        for x in range(8):
            for y in range(8):
                piece = chess_board.piece_at(chess.square(x, y))
                if piece:
                    if piece.piece_type == piece_type:
                        if piece.color == chess.WHITE:
                            white += table[x][y]
                        else:
                            black += table[7 - x][y]

        return white - black

    @staticmethod
    def get_material_score(chess_board: chess.Board, ai_color):
        """
        Returns the score for the material on the board.
        :param chess_board:
        :param ai_color: The color of the AI, used to determine which pieces are positive and negative.
        :return:
        """
        white = 0
        black = 0
        for x in range(8):
            for y in range(8):
                piece = chess_board.piece_at(chess.square(x, y))
                if piece:
                    if piece.color == chess.WHITE:
                        white += Heuristics.piece_values[piece.piece_type]
                    else:
                        black += Heuristics.piece_values[piece.piece_type]
        if ai_color == chess.WHITE:
            return white - black
        else:
            return black - white


class AI:
    INFINITE = 10000000

    def __init__(self, color):
        # These values are used to display debug information about the last move calculated.
        self.total_moves_checked = 0
        self.best_move_score = 0
        self.total_optimal_moves = 0
        self.calculate_time = 0
        self.total_legal_moves = 0
        self.search_depth = 0
        self.color = color
        self.highest_score_calculated = -AI.INFINITE

    def get_ai_move(self, chessboard: chess.Board, invalid_moves, depth=2,
                    time_limit=60, skill=1):
        """
        Returns the best move for the AI.
        :param chessboard:  The chessboard
        :param invalid_moves: The moves that are not allowed, used to prevent the AI from repeating the same move.
        :param depth: The maximum depth to search.
        :param time_limit: The maximum time to search.
        :param skill: The skill of the AI. 1 is the full skill, 0 is zero skill.
        :return:
        """
        best_move = []
        best_score = -AI.INFINITE
        start_time = time.time()
        self.total_moves_checked = 0
        self.highest_score_calculated = -AI.INFINITE

        # If the total number of legal moves is less than 10, then increase the depth by 1.
        if chessboard.legal_moves.count() < 10:
            depth += 1
        self.search_depth = depth
        self.total_legal_moves = chessboard.legal_moves.count()
        for move in chessboard.legal_moves:
            if move in invalid_moves:
                continue

            copy = chessboard.copy()
            copy.push(move)

            if time.time() - start_time > time_limit:
                break

            # Calculate the value of this move
            score = self.alphabeta(copy, depth, -AI.INFINITE, AI.INFINITE, False)
            if score > best_score:  # If the score is better, choose this move.
                self.highest_score_calculated = score
                if random.random() > skill:  # If the skill is not 1, then randomly skip some moves.
                    continue  # This is to reduce the skill of the AI.
                best_score = score
                best_move = [move]
            elif score == best_score:  # If the score is the same, choose a random move.
                best_move.append(move)

        self.total_optimal_moves = len(best_move)
        self.best_move_score = best_score
        self.calculate_time = time.time() - start_time
        return random.choice(best_move)

    @staticmethod
    def is_invalid_move(move, invalid_moves):
        for invalid_move in invalid_moves:
            if invalid_move.equals(move):
                return True
        return False

    # @staticmethod
    # def minimax(board, depth, maximizing):
    #     if depth == 0:
    #         return Heuristics.evaluate(board)
    #
    #     if maximizing:
    #         best_score = -AI.INFINITE
    #         for move in board.get_possible_moves():
    #             copy = board.Board.clone(board)
    #             copy.perform_move(move)
    #
    #             score = AI.minimax(copy, depth - 1, False)
    #             best_score = max(best_score, score)
    #
    #         return best_score
    #     else:
    #         best_score = AI.INFINITE
    #         for move in board.get_possible_moves():
    #             copy = board.Board.clone(board)
    #             copy.perform_move(move)
    #
    #             score = AI.minimax(copy, depth - 1, True)
    #             best_score = min(best_score, score)
    #
    #         return best_score

    def alphabeta(self, chessboard: chess.Board, depth, a, b, maximizing):
        """
        Alpha beta pruning
        :param chessboard: The chessboard
        :param depth:  The depth of the search (how many moves ahead)
        :param a:   The alpha value (best score for the maximizing player)
        :param b:   The beta value (best score for the minimizing player)
        :param maximizing: True if maximizing, false if minimizing
        :return:   The score
        """
        if depth == 0:  # If we have reached the end of the search
            return Heuristics.evaluate(chessboard, self.color)

        if maximizing:  # If we are maximizing
            best_score = -AI.INFINITE
            for move in chessboard.legal_moves:  # For each move
                self.total_moves_checked += 1
                copy = chessboard.copy()
                copy.push(move)

                score = self.alphabeta(copy, depth - 1, a, b, False)  # Calculate the score of this move
                best_score = max(best_score, score)  # Choose the best score
                a = max(a, best_score)  # Update the alpha value
                if b <= a:  # If the beta value is less than or equal to the alpha value, then we can prune this branch.
                    break
            return best_score
        else:  # If we are minimizing
            best_score = AI.INFINITE
            for move in chessboard.legal_moves:  # For each move
                self.total_moves_checked += 1
                copy = chessboard.copy()
                copy.push(move)

                score = self.alphabeta(copy, depth - 1, a, b, True)  # Calculate the score of this move
                best_score = min(best_score, score)  # Choose the best score
                b = min(b, best_score)  # Update the beta value
                if b <= a:  # If the beta value is less than or equal to the alpha value, then we can prune this branch.
                    break
            return best_score

