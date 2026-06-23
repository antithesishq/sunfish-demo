"""Workload for the `fifty-move-draw` property.

Property (see ../scratchbook/properties/fifty-move-draw.md):
    If 50 consecutive moves (100 plies) occur without a capture taking place
    or a pawn being moved, the game ends in a draw.

This workload plays full, randomized games from the standard
starting position:

  - python-chess is the rules oracle: it enumerates legal moves, tracks the
    halfmove clock, and decides when the game is over.
  - Each ply, a random legal move is chosen. The random
    choice goes through the Antithesis SDK so it becomes a decision point the
    platform can explore.
  - Play continues until the game ends by the rules, or until the oracle reports
    a fifty-move position. At that point the `Always` assertion checks whether
    the engine treats the position as a draw.
"""

import os
import subprocess
import sys

import chess

from antithesis.assertions import always 
from antithesis.lifecycle import setup_complete
from antithesis.random import random_choice

# -----------------------------------------------------------------------------

REPO_ROOT = os.path.abspath("/sunfish")

# Standard chess starting position.
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Engine search depth per move. Small and bounded so the game runs quickly and
# deterministically; the property does not depend on engine strength.
GO_DEPTH = 3

# How much to favor moves that advance the half-move clock.
CLOCK_ADVANCE_WEIGHT = 1

# When enabled, print the current board FEN at the top of each move loop
# iteration. Handy for watching the game / the halfmove clock climb; off by
# default to keep output clean.
#
# The default comes from the PRINT_FEN env var (baked into the image), but it
# can be toggled live by writing a flag file — useful from the Multiverse
# Debugger's bash shell, where the running process's environment can't be
# changed:
#   echo 1 > /tmp/print_fen   # enable from the next ply onward
#   echo 0 > /tmp/print_fen   # (or rm the file) back to the env default
PRINT_FEN_DEFAULT = os.environ.get("PRINT_FEN", "").lower() not in ("", "0", "false")
PRINT_FEN_FILE = os.environ.get("PRINT_FEN_FILE", "/tmp/print_fen")


def print_fen_enabled():
    """Re-evaluated each loop so the flag file can toggle FEN logging live."""
    if not os.path.exists(PRINT_FEN_FILE):
        return PRINT_FEN_DEFAULT
    try:
        with open(PRINT_FEN_FILE) as f:
            return f.read().strip().lower() not in ("", "0", "false")
    except OSError:
        return PRINT_FEN_DEFAULT


class Engine:
    """A thin UCI driver around a Sunfish subprocess."""

    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "sunfish.py"],
            cwd=REPO_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            env={**os.environ, "NO_COLOR": "1", "PYTHONUNBUFFERED": "1"},
        )

    def _send(self, line):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def _read_until(self, token):
        """Read stdout lines until one starts with `token`; return that line."""
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("engine closed stdout unexpectedly")
            line = line.strip()
            if line.split(" ", 1)[0] == token:
                return line

    def handshake(self):
        self._send("uci")
        self._read_until("uciok")
        self._send("isready")
        self._read_until("readyok")

    def bestmove(self, fen, moves):
        """Ask the engine for the best move in `fen` after `moves` (UCI strings).

        Returns the bestmove string, which is "(none)" when the engine reports
        no move / treats the game as over.
        """
        pos = f"position fen {fen}"
        if moves:
            pos += " moves " + " ".join(moves)
        self._send(pos)
        self._send(f"go depth {GO_DEPTH}")
        line = self._read_until("bestmove")
        return line.split()[1]

    def quit(self):
        try:
            self._send("quit")
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def advances_halfmove_clock(board, move):
    # The fifty-move clock advances on any move that is neither a capture
    # (en passant counts) nor a pawn move. Castling advances it; promotion
    # is a pawn move, so it resets.
    if board.is_capture(move):
        return False
    if board.piece_type_at(move.from_square) == chess.PAWN:
        return False
    return True


def main():
    engine = Engine()
    engine.handshake()
    print("[workload]: sunfish is ready")
    setup_complete({"Message": "sunfish is ready"})

    board = chess.Board(START_FEN)
    moves = []  # UCI move strings, replayed via `position fen <start> moves ...`

    try:
        while True:
            if print_fen_enabled():
                print(board.fen(), flush=True)

            legal = list(board.legal_moves)
            if not legal:
                print(f"[workload] no legal moves at ply {len(moves)}: "
                      f"{board.result()} ({board.fen()})", flush=True)
                probe = engine.bestmove(START_FEN, moves)
                always(
                    probe == "(none)",
                    "game ends when there are no legal moves",
                    {"plies": len(moves), "halfmove_clock": board.halfmove_clock,
                     "fen": board.fen(), "engine_response": probe},
                )
                break

            pool = []
            for m in legal:
                pool += [m] * (CLOCK_ADVANCE_WEIGHT if advances_halfmove_clock(board, m) else 1)
            move = random_choice(pool)
            board.push(move)
            moves.append(move.uci())
            
            if board.is_fifty_moves():
                print(f"[workload] 50-move draw at ply {len(moves)}: "
                      f"{board.result()} ({board.fen()})",
                      f"halfmove_clock {board.halfmove_clock}", flush=True)
                probe = engine.bestmove(START_FEN, moves)
                if probe != "(none)":
                    print(f"[workload] sunfish failed to detect 50-move draw {probe}")
                always(
                    probe == "(none)",
                    "game drawn after 50 moves with no capture or pawn move",
                    {"plies": len(moves), "halfmove_clock": board.halfmove_clock,
                     "fen": board.fen(), "engine_response": probe},
                )
                break

            if board.is_game_over():
                print(f"[workload] game over at ply {len(moves)}: "
                      f"{board.result()} ({board.fen()})", flush=True)
                break
    finally:
        engine.quit()


if __name__ == "__main__":
    print(f"[workload] clock_advance_weight: {CLOCK_ADVANCE_WEIGHT}")
    game = 1
    while True:
        print(f"[workload] starting game {game}")
        main()
