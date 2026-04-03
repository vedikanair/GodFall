from engine.pieces import Piece, PieceType, Faction


class Move:
    def __init__(self, piece, to_row, to_col,
            move_type="move",
            captured_piece=None,
            swap_target=None,
            promotion=None):
        # stores all information about a single game action
        self.piece          = piece
        self.from_row       = piece.row
        self.from_col       = piece.col
        self.to_row         = to_row
        self.to_col         = to_col
        self.move_type      = move_type
        self.captured_piece = captured_piece
        self.swap_target    = swap_target
        self.promotion      = promotion

    def __repr__(self):
        # returns a readable string showing the move from and to coordinates
        return (f"{self.piece.name}({self.from_row},{self.from_col})"
                f"->({self.to_row},{self.to_col})[{self.move_type}]")


class Board:
    def __init__(self):
        # sets up a new board with starting piece layout and initial turn
        self.grid         = [[None] * 8 for _ in range(8)]
        self.turn         = Faction.OLYMPUS
        self.move_history = []
        self.winner       = None
        self.is_draw      = False
        self._setup()

    def _setup(self):
        # places all pieces in their starting positions for both factions
        uw_back = [
            PieceType.HERMES, PieceType.ARES,   PieceType.ATHENA,
            PieceType.ZEUS,
            PieceType.APOLLO, PieceType.ARTEMIS, PieceType.HEPHAESTUS, PieceType.HERMES,
        ]
        for c, pt in enumerate(uw_back):
            self.grid[0][c] = Piece(pt, Faction.UNDERWORLD, 0, c)

        self.grid[1][0] = Piece(PieceType.ARES,       Faction.UNDERWORLD, 1, 0)
        for c in range(1, 7):
            self.grid[1][c] = Piece(PieceType.SOLDIER, Faction.UNDERWORLD, 1, c)
        self.grid[1][7] = Piece(PieceType.HEPHAESTUS, Faction.UNDERWORLD, 1, 7)

        self.grid[6][0] = Piece(PieceType.HEPHAESTUS, Faction.OLYMPUS, 6, 0)
        for c in range(1, 7):
            self.grid[6][c] = Piece(PieceType.SOLDIER, Faction.OLYMPUS, 6, c)
        self.grid[6][7] = Piece(PieceType.ARES,       Faction.OLYMPUS, 6, 7)

        ol_back = [
            PieceType.HERMES, PieceType.HEPHAESTUS, PieceType.ARTEMIS,
            PieceType.APOLLO,
            PieceType.ZEUS,
            PieceType.ATHENA, PieceType.ARES, PieceType.HERMES,
        ]
        for c, pt in enumerate(ol_back):
            self.grid[7][c] = Piece(pt, Faction.OLYMPUS, 7, c)

    def in_bounds(self, r, c):
        # returns true if the row and column are inside the 8x8 grid
        return 0 <= r < 8 and 0 <= c < 8

    def get_pieces(self, faction):
        # returns a list of all living pieces belonging to the given faction
        return [self.grid[r][c]
                for r in range(8) for c in range(8)
                if self.grid[r][c] is not None
                and self.grid[r][c].faction == faction]

    def get_zeus(self, faction):
        # finds and returns the zeus piece for a faction or none if captured
        for p in self.get_pieces(faction):
            if p.piece_type == PieceType.ZEUS:
                return p
        return None

    def get_threatened_squares(self, faction):
        # returns the set of all squares the enemy of faction currently threatens
        enemy = (Faction.UNDERWORLD if faction == Faction.OLYMPUS
                 else Faction.OLYMPUS)
        threatened = set()
        for p in self.get_pieces(enemy):
            for sq in p.get_capture_squares(self):
                threatened.add(sq)
        return threatened

    def hephaestus_adjacent_bonus(self, piece):
        # returns true if a friendly hephaestus is orthogonally adjacent to the given piece
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            r, c = piece.row + dr, piece.col + dc
            if self.in_bounds(r, c):
                n = self.grid[r][c]
                if (n is not None
                        and n.faction == piece.faction
                        and n.piece_type == PieceType.HEPHAESTUS):
                    return True
        return False

    def get_all_legal_moves(self, faction):
        # generates every legal move for the given faction filtering out moves that expose zeus
        moves      = []
        threatened = self.get_threatened_squares(faction)

        for piece in self.get_pieces(faction):
            if piece.piece_type == PieceType.HEPHAESTUS:
                continue

            raw = piece.get_valid_moves(self)

            if (self.hephaestus_adjacent_bonus(piece)
                    and piece.piece_type == PieceType.HERMES):
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    for step in range(1, 5):
                        r, c = piece.row + dr*step, piece.col + dc*step
                        if not self.in_bounds(r, c):
                            break
                        t = self.grid[r][c]
                        if t is None:
                            if (r, c) not in raw:
                                raw.append((r, c))
                        elif t.faction != piece.faction:
                            if (r, c) not in raw:
                                raw.append((r, c))
                            break
                        else:
                            break

            for to_r, to_c in raw:
                t     = self.grid[to_r][to_c]
                mtype = "capture" if t is not None else "move"

                if piece.piece_type == PieceType.ZEUS and (to_r, to_c) in threatened:
                    continue
                if self._leaves_zeus_exposed(piece, to_r, to_c, mtype, faction):
                    continue

                moves.append(Move(piece, to_r, to_c, mtype, captured_piece=t))

            if piece.piece_type == PieceType.ARTEMIS:
                for to_r, to_c in piece.get_artemis_captures(self):
                    t = self.grid[to_r][to_c]
                    moves.append(Move(piece, piece.row, piece.col,
                                      "artemis_capture", captured_piece=t))

            if piece.piece_type == PieceType.APOLLO:
                for sw_r, sw_c in piece.get_apollo_swaps(self):
                    st = self.grid[sw_r][sw_c]
                    moves.append(Move(piece, sw_r, sw_c, "swap", swap_target=st))

        return moves

    def get_hephaestus_attack_moves(self, faction):
        # returns moves where any piece adjacent to an enemy hephaestus attacks it
        moves = []
        enemy = (Faction.UNDERWORLD if faction == Faction.OLYMPUS
                 else Faction.OLYMPUS)
        for ep in self.get_pieces(enemy):
            if ep.piece_type != PieceType.HEPHAESTUS:
                continue
            for ap in self.get_pieces(faction):
                if (abs(ap.row - ep.row) <= 1
                        and abs(ap.col - ep.col) <= 1
                        and ap is not ep):
                    moves.append(Move(ap, ep.row, ep.col,
                                      "heph_attack", captured_piece=ep))
        return moves

    def _leaves_zeus_exposed(self, piece, to_r, to_c, move_type, faction):
        # checks if making a move would leave the factions zeus in a threatened square
        zeus = self.get_zeus(faction)
        if zeus is None:
            return False
        tmp = self.copy()
        tmp._apply_raw(piece.row, piece.col, to_r, to_c, move_type)
        tz  = tmp.get_zeus(faction)
        if tz is None:
            return True
        return (tz.row, tz.col) in tmp.get_threatened_squares(faction)

    def _apply_raw(self, fr, fc, tr, tc, move_type):
        # applies a move directly to the grid without validation used for simulation only
        piece = self.grid[fr][fc]
        if piece is None:
            return
        if move_type == "swap":
            tgt = self.grid[tr][tc]
            if tgt:
                tgt.row, tgt.col = fr, fc
                self.grid[fr][fc] = tgt
            else:
                self.grid[fr][fc] = None
            piece.row, piece.col = tr, tc
            self.grid[tr][tc] = piece
        elif move_type == "artemis_capture":
            self.grid[tr][tc] = None
        elif move_type == "heph_attack":
            tgt = self.grid[tr][tc]
            if tgt:
                tgt.hp -= 1
                if tgt.hp <= 0:
                    self.grid[tr][tc] = None
        else:
            self.grid[tr][tc] = piece
            self.grid[fr][fc] = None
            piece.row, piece.col = tr, tc

    def apply_move(self, move, promotion_choice=None):
        # executes a validated move updates the board state and returns the result string
        piece  = move.piece
        result = None

        if move.move_type == "swap":
            tgt = move.swap_target
            self.grid[piece.row][piece.col] = tgt
            self.grid[move.to_row][move.to_col] = piece
            if tgt:
                tgt.row, tgt.col = piece.row, piece.col
            piece.row, piece.col = move.to_row, move.to_col
            piece.swap_cooldown = 2

        elif move.move_type == "artemis_capture":
            cap = self.grid[move.to_row][move.to_col]
            if cap:
                if cap.piece_type == PieceType.ZEUS:
                    self.winner = piece.faction
                    result = "godfall"
                self.grid[move.to_row][move.to_col] = None
                result = result or "capture"

        elif move.move_type == "heph_attack":
            tgt = self.grid[move.to_row][move.to_col]
            if tgt and tgt.piece_type == PieceType.HEPHAESTUS:
                tgt.hp -= 1
                if tgt.hp <= 0:
                    self.grid[move.to_row][move.to_col] = None
                    result = "capture"
                else:
                    result = "heph_hit"

        else:
            cap = self.grid[move.to_row][move.to_col]
            if cap:
                if cap.piece_type == PieceType.ZEUS:
                    self.winner = piece.faction
                    result = "godfall"
                result = result or "capture"
            self.grid[move.to_row][move.to_col] = piece
            self.grid[piece.row][piece.col] = None
            piece.row, piece.col = move.to_row, move.to_col

            if piece.piece_type == PieceType.SOLDIER:
                last = 7 if piece.faction == Faction.OLYMPUS else 0
                if piece.row == last:
                    promo = promotion_choice or PieceType.HERMES
                    piece.piece_type = promo
                    result = "promotion"

        for p in self.get_pieces(self.turn):
            if p.piece_type == PieceType.APOLLO and p.swap_cooldown > 0:
                p.swap_cooldown -= 1

        self.move_history.append(move)
        self.turn = (Faction.UNDERWORLD if self.turn == Faction.OLYMPUS
                     else Faction.OLYMPUS)

        if self.winner is None:
            nxt = (self.get_all_legal_moves(self.turn)
                   + self.get_hephaestus_attack_moves(self.turn))
            if not nxt:
                self.is_draw = True
                result = "draw"

        return result

    def copy(self):
        # creates a full deep copy of the board for use in ai simulation
        nb = Board.__new__(Board)
        nb.grid = [[None]*8 for _ in range(8)]
        for r in range(8):
            for c in range(8):
                if self.grid[r][c] is not None:
                    nb.grid[r][c] = self.grid[r][c].copy()
        nb.turn         = self.turn
        nb.move_history = []
        nb.winner       = self.winner
        nb.is_draw      = self.is_draw
        return nb
