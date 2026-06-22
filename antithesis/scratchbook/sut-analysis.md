---
sut_path: /home/avpai/src/sunfish-demo
commit: d41cc1a39324b1789f49c0cd3daa0c47e887afb0
updated: 2026-06-22
external_references:
  - path: http://wbec-ridderkerk.nl/html/UCIProtocol.html
    why: UCI protocol spec — the command/response contract used to drive games into the engine.
---

# SUT Analysis — Sunfish (core engine)

## Scope

Testing target: the **fifty-move-draw** property — *if 50 consecutive moves (100
plies) pass with no capture and no pawn move, the game is a draw* (see
`properties/fifty-move-draw.md`). This analysis covers only what's needed to
exercise and judge that one rule. The NNUE variant (`sunfish_nnue.py`, `nnue/`)
is out of scope.

## What Sunfish is

A small chess engine in pure Python. It speaks the
[UCI protocol](http://wbec-ridderkerk.nl/html/UCIProtocol.html) over
stdin/stdout: `position startpos moves ...` sets up a game line, `go ...` makes
the engine search and print a `bestmove`. Single process, no persistence, no
network. `sunfish.py` runs via `tools/uci.py:run` (the real UCI loop);
`python-chess` (`chess==1.9.4`, already in `requirements.txt`) is available as a
rules oracle and is the natural way to score the draw.

## The key finding for this property: Sunfish does not implement the fifty-move rule

The engine has **no fifty-move tracking at all**:

- A position is `Position(namedtuple("Position", "board score wc bc ep kp"))`
  (`sunfish.py:143`). There is **no halfmove-clock field** and no
  captureless/pawn-move counter anywhere in `Position` or `Searcher`. The state
  needed to apply the rule simply isn't carried.
- The only draw detection in the engine is **repetition**: in `Searcher.bound`,
  `if can_null and depth > 0 and pos in self.history: return 0` (`sunfish.py:303`),
  where `history` is a `set` of positions (`sunfish.py:271`, `:411`). Nothing else
  returns a draw score for a non-repeated position.
- When a FEN is loaded, `tools/uci.py:from_fen(board, color, castling, enpas,
  _hclock, _fclock)` (`:278`) parses the halfmove-clock field but **discards it**
  (the `_hclock` parameter is unused) — so even the standard input that conveys
  fifty-move state is ignored.

**Consequence for testing:** Sunfish will keep playing a captureless,
pawn-moveless position indefinitely; it never declares or scores a fifty-move
draw. **This property is a bug report against Sunfish** — the engine should honor
the fifty-move rule but does not, so the property fails by design. The workload
counts plies-since-capture/pawn-move (using `python-chess`
`Board.is_fifty_moves()` / `can_claim_fifty_moves()` as the oracle), drives the
game past 100 such plies, and asserts the engine treats the position as a draw;
because no such logic exists in the engine, that assertion exposes the missing
rule.

## How to drive it

To reach a captureless, pawn-moveless run, the workload alternates engine moves
(via `position startpos moves ...` + `go`) and/or scripted moves, tracking the
halfmove clock itself with python-chess. Pure-shuffle positions (e.g. kings and
a couple of pieces with no pawns) reach 100 captureless plies quickly. The engine
output to watch is the `bestmove` line; the draw determination happens in the
workload/oracle, since the engine emits no draw signal of its own.

## Assumptions

- SUT under test is the **source** path driven by `tools/uci.py` (not the
  minified single-file build).
- Chess-rule correctness, including the fifty-move clock, is judged by
  `python-chess`, matching how `tools/tester.py` already uses it.
