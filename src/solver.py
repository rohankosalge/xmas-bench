"""Back-compat shim: solve() now runs the modular engine (see engine.py)."""

import config
import engine


def solve(puzzle, proposer_model=None, cell_model=None, rounds=None):
    """Solve a puz.Puzzle with a one-off baseline-style spec."""
    spec = {
        "roles": {
            "proposer": proposer_model or config.PROPOSER_MODEL,
            "cell": cell_model or config.CELL_MODEL,
        },
        "pipeline": ["propose_words", "apply_greedy", "cell_cascade"],
        "rounds": rounds or config.MAX_ROUNDS,
    }
    return engine.run(puzzle, spec)
