from enum import Enum


class Faction(Enum):
    OLYMPUS    = "olympus"
    UNDERWORLD = "underworld"


class PieceType(Enum):
    ZEUS       = "zeus"
    ATHENA     = "athena"
    HERMES     = "hermes"
    ARES       = "ares"
    ARTEMIS    = "artemis"
    HEPHAESTUS = "hephaestus"
    APOLLO     = "apollo"
    SOLDIER    = "soldier"


PIECE_NAMES = {
    Faction.OLYMPUS: {
        PieceType.ZEUS:       "Zeus",
        PieceType.ATHENA:     "Athena",
        PieceType.HERMES:     "Hermes",
        PieceType.ARES:       "Ares",
        PieceType.ARTEMIS:    "Artemis",
        PieceType.HEPHAESTUS: "Hephaestus",
        PieceType.APOLLO:     "Apollo",
        PieceType.SOLDIER:    "Soldier",
    },
    Faction.UNDERWORLD: {
        PieceType.ZEUS:       "Hades",
        PieceType.ATHENA:     "Hecate",
        PieceType.HERMES:     "Charon",
        PieceType.ARES:       "Thanatos",
        PieceType.ARTEMIS:    "Nyx",
        PieceType.HEPHAESTUS: "Cerberus",
        PieceType.APOLLO:     "Morpheus",
        PieceType.SOLDIER:    "Shade",
    },
}

PIECE_SHORT = {
    PieceType.ZEUS:       "King",
    PieceType.ATHENA:     "Ext Knight",
    PieceType.HERMES:     "Speed Runner",
    PieceType.ARES:       "Forced Attacker",
    PieceType.ARTEMIS:    "Ranged Striker",
    PieceType.HEPHAESTUS: "Wall 3HP",
    PieceType.APOLLO:     "Swapper",
    PieceType.SOLDIER:    "Foot Soldier",
}


class Piece:
    def __init__(self, piece_type: PieceType, faction: Faction, row: int, col: int):
        # initialises a piece with its type faction position hp and cooldown
        self.piece_type    = piece_type
        self.faction       = faction
        self.row           = row
        self.col           = col
        self.hp            = 3 if piece_type == PieceType.HEPHAESTUS else 1
        self.swap_cooldown = 0

    @property
    def name(self):
        # returns the display name of this piece based on its faction
        return PIECE_NAMES[self.faction][self.piece_type]

    @property
    def short(self):
        # returns a short label describing this piece type
        return PIECE_SHORT[self.piece_type]

    @property
    def enemy_faction(self):
        # returns the faction that is the opponent of this piece
        return Faction.UNDERWORLD if self.faction == Faction.OLYMPUS else Faction.OLYMPUS

    @property
    def forward(self):
        # returns the row direction a soldier advances toward the enemy back row
        return -1 if self.faction == Faction.OLYMPUS else 1

    def get_valid_moves(self, board):
        # dispatches to the correct move generator based on piece type
        dispatch = {
            PieceType.ZEUS:       self._zeus_moves,
            PieceType.ATHENA:     self._athena_moves,
            PieceType.HERMES:     self._hermes_moves,
            PieceType.ARES:       self._ares_moves,
            PieceType.ARTEMIS:    self._artemis_moves,
            PieceType.HEPHAESTUS: self._hephaestus_moves,
            PieceType.APOLLO:     self._apollo_moves,
            PieceType.SOLDIER:    self._soldier_moves,
        }
        return dispatch[self.piece_type](board)

    def get_capture_squares(self, board):
        # returns squares this piece threatens used for zeus safety checking
        if self.piece_type == PieceType.ARTEMIS:
            return self._artemis_threat_squares(board)
        if self.piece_type == PieceType.HEPHAESTUS:
            return []
        return self.get_valid_moves(board)

    def _zeus_moves(self, board):
        # returns all squares zeus can move to one step in any direction
        moves = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                r, c = self.row + dr, self.col + dc
                if board.in_bounds(r, c):
                    t = board.grid[r][c]
                    if t is None or t.faction != self.faction:
                        moves.append((r, c))
        return moves

    def _athena_moves(self, board):
        # returns all squares athena can jump to using the extended knight pattern
        moves = []
        for dr, dc in [(3,1),(3,-1),(-3,1),(-3,-1),(1,3),(1,-3),(-1,3),(-1,-3)]:
            r, c = self.row + dr, self.col + dc
            if board.in_bounds(r, c):
                t = board.grid[r][c]
                if t is None or t.faction != self.faction:
                    moves.append((r, c))
        return moves

    def _hermes_moves(self, board):
        # returns squares hermes can reach moving up to three steps straight and stopping at blockers
        moves = []
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            for step in range(1, 4):
                r, c = self.row + dr*step, self.col + dc*step
                if not board.in_bounds(r, c):
                    break
                t = board.grid[r][c]
                if t is None:
                    moves.append((r, c))
                elif t.faction != self.faction:
                    moves.append((r, c))
                    break
                else:
                    break
        return moves

    def _ares_moves(self, board):
        # returns forced capture squares if enemies are nearby otherwise free movement squares
        forced = []
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                if dr == 0 and dc == 0:
                    continue
                r, c = self.row + dr, self.col + dc
                if board.in_bounds(r, c):
                    t = board.grid[r][c]
                    if (t is not None
                            and t.faction != self.faction
                            and t.piece_type != PieceType.HEPHAESTUS):
                        forced.append((r, c))
        if forced:
            return forced
        moves = []
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                if dr == 0 and dc == 0:
                    continue
                r, c = self.row + dr, self.col + dc
                if board.in_bounds(r, c):
                    t = board.grid[r][c]
                    if t is None or t.faction != self.faction:
                        moves.append((r, c))
        return moves

    def _artemis_moves(self, board):
        # returns empty diagonal squares artemis can move to one step away
        moves = []
        for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            r, c = self.row + dr, self.col + dc
            if board.in_bounds(r, c) and board.grid[r][c] is None:
                moves.append((r, c))
        return moves

    def get_artemis_captures(self, board):
        # returns enemy squares artemis can ranged capture two diagonal steps away with empty gap
        captures = []
        for dr, dc in [(-2,-2),(-2,2),(2,-2),(2,2)]:
            r, c   = self.row + dr, self.col + dc
            mr, mc = self.row + dr//2, self.col + dc//2
            if board.in_bounds(r, c):
                t   = board.grid[r][c]
                gap = board.grid[mr][mc]
                if t is not None and t.faction != self.faction and gap is None:
                    captures.append((r, c))
        return captures

    def _artemis_threat_squares(self, board):
        # returns squares artemis threatens for the zeus safety check
        threats = []
        for dr, dc in [(-2,-2),(-2,2),(2,-2),(2,2)]:
            r, c   = self.row + dr, self.col + dc
            mr, mc = self.row + dr//2, self.col + dc//2
            if board.in_bounds(r, c) and board.grid[mr][mc] is None:
                threats.append((r, c))
        return threats

    def _hephaestus_moves(self, board):
        # returns empty list because hephaestus cannot move
        return []

    def _apollo_moves(self, board):
        # returns squares apollo can move to one step in any direction
        moves = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                r, c = self.row + dr, self.col + dc
                if board.in_bounds(r, c):
                    t = board.grid[r][c]
                    if t is None or t.faction != self.faction:
                        moves.append((r, c))
        return moves

    def get_apollo_swaps(self, board):
        # returns positions of friendly pieces apollo can swap with excluding zeus and checking cooldown
        if self.swap_cooldown > 0:
            return []
        swaps = []
        for r in range(8):
            for c in range(8):
                p = board.grid[r][c]
                if (p is not None
                        and p.faction == self.faction
                        and p is not self
                        and p.piece_type != PieceType.ZEUS):
                    swaps.append((r, c))
        return swaps

    def _soldier_moves(self, board):
        # returns squares a soldier can move to advancing forward one square or capturing diagonally
        moves = []
        fwd = self.forward
        r, c = self.row + fwd, self.col
        if board.in_bounds(r, c) and board.grid[r][c] is None:
            moves.append((r, c))
        for dc in (-1, 1):
            rc, cc = self.row + fwd, self.col + dc
            if board.in_bounds(rc, cc):
                t = board.grid[rc][cc]
                if t is not None and t.faction != self.faction:
                    moves.append((rc, cc))
        return moves

    def copy(self):
        # creates a deep copy of this piece preserving all state
        p = Piece(self.piece_type, self.faction, self.row, self.col)
        p.hp            = self.hp
        p.swap_cooldown = self.swap_cooldown
        return p

    def __repr__(self):
        # returns a string representation of this piece with its position
        return f"{self.name}({self.row},{self.col})"
