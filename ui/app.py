import tkinter as tk
from tkinter import font as tkfont
import threading

from engine.pieces import Piece, PieceType, Faction, PIECE_NAMES
from engine.board  import Board, Move
from ai.minimax    import AIEngine


BG        = "#f4f3ef"
BG2       = "#e6e4dd"

SQ_LIGHT  = "#eee4da"
SQ_DARK   = "#b7a58a"

SQ_SEL    = "#c9d36a"
SQ_MOVE   = "#a8c96b"
SQ_CAP    = "#d46a6a"
SQ_SWAP   = "#6aa8d4"

FG        = "#2b2b2b"
FG2       = "#6b6b6b"

OL_COLOR  = "#2f3e9e"
UW_COLOR  = "#7a2f2f"

BTN_BG    = "#dcdad2"
BTN_ACT   = "#c6c3bb"

SYMS = {
    Faction.OLYMPUS: {
        PieceType.ZEUS:       "⚡︎",
        PieceType.ATHENA:     "𖦹",
        PieceType.HERMES:     "Η",
        PieceType.ARES:       "Α̈",
        PieceType.ARTEMIS:    "↟",
        PieceType.HEPHAESTUS: "♯",
        PieceType.APOLLO:     "✮",
        PieceType.SOLDIER:    "◆",
    },
    Faction.UNDERWORLD: {
        PieceType.ZEUS:       "⚡︎",
        PieceType.ATHENA:     "𖦹",
        PieceType.HERMES:     "H",
        PieceType.ARES:       "A",
        PieceType.ARTEMIS:    "↟",
        PieceType.HEPHAESTUS: "♯",
        PieceType.APOLLO:     "✮",
        PieceType.SOLDIER:    "◇",
    },
}

PIECE_ABILITY = {
    PieceType.ZEUS:       "⚡︎: Moves 1 sq any direction. Cannot enter threatened squares.",
    PieceType.ATHENA:     "𖦹: Jumps (+-3,+-1) or (+-1,+-3). Cannot be blocked.",
    PieceType.HERMES:     "Η: Up to 3 squares straight. Blocked by pieces.",
    PieceType.ARES:       "A: Must capture enemies within radius 2. Else moves up to 2.",
    PieceType.ARTEMIS:    "↟: Move 1 diagonal OR capture 2 diagonal (stays in place).",
    PieceType.HEPHAESTUS: "♯: Immovable. 3 HP. Buffs adjacent friendlies +1 range.",
    PieceType.APOLLO:     "✮: Move 1 any dir OR swap with any friendly (not Zeus). 2-turn cooldown.",
    PieceType.SOLDIER:    "◇: Forward 1, capture diagonal. Promotes on last row.",
}

CELL      = 72
BOARD_PAD = 20
BOARD_SZ  = CELL * 8 + BOARD_PAD * 2
PANEL_W   = 220
WIN_W     = BOARD_SZ + PANEL_W + 4
WIN_H     = BOARD_SZ + 28


def sq_to_xy(row, col):
    # converts board row and column to the top left pixel of that cell on the canvas
    return BOARD_PAD + col * CELL, BOARD_PAD + row * CELL


def xy_to_sq(x, y):
    # converts canvas pixel coordinates to a board row and column or none if outside grid
    col = (x - BOARD_PAD) // CELL
    row = (y - BOARD_PAD) // CELL
    if 0 <= row < 8 and 0 <= col < 8:
        return row, col
    return None


class PromotionDialog(tk.Toplevel):
    def __init__(self, parent, faction):
        # creates a modal dialog asking the player to choose a promotion piece
        super().__init__(parent)
        self.result = None
        self.title("Promotion")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        names   = PIECE_NAMES[faction]
        options = [PieceType.HERMES, PieceType.ARTEMIS, PieceType.ARES]

        tk.Label(self, text="Choose promotion piece",
            bg=BG, fg=FG, font=("Courier New", 12, "bold")).pack(pady=(16, 8))

        for pt in options:
            tk.Button(
                self,
                text=f"{names[pt]}",
                bg=BTN_BG, fg=FG,
                activebackground=BTN_ACT,
                relief="groove", bd=1,
                font=("Courier New", 11),
                padx=12, pady=6,
                command=lambda p=pt: self._pick(p),
            ).pack(fill="x", padx=24, pady=3)

        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{pw - 120}+{ph - 80}")

    def _pick(self, pt):
        # stores the chosen piece type and closes the dialog
        self.result = pt
        self.destroy()


class GodfallApp:
    def __init__(self, root: tk.Tk):
        # initialises the application sets up game state variables and shows the start screen
        self.root        = root
        self.root.title("GODFALL")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.board       = None
        self.selected    = None
        self.valid_moves = []
        self.is_swap     = False
        self.ai_engine   = None
        self.ai_faction  = None
        self.mode        = None
        self.ai_thinking = False
        self.game_active = False

        self.font_title  = tkfont.Font(family="Courier New", size=22, weight="bold")
        self.font_normal = tkfont.Font(family="Courier New", size=11)
        self.font_small  = tkfont.Font(family="Courier New", size=9)
        self.font_piece  = tkfont.Font(family="Segoe UI Symbol", size=18, weight="bold")
        self.font_btn    = tkfont.Font(family="Courier New", size=12)

        self._build_menu()

    def _clear(self):
        # destroys all widgets currently in the root window
        for w in self.root.winfo_children():
            w.destroy()

    def _build_menu(self):
        # builds the minimal start screen with two mode buttons
        self._clear()
        self.root.geometry("340x220")

        frame = tk.Frame(self.root, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="GODFALL", bg=BG, fg=FG,
                font=self.font_title).pack(pady=(0, 18))

        tk.Button(frame, text="Human vs AI",
                bg=BTN_BG, fg=FG,
                activebackground=BTN_ACT,
                relief="groove", bd=1,
                font=self.font_btn,
                padx=16, pady=8, width=20,
                command=lambda: self._start("hvai")).pack(pady=5)

        tk.Button(frame, text="Human vs Human",
                bg=BTN_BG, fg=FG,
                activebackground=BTN_ACT,
                relief="groove", bd=1,
                font=self.font_btn,
                padx=16, pady=8, width=20,
                command=lambda: self._start("hvh")).pack(pady=5)

    def _start(self, mode):
        # initialises a new game in the chosen mode and builds the game screen
        self._clear()
        self.root.geometry(f"{WIN_W}x{WIN_H}")

        self.board       = Board()
        self.selected    = None
        self.valid_moves = []
        self.game_active = True
        self.mode        = mode

        if mode == "hvai":
            self.ai_faction = Faction.UNDERWORLD
            self.ai_engine  = AIEngine(Faction.UNDERWORLD, depth=3)
        else:
            self.ai_faction = None
            self.ai_engine  = None

        self._build_game_ui()
        self._draw_board()
        self._update_panel()

    def _build_game_ui(self):
        # creates the canvas for the board and the side panel frame
        self.canvas = tk.Canvas(
            self.root, width=BOARD_SZ, height=BOARD_SZ,
            bg=SQ_LIGHT, highlightthickness=1, highlightbackground="#999"
        )
        self.canvas.place(x=0, y=0)
        self.canvas.bind("<Button-1>", self._on_click)

        self.panel = tk.Frame(self.root, bg=BG2, width=PANEL_W, height=WIN_H)
        self.panel.place(x=BOARD_SZ + 4, y=0)
        self.panel.pack_propagate(False)

        self._build_panel()

        self.statusbar = tk.Label(
            self.root, text="", bg=BG, fg=FG2,
            font=self.font_small, anchor="w", padx=6
        )
        self.statusbar.place(x=0, y=BOARD_SZ, width=BOARD_SZ, height=28)

    def _build_panel(self):
        # populates the right side panel with turn label piece info log and buttons
        p = self.panel

        self.lbl_turn = tk.Label(p, text="", bg=BG2, fg=FG,
            font=("Courier New", 11, "bold"))
        self.lbl_turn.pack(pady=(14, 2))

        self.lbl_move = tk.Label(p, text="Move 1", bg=BG2, fg=FG2,
            font=self.font_small)
        self.lbl_move.pack()

        tk.Frame(p, bg="#aaa", height=1).pack(fill="x", padx=10, pady=8)

        tk.Label(p, text="Selected", bg=BG2, fg=FG2,
            font=self.font_small).pack(anchor="w", padx=10)

        self.lbl_piece = tk.Label(p, text="—", bg=BG2, fg=FG,
            font=("Courier New", 10, "bold"), wraplength=190,
            justify="left")
        self.lbl_piece.pack(anchor="w", padx=10, pady=2)

        self.lbl_ability = tk.Label(p, text="", bg=BG2, fg=FG2,
                                    font=self.font_small, wraplength=195,
                                    justify="left")
        self.lbl_ability.pack(anchor="w", padx=10)

        tk.Frame(p, bg="#aaa", height=1).pack(fill="x", padx=10, pady=8)

        tk.Label(p, text="Move Log", bg=BG2, fg=FG2,
                font=self.font_small).pack(anchor="w", padx=10)

        self.log_text = tk.Text(
            p, height=16, width=24,
            bg=BG, fg=FG,
            font=self.font_small, relief="flat", bd=0,
            state="disabled", cursor="arrow", wrap="word"
        )
        self.log_text.pack(fill="x", padx=8, pady=4)

        tk.Frame(p, bg="#aaa", height=1).pack(fill="x", padx=10, pady=8)

        tk.Button(p, text="New Game",
                  bg=BTN_BG, fg=FG,
                  activebackground=BTN_ACT,
                  relief="groove", bd=1,
                  font=self.font_small,
                  padx=8, pady=4,
                  command=self._build_menu).pack(fill="x", padx=10, pady=2)

        tk.Button(p, text="Legend",
                  bg=BTN_BG, fg=FG,
                  activebackground=BTN_ACT,
                  relief="groove", bd=1,
                  font=self.font_small,
                  padx=8, pady=4,
                  command=self._show_legend).pack(fill="x", padx=10, pady=2)

    def _draw_board(self):
        # redraws the entire board canvas including squares highlights and pieces
        cv = self.canvas
        cv.delete("all")
        valid_set = set(self.valid_moves)

        for r in range(8):
            for c in range(8):
                x, y    = sq_to_xy(r, c)
                is_light = (r + c) % 2 == 0
                piece    = self.board.grid[r][c]

                if self.selected == (r, c):
                    fill = SQ_SEL
                elif (r, c) in valid_set:
                    fill = SQ_CAP if (piece and piece.faction != self.board.turn) else (SQ_SWAP if self.is_swap else SQ_MOVE)
                else:
                    fill = SQ_LIGHT if is_light else SQ_DARK

                cv.create_rectangle(x, y, x+CELL, y+CELL, fill=fill, outline="#888", width=0.5)

                if c == 0:
                    cv.create_text(x+4, y+4, text=str(8-r), fill="#555",
                                   font=self.font_small, anchor="nw")
                if r == 7:
                    cv.create_text(x+CELL-4, y+CELL-4, text="abcdefgh"[c],
                                   fill="#555", font=self.font_small, anchor="se")

                if (r, c) in valid_set and piece is None:
                    cx2, cy2 = x + CELL//2, y + CELL//2
                    d = 6
                    cv.create_oval(cx2-d, cy2-d, cx2+d, cy2+d, fill="#777", outline="")

                if piece:
                    self._draw_piece(cv, piece, r, c)

    def _draw_piece(self, cv, piece, row, col):
        # draws a single piece symbol on the board at the given row and column
        x, y  = sq_to_xy(row, col)
        cx    = x + CELL // 2
        cy    = y + CELL // 2
        color = OL_COLOR if piece.faction == Faction.OLYMPUS else UW_COLOR
        sym   = SYMS[piece.faction].get(piece.piece_type, "?")

        cv.create_text(cx, cy, text=sym, fill=color, font=self.font_piece)

        if piece.piece_type == PieceType.HEPHAESTUS:
            cv.create_text(x+CELL-4, y+4, text=str(piece.hp),
                           fill=color, font=self.font_small, anchor="ne")

        if piece.piece_type == PieceType.APOLLO and piece.swap_cooldown > 0:
            cv.create_text(x+4, y+4, text=str(piece.swap_cooldown),
                           fill="#c00", font=self.font_small, anchor="nw")

    def _update_panel(self):
        # refreshes all labels in the side panel to reflect current board state
        b     = self.board
        is_ol = b.turn == Faction.OLYMPUS
        name  = "Olympus" if is_ol else "Underworld"
        color = OL_COLOR  if is_ol else UW_COLOR

        self.lbl_turn.config(text=f"{name}'s turn", fg=color)
        self.lbl_move.config(text=f"Move {len(b.move_history) + 1}")

        if self.selected:
            r, c  = self.selected
            piece = b.grid[r][c]
            if piece:
                self.lbl_piece.config(text=piece.name, fg=color)
                self.lbl_ability.config(text=PIECE_ABILITY[piece.piece_type])
        else:
            self.lbl_piece.config(text="—", fg=FG)
            self.lbl_ability.config(text="Click a piece to select")

    def _log(self, msg):
        # appends a message to the move log text widget
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _set_status(self, msg):
        # updates the status bar text at the bottom of the board
        self.statusbar.config(text=msg)

    def _on_click(self, event):
        # handles mouse clicks on the board canvas routing to select or move logic
        if not self.game_active or self.ai_thinking:
            return
        if self.mode == "hvai" and self.board.turn == self.ai_faction:
            return

        sq = xy_to_sq(event.x, event.y)
        if sq is None:
            return

        r, c = sq
        if self.selected is None:
            self._try_select(r, c)
        else:
            self._try_move(r, c)

    def _try_select(self, r, c):
        # tries to select the piece at the given square and highlights its legal moves
        b     = self.board
        piece = b.grid[r][c]

        if piece is None:
            self._set_status("No piece there")
            return
        if piece.faction != b.turn:
            self._set_status("That is an enemy piece")
            return
        if piece.piece_type == PieceType.HEPHAESTUS:
            self._set_status(f"{piece.name} cannot move")
            return

        all_moves = b.get_all_legal_moves(b.turn) + b.get_hephaestus_attack_moves(b.turn)

        dests      = []
        swap_dests = []
        for m in all_moves:
            if m.from_row == r and m.from_col == c:
                dests.append((m.to_row, m.to_col))
                if m.move_type == "swap":
                    swap_dests.append((m.to_row, m.to_col))

        dests = list(set(dests))

        if not dests:
            self._set_status(f"{piece.name} has no legal moves")
            return

        self.selected    = (r, c)
        self.valid_moves = dests
        self.is_swap     = bool(swap_dests) and len(swap_dests) == len(dests)
        self._draw_board()
        self._update_panel()
        self._set_status(f"{piece.name} selected  {len(dests)} moves available")

    def _try_move(self, r, c):
        # tries to execute a move to the clicked square or reselects if clicking another piece
        sel_r, sel_c = self.selected
        b = self.board

        if (r, c) == (sel_r, sel_c):
            self.selected    = None
            self.valid_moves = []
            self._draw_board()
            self._update_panel()
            self._set_status("")
            return

        all_moves = b.get_all_legal_moves(b.turn) + b.get_hephaestus_attack_moves(b.turn)

        move = None
        for m in all_moves:
            if (m.from_row == sel_r and m.from_col == sel_c
                    and m.to_row == r and m.to_col == c):
                move = m
                break

        if move is None:
            piece = b.grid[r][c]
            if piece and piece.faction == b.turn:
                self.selected    = None
                self.valid_moves = []
                self._try_select(r, c)
            else:
                self._set_status("Invalid move")
            return

        promo = None
        if move.piece.piece_type == PieceType.SOLDIER and move.move_type != "swap":
            last = 7 if move.piece.faction == Faction.OLYMPUS else 0
            if move.to_row == last:
                dlg   = PromotionDialog(self.root, move.piece.faction)
                self.root.wait_window(dlg)
                promo = dlg.result or PieceType.HERMES

        self._execute_move(move, promo)

    def _execute_move(self, move, promo=None):
        # applies the move to the board updates the ui and triggers the ai if needed
        b      = self.board
        result = b.apply_move(move, promotion_choice=promo)
        msg    = self._describe(move, result)
        self._log(msg)

        self.selected    = None
        self.valid_moves = []
        self._draw_board()
        self._update_panel()

        if result == "godfall":
            self._show_end(b.winner)
            return
        if result == "draw":
            self._show_draw()
            return

        self._set_status(msg)

        if self.mode == "hvai" and b.turn == self.ai_faction and self.game_active:
            self.root.after(200, self._trigger_ai)

    def _describe(self, move, result):
        # returns a short human readable string describing what a move did
        p  = move.piece
        to = f"{'abcdefgh'[move.to_col]}{8 - move.to_row}"
        if move.move_type == "swap":
            other = move.swap_target
            return f"{p.name} swaps with {other.name if other else '?'}"
        if move.move_type == "artemis_capture":
            cap = move.captured_piece
            return f"{p.name} strikes {cap.name if cap else '?'} at {to}"
        if move.move_type == "heph_attack":
            cap = move.captured_piece
            if result == "heph_hit":
                return f"{p.name} hits {cap.name if cap else '?'} ({cap.hp}HP left)"
            return f"{p.name} destroys {cap.name if cap else '?'}"
        if result == "capture":
            cap = move.captured_piece
            return f"{p.name} captures {cap.name if cap else '?'} at {to}"
        if result == "godfall":
            return f"GODFALL  {p.name} takes the king"
        if result == "promotion":
            return f"{p.name} promotes at {to}"
        fr = f"{'abcdefgh'[move.from_col]}{8 - move.from_row}"
        return f"{p.name} {fr} to {to}"

    def _trigger_ai(self):
        # starts the ai thinking in a background thread to avoid freezing the ui
        if not self.game_active:
            return
        self.ai_thinking = True
        self._set_status("AI is thinking...")
        self.root.update()

        def worker():
            move = self.ai_engine.get_best_move(self.board)
            self.root.after(0, lambda: self._ai_done(move))

        threading.Thread(target=worker, daemon=True).start()

    def _ai_done(self, move):
        # receives the ai chosen move and executes it on the board
        self.ai_thinking = False
        if move is None:
            self._show_draw()
            return
        self._execute_move(move, promo=PieceType.ARES)

    def _show_end(self, winner):
        # shows a game over overlay with the winning faction name and a play again button
        self.game_active = False
        is_ol  = winner == Faction.OLYMPUS
        name   = "Olympus" if is_ol else "Underworld"
        color  = OL_COLOR  if is_ol else UW_COLOR

        ov = tk.Frame(self.root, bg=BG)
        ov.place(x=0, y=0, width=BOARD_SZ, height=BOARD_SZ)

        tk.Label(ov, text="GODFALL", bg=BG, fg=color,
            font=("Courier New", 28, "bold")).place(relx=0.5, rely=0.38, anchor="center")

        tk.Label(ov, text=f"{name} wins", bg=BG, fg=FG,
            font=("Courier New", 14)).place(relx=0.5, rely=0.50, anchor="center")

        tk.Label(ov, text=f"{len(self.board.move_history)} moves", bg=BG, fg=FG2,
            font=self.font_small).place(relx=0.5, rely=0.58, anchor="center")

        tk.Button(ov, text="Play Again",
            bg=BTN_BG, fg=FG,
            activebackground=BTN_ACT,
            relief="groove", bd=1,
            font=self.font_btn,
            padx=14, pady=8,
            command=self._build_menu).place(relx=0.5, rely=0.70, anchor="center")

    def _show_draw(self):
        # shows a draw overlay with a play again button
        self.game_active = False

        ov = tk.Frame(self.root, bg=BG)
        ov.place(x=0, y=0, width=BOARD_SZ, height=BOARD_SZ)

        tk.Label(ov, text="DRAW", bg=BG, fg=FG,
                 font=("Courier New", 28, "bold")).place(relx=0.5, rely=0.38, anchor="center")

        tk.Label(ov, text="No legal moves", bg=BG, fg=FG2,
                 font=("Courier New", 12)).place(relx=0.5, rely=0.50, anchor="center")

        tk.Button(ov, text="Play Again",
                  bg=BTN_BG, fg=FG,
                  activebackground=BTN_ACT,
                  relief="groove", bd=1,
                  font=self.font_btn,
                  padx=14, pady=8,
                  command=self._build_menu).place(relx=0.5, rely=0.62, anchor="center")

    def _show_legend(self):
        # opens a popup window listing all piece names and their movement abilities
        win = tk.Toplevel(self.root)
        win.title("Piece Legend")
        win.configure(bg=BG)
        win.resizable(False, False)

        tk.Label(win, text="Piece Legend", bg=BG, fg=FG,
                 font=("Courier New", 12, "bold")).pack(pady=(12, 6))

        pairs = [
            ("Zeus",           PieceType.ZEUS),
            ("Athena",        PieceType.ATHENA),
            ("Hermes",        PieceType.HERMES),
            ("Ares",       PieceType.ARES),
            ("Artemis",          PieceType.ARTEMIS),
            ("Hephaestus",  PieceType.HEPHAESTUS),
            ("Apollo",      PieceType.APOLLO),
            ("Soldier",        PieceType.SOLDIER),
        ]

        for label, pt in pairs:
            row = tk.Frame(win, bg=BG2)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=label, bg=BG2, fg=FG,
                     font=("Courier New", 9, "bold"),
                     width=22, anchor="w").pack(side="left", padx=6, pady=4)
            tk.Label(row, text=PIECE_ABILITY[pt], bg=BG2, fg=FG2,
                     font=("Courier New", 8),
                     wraplength=280, justify="left").pack(side="left", padx=4)

        tk.Button(win, text="Close", bg=BTN_BG, fg=FG,
                  relief="groove", bd=1, font=self.font_small,
                  padx=10, pady=4, command=win.destroy).pack(pady=10)

        win.update_idletasks()
        px = self.root.winfo_rootx() + self.root.winfo_width()  // 2
        py = self.root.winfo_rooty() + self.root.winfo_height() // 2
        w, h = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{px - w//2}+{py - h//2}")


def launch():
    # creates the root tkinter window and starts the application main loop
    root = tk.Tk()
    root.title("GODFALL")
    GodfallApp(root)
    root.mainloop()
