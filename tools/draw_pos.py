#!/usr/bin/env python3
"""Turn FEN positions into an animated GIF.

Self-contained: relies only on Python packages (python-chess for FEN parsing,
Pillow for rasterization). It deliberately avoids cairosvg/cairocffi, which
dlopen the system `libcairo.so.2` shared library at runtime -- an external
native dependency that is awkward to guarantee inside minimal containers such
as the Antithesis test environment. The board is drawn directly with Pillow's
ImageDraw instead of rendering SVG.
"""
import argparse
import os
import chess
from PIL import Image, ImageDraw, ImageFont

LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
WHITE_PIECE = (250, 250, 250)
BLACK_PIECE = (38, 36, 33)
WHITE_OUTLINE = (30, 30, 30)
BLACK_OUTLINE = (210, 210, 210)

# DejaVu Sans is vendored beside this script so the tool has no system-font or
# native-library dependency (works identically locally and in the container).
# Resolve relative to __file__ rather than the CWD so it loads no matter where
# the script is invoked from.
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "assets", "DejaVuSans.ttf")

# The solid ("black") chess glyphs U+265A-265F are filled shapes; we render them
# for both colors and tint white/black, giving each a contrasting outline. Keyed
# by python-chess piece symbol (uppercase = white, lowercase = black).
PIECE_GLYPHS = {
    "K": "♚", "Q": "♛", "R": "♜",
    "B": "♝", "N": "♞", "P": "♟",
}

def fen_to_image(fen, size=400):
    board = chess.Board(fen)
    square = size // 8
    size = square * 8  # snap to a whole number of squares
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, int(square * 0.82))

    for rank in range(8):
        for file in range(8):
            x0, y0 = file * square, rank * square
            is_light = (rank + file) % 2 == 0
            draw.rectangle(
                [x0, y0, x0 + square, y0 + square],
                fill=LIGHT_SQUARE if is_light else DARK_SQUARE,
            )
            # chess.Square counts ranks from the bottom (rank 8 at the top).
            piece = board.piece_at(chess.square(file, 7 - rank))
            if piece is None:
                continue
            cx, cy = x0 + square / 2, y0 + square / 2
            glyph = PIECE_GLYPHS[piece.symbol().upper()]
            if piece.color == chess.WHITE:
                fill, outline = WHITE_PIECE, WHITE_OUTLINE
            else:
                fill, outline = BLACK_PIECE, BLACK_OUTLINE
            draw.text((cx, cy), glyph, fill=fill, font=font, anchor="mm",
                      stroke_width=max(1, square // 32), stroke_fill=outline)
    return img

def make_gif(fens, output_path, size, duration, loop):
    frames = [fen_to_image(fen, size) for fen in fens]
    frames[0].save(
        output_path, save_all=True, append_images=frames[1:],
        duration=duration, loop=loop,
    )
    print(f"Saved {len(frames)} frames to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Turn FEN positions into an animated GIF.")
    parser.add_argument("fens", nargs="+", help="List of FEN strings")
    parser.add_argument("-o", "--output", default="output.gif")
    parser.add_argument("-s", "--size", type=int, default=400)
    parser.add_argument("-d", "--duration", type=int, default=800, help="ms per frame")
    parser.add_argument("-l", "--loop", type=int, default=0)
    args = parser.parse_args()

    make_gif(args.fens, args.output, args.size, args.duration, args.loop)
