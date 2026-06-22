# fifty-move-draw — Fifty moves without a capture ends in a draw

**Type** 
Liveness

**Property**
If 50 consecutive moves (100 plies) occur without a capture taking place or a pawn being moved, the game ends in a draw.

**Invariant**
`Sometimes("game drawn after 50 moves with no capture or pawn move")` — fired by the workload when it observes a position reached after 50 captureless moves and confirms the game is scored/declared a draw. `Sometimes` because it asserts a meaningful progress state (the draw) eventually becomes true under exploration, rather than an invariant on every position.

**Why It Matters**
Without the rule, a drawn position can be played indefinitely; a player can be denied a deserved draw, or the engine can keep "winning" a dead position. It is one of the standard FIDE termination conditions a complete chess implementation must honor.