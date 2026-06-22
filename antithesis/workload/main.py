"""Workload for the `fifty-move-draw` property.

Property (see ../scratchbook/properties/fifty-move-draw.md):
    If 50 consecutive moves (100 plies) occur without a capture taking place
    or a pawn being moved, the game ends in a draw.

The workload drives Sunfish (over UCI, as a subprocess) from a sparse,
captureless endgame and lets the engine play both sides. It tracks the halfmove
clock with `python-chess` as the rules oracle. Once the oracle reports a
fifty-move position (100 plies with no capture or pawn move), it checks whether
the engine treats that position as a draw and fires the `Sometimes` assertion.
Because Sunfish has no such logic, the assertion's condition never becomes true,
exposing the missing rule.
"""

import os
import subprocess
import sys

import chess

try:
    from antithesis.assertions import always, reachable, sometimes
except ImportError:  # pragma: no cover - shim for pre-setup local runs
    def _shim(name):
        def _fn(message, condition=True, details=None):
            status = "PASS" if condition else "fail"
            print(f"[antithesis:{name}:{status}] {message} {details or {}}",
                  flush=True)
        return _fn

    always = _shim("always")
    sometimes = _shim("sometimes")

    def reachable(message, details=None):  # signature differs from always/sometimes
        print(f"[antithesis:reachable] {message} {details or {}}", flush=True)

# -----------------------------------------------------------------------------

REPO_ROOT = os.path.abspath("/sunfish")

# A sparse endgame: two white knights and both kings, no pawns, no castling.
# Knights and kings can shuffle indefinitely without any capture or pawn move,
# so the halfmove clock climbs straight to the fifty-move threshold. python-chess
# does not flag king + two knights vs king as insufficient material, so
# is_fifty_moves() is the operative termination signal.
START_FEN = "4k3/8/8/8/8/8/8/N3K2N w - - 0 1"

# Engine search depth per move. Small and bounded so the game runs quickly and
# deterministically; the property does not depend on engine strength.
GO_DEPTH = 3

# Play well past the 100-ply (fifty full-move) threshold to give the engine
# repeated opportunities to declare the draw.
MAX_PLIES = 140


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


def main():
    engine = Engine()
    engine.handshake()

    board = chess.Board(START_FEN)
    moves = []  # UCI move strings, fed back via `position ... moves ...`
    fired_at_fifty = False

    try:
        for _ply in range(MAX_PLIES):
            mv = engine.bestmove(START_FEN, moves)

            if mv == "(none)":
                # Engine reports no move available. At a fifty-move position this
                # would count as treating the game as over; otherwise it is a
                # stalemate/terminal in this sparse endgame.
                sometimes(
                    "game drawn after 50 moves with no capture or pawn move",
                    board.is_fifty_moves(),
                    {"plies": len(moves), "halfmove_clock": board.halfmove_clock,
                     "fen": board.fen(), "signal": "bestmove (none)"},
                )
                break

            try:
                move = chess.Move.from_uci(mv)
            except ValueError:
                always("engine emits a parseable UCI move", False, {"move": mv})
                break

            if move not in board.legal_moves:
                # Sunfish is a king-capture engine and does not fully enforce
                # check; if it ever returns a move the oracle rejects, stop and
                # record it rather than desync the oracle.
                always("engine move is legal per the rules oracle", False,
                       {"move": mv, "fen": board.fen(), "plies": len(moves)})
                break

            board.push(move)
            moves.append(mv)

            if board.is_fifty_moves():
                reachable(
                    "reached a fifty-move position (100 plies, no capture/pawn move)",
                    {"plies": len(moves), "halfmove_clock": board.halfmove_clock,
                     "fen": board.fen()},
                )
                # The engine should now treat this position as a draw. We probe
                # it: a draw-aware engine returns no move ("(none)") because the
                # game is over. Sunfish instead keeps returning a winning move,
                # so this condition stays false and the bug is exposed.
                probe = engine.bestmove(START_FEN, moves)
                engine_declares_draw = probe == "(none)"
                sometimes(
                    "game drawn after 50 moves with no capture or pawn move",
                    engine_declares_draw,
                    {"plies": len(moves), "halfmove_clock": board.halfmove_clock,
                     "fen": board.fen(), "engine_response": probe},
                )
                fired_at_fifty = True
                break

        if not fired_at_fifty:
            # We never reached the fifty-move threshold within MAX_PLIES; record
            # that the meaningful state was not observed this run.
            print(f"[workload] did not reach fifty-move threshold in {len(moves)} "
                  f"plies (halfmove_clock={board.halfmove_clock})", flush=True)
    finally:
        engine.quit()


if __name__ == "__main__":
    main()
