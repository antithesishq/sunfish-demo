#!/usr/bin/env python3
import sys
import chess

def main():
    if len(sys.argv) < 2:
        print("usage: fen.py <fen string>", file=sys.stderr)
        sys.exit(1)

    fen = " ".join(sys.argv[1:])
    try:
        board = chess.Board(fen)
    except ValueError as e:
        print(f"invalid fen: {e}", file=sys.stderr)
        sys.exit(1)

    print(board.unicode(invert_color=True, borders=True))
    print()
    print(f"  turn:           {'white' if board.turn else 'black'}")
    print(f"  halfmove clock: {board.halfmove_clock}")
    print(f"  fullmove:       {board.fullmove_number}")
    print(f"  fifty moves:    {board.is_fifty_moves()}")

if __name__ == "__main__":
    main()