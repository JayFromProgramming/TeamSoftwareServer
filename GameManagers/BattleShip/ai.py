import random


class BattleShipAI:

    def __init__(self, board, current_room):
        """
        Creates a new AI to play battleship, when instantiated it will generate a random ship placement
        """
        self.board = board

        self.username = "BattleShipAI"
        self.user_id = -1
        self.online = True
        self.room_updated = False
        self.current_room = current_room

        # AI logic variables
        self.last_shot = None
        self.homing = False  # If the AI is homing in on a ship
        self.direction_established = False  # If the direction of the ship has been established
        self.last_hit = None  # The last hit the AI made
        self.homing_start = None  # The first hit the AI made when homing in on a ship
        self.direction = None  # The estimated direction of the ship (horizontal or vertical)
        self.backtracking = False  # If the AI is backtracking to find the rest of the ship
        self.sunk_ships = []  # A list of the ships that have been sunk
        # It takes 2 hits to establish the direction of the ship once the direction has been established
        # the AI will shoot on that line until it sinks the ship or misses.
        # If the AI misses after establishing a line and it has not sunk the ship it will go in the opposite
        # direction of the line it was shooting on. If it misses again it will go back to shooting randomly.

        self.place_ships()

    def place_ships(self):
        """
        Generates a random ship placement
        :return:
        """
        for ship in self.board.ships:
            while True:
                x = random.randint(0, self.board.size - 1)
                y = random.randint(0, self.board.size - 1)
                direction = random.choice(["horizontal", "vertical"])
                if self.board.place_ship(ship, x, y, direction):
                    break

    def encode(self):
        return {
            "username": self.username,
            "user_id": self.user_id,
            "online": self.online,
        }

    def calc_homing_logic(self, was_hit, enemy_board, backtrack=False):

        if self.direction_established:
            if backtrack and not self.backtracking:
                # If this is the first time backtracking, set the backtracking flag to true
                self.backtracking = True
                self.last_hit = self.homing_start
                match self.direction:
                    case "up":
                        self.direction = "down"
                    case "down":
                        self.direction = "up"
                    case "left":
                        self.direction = "right"
                    case "right":
                        self.direction = "left"

                return self.calc_homing_logic(was_hit, enemy_board)
            elif backtrack and self.backtracking:
                # If this is the second time backtracking, then the AI should go back to shooting randomly
                self.homing = False
                self.direction_established = False
                self.homing_start = None
                self.direction = None
                self.backtracking = False
                return self.get_random_shot(enemy_board)
            else:
                # Continue shooting in the same direction
                match self.direction:
                    case "up":
                        x = self.last_hit[0] - 1
                        y = self.last_hit[1]
                    case "down":
                        x = self.last_hit[0] + 1
                        y = self.last_hit[1]
                    case "left":
                        x = self.last_hit[0]
                        y = self.last_hit[1] - 1
                    case "right":
                        x = self.last_hit[0]
                        y = self.last_hit[1] + 1
                    case _:
                        raise Exception("Invalid direction")
                if x < 0 or x > self.board.size - 1 or y < 0 or y > self.board.size - 1:
                    # If the shot is out of bounds, the AI should go back to shooting randomly
                    self.homing = False
                    self.direction_established = False
                    self.homing_start = None
                    self.direction = None
                    self.backtracking = False
                    return self.get_random_shot(enemy_board)
                self.last_shot = (x, y)
                return {"x": x, "y": y}
        else:
            if was_hit:
                print(f"DIRECTION ESTABLISHED: {self.direction}")
                self.direction_established = True
                return self.calc_homing_logic(was_hit, enemy_board)
            # Pick a random untested direction
            attempts = 0
            while True:
                self.direction = random.choice(["up", "down", "left", "right"])
                x, y = self.last_hit
                match self.direction:
                    case "up":
                        if enemy_board.board[self.homing_start[0] - 1][self.homing_start[1]] == 0 and \
                                self.homing_start[0] - 1 >= 0:  # If the tile above the homing start is untested
                            x = self.homing_start[0] - 1
                    case "down":
                        if enemy_board.board[self.homing_start[0] + 1][self.homing_start[1]] == 0 and \
                                self.homing_start[
                                    0] + 1 < self.board.size:  # If the tile below the homing start is untested
                            x = self.homing_start[0] + 1
                    case "left":
                        if enemy_board.board[self.homing_start[0]][self.homing_start[1] - 1] == 0 and \
                                self.homing_start[
                                    1] - 1 >= 0:  # If the tile to the left of the homing start is untested
                            y = self.homing_start[1] - 1
                    case "right":
                        if enemy_board.board[self.homing_start[0]][self.homing_start[1] + 1] == 0 and \
                                self.homing_start[
                                    1] + 1 < self.board.size:  # If the tile to the right of the homing start is untested
                            y = self.homing_start[1] + 1
                    case _:
                        raise Exception("Invalid direction")
                if x != self.last_hit[0] or y != self.last_hit[1]:
                    break

                attempts += 1
                if attempts > 5:
                    raise Exception("Could not find a valid direction")

            self.last_shot = (x, y)
            return {"x": x, "y": y}

    def get_random_shot(self, enemy_board):
        while True:
            x = random.randint(0, self.board.size - 1)
            y = random.randint(0, self.board.size - 1)
            if enemy_board.board[x][y] == 0:
                self.last_shot = (x, y)
                return {"x": x, "y": y}

    def get_ai_move(self, enemy_board):
        """
        Gets the AI's next move, the AI will start by shooting at random squares, if it hits a ship it will shoot
        around squares it has already shot at until it sinks a ship. If it sinks a ship it will shoot at random
        squares again.
        :param ai_board: The AI's board
        :param enemy_board: The enemy's board
        :return: The AI's next move
        """
        # Determine if the last shot hit a ship
        # Compare the state of the enemy's ships from the last turn to the current turn
        for ship in enemy_board.ships:
            if ship not in self.sunk_ships:
                if ship.sunk:
                    self.sunk_ships.append(ship)
                    self.homing = False
                    self.direction_established = False
                    self.homing_start = None
                    self.direction = None
                    self.backtracking = False
                    return self.get_random_shot(enemy_board)

        if self.last_shot is not None:
            if enemy_board.board[self.last_shot[0]][self.last_shot[1]] == 1:
                self.last_hit = self.last_shot
                if not self.homing:
                    self.homing = True
                    self.homing_start = self.last_shot
                    return self.calc_homing_logic(False, enemy_board)
                else:
                    return self.calc_homing_logic(True, enemy_board)
            else:
                if self.homing:
                    return self.calc_homing_logic(False, enemy_board, backtrack=True)

        return self.get_random_shot(enemy_board)

    def debug(self):
        """
        Print debug information
        :return:
        """
        info = []
        info.append(f"Backtracking: {self.backtracking}")
        info.append(f"Direction established: {self.direction_established}")
        info.append(f"Direction: {self.direction}")
        info.append(f"Homing: {self.homing}")
        info.append(f"Last shot: {self.last_shot}")
        info.append(f"Last hit: {self.last_hit}")
        info.append(f"Homing start: {self.homing_start}")
        info.append(f"Sunk ships: {self.sunk_ships}")
        return "\n".join(info)
