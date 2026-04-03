import math
from engine.pieces import PieceType, Faction
from engine.board  import Board, Move


PIECE_VALUES = {
    PieceType.ZEUS:        10000,
    PieceType.ATHENA:        500,
    PieceType.HERMES:        300,
    PieceType.ARES:          350,
    PieceType.ARTEMIS:       280,
    PieceType.HEPHAESTUS:    200,
    PieceType.APOLLO:        250,
    PieceType.SOLDIER:       100,
}

SOLDIER_TABLE = [
    [ 0,  0,  0,  0,  0,  0,  0,  0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [ 5,  5, 10, 25, 25, 10,  5,  5],
    [ 0,  0,  0, 20, 20,  0,  0,  0],
    [ 5, -5,-10,  0,  0,-10, -5,  5],
    [ 5, 10, 10,-20,-20, 10, 10,  5],
    [ 0,  0,  0,  0,  0,  0,  0,  0],
]

CENTER_TABLE = [
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5, 10, 10,  5,  0,-10],
    [-10,  5,  5, 10, 10,  5,  5,-10],
    [-10,  0, 10, 10, 10, 10,  0,-10],
    [-10,  5, 10, 10, 10, 10,  5,-10],
    [-10,  0,  5,  0,  0,  5,  0,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20],
]

ZEUS_SAFETY = [
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-20,-30,-30,-40,-40,-30,-30,-20],
    [-10,-20,-20,-20,-20,-20,-20,-10],
    [ 20, 20,  0,  0,  0,  0, 20, 20],
    [ 20, 30, 10,  0,  0, 10, 30, 20],
]


def _pos_score(piece):
    # returns a positional bonus for a piece based on its type and location on the board
    r = piece.row if piece.faction == Faction.OLYMPUS else 7 - piece.row
    c = piece.col
    if piece.piece_type == PieceType.SOLDIER:
        return SOLDIER_TABLE[r][c]
    if piece.piece_type == PieceType.ZEUS:
        return ZEUS_SAFETY[r][c]
    return CENTER_TABLE[r][c]


def evaluate(board, ai_faction):
    # scores the board from the ai factions perspective combining material position and mobility
    if board.winner == ai_faction:
        return 99999
    if board.winner is not None:
        return -99999
    if board.is_draw:
        return 0

    enemy = (Faction.UNDERWORLD if ai_faction == Faction.OLYMPUS
        else Faction.OLYMPUS)
    score = 0

    for r in range(8):
        for c in range(8):
            p = board.grid[r][c]
            if p is None:
                continue
            val = PIECE_VALUES[p.piece_type]
            if p.piece_type == PieceType.HEPHAESTUS:
                val = val * p.hp // 3
            ps = val + _pos_score(p)
            score += ps if p.faction == ai_faction else -ps

    ai_mob = len(board.get_all_legal_moves(ai_faction))
    en_mob = len(board.get_all_legal_moves(enemy))
    score += (ai_mob - en_mob) * 2

    for p in board.get_pieces(ai_faction):
        if board.hephaestus_adjacent_bonus(p):
            score += 15

    return score


def _order_moves(moves):
    # sorts moves so captures are evaluated first to improve alpha beta pruning efficiency
    def key(m):
        if m.move_type in ("capture", "artemis_capture", "godfall"):
            cap = m.captured_piece
            return (PIECE_VALUES.get(cap.piece_type, 0)
                    - PIECE_VALUES.get(m.piece.piece_type, 0) // 10) if cap else 0
        if m.move_type == "heph_attack":
            return 50
        return 0
    return sorted(moves, key=key, reverse=True)


class AIEngine:
    def __init__(self, ai_faction: Faction, depth: int = 3):
        # initialises the ai engine with a faction to play for and a search depth
        self.ai_faction      = ai_faction
        self.depth           = depth
        self.nodes_evaluated = 0

    def get_best_move(self, board):
        # runs minimax from the root and returns the best move found for the ai faction
        self.nodes_evaluated = 0
        moves = _order_moves(
            board.get_all_legal_moves(self.ai_faction)
            + board.get_hephaestus_attack_moves(self.ai_faction)
        )
        if not moves:
            return None

        best_move  = None
        best_score = -math.inf
        alpha      = -math.inf
        beta       =  math.inf

        for move in moves:
            sim = board.copy()
            self._sim_apply(sim, move)
            score = self._minimax(sim, self.depth - 1, alpha, beta, False)
            if score > best_score:
                best_score = score
                best_move  = move
            alpha = max(alpha, best_score)

        return best_move

    def _minimax(self, board, depth, alpha, beta, maximising):
        # recursively evaluates board positions using minimax with alpha beta cutoffs
        self.nodes_evaluated += 1

        if board.winner is not None or board.is_draw or depth == 0:
            return evaluate(board, self.ai_faction)

        cur = (self.ai_faction if maximising
            else (Faction.UNDERWORLD if self.ai_faction == Faction.OLYMPUS
                else Faction.OLYMPUS))

        moves = _order_moves(
            board.get_all_legal_moves(cur)
            + board.get_hephaestus_attack_moves(cur)
        )
        if not moves:
            return 0

        if maximising:
            best = -math.inf
            for m in moves:
                sim = board.copy()
                self._sim_apply(sim, m)
                val   = self._minimax(sim, depth - 1, alpha, beta, False)
                best  = max(best, val)
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
            return best
        else:
            best = math.inf
            for m in moves:
                sim = board.copy()
                self._sim_apply(sim, m)
                val  = self._minimax(sim, depth - 1, alpha, beta, True)
                best = min(best, val)
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return best

    def _sim_apply(self, board, move):
        # applies a move to a simulation board auto promoting soldiers to ares
        sp = board.grid[move.from_row][move.from_col]
        if sp is None:
            return
        cap = (board.grid[move.to_row][move.to_col]
            if move.move_type not in ("swap", "artemis_capture")
            else move.captured_piece)
        st  = (board.grid[move.to_row][move.to_col]
            if move.move_type == "swap" else None)
        sm  = Move(sp, move.to_row, move.to_col, move.move_type,
            captured_piece=cap, swap_target=st)
        board.apply_move(sm, promotion_choice=PieceType.ARES)
