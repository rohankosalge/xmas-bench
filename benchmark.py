"""Score an XMAS variant on scraped minis. Resumable: cached puzzles are skipped.

    python benchmark.py --variant baseline --num 5
"""

import argparse
import glob
import json
import os

import puz

import config
import engine


def score(manager, puzzle):
    """Accuracy of a solved GridManager vs the true solution."""
    got, want = manager.solution_string(), puzzle.solution
    white = [i for i, ch in enumerate(want) if ch != "."]
    cells = sum(got[i] == want[i] for i in white)
    words = sum(
        all(manager.letters.get(c) == want[c] for c in s.cells) for s in manager.slots
    )
    return {
        "cell_acc": cells / len(white),
        "word_acc": words / len(manager.slots),
        "solved": got == want,
    }


def _check(spec):
    """Fail fast on a misconfigured variant."""
    for name in spec["roles"]:
        assert name in engine.ROLES, f"unknown role: {name}"
    for name in spec["pipeline"]:
        assert name in engine.STEPS, f"unknown step: {name}"


def run(variant, num):
    spec = config.XMAS_VARIANTS[variant]
    _check(spec)
    out_dir = os.path.join(config.RESULTS_DIR, variant)
    os.makedirs(out_dir, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(config.OUTPUT_DIR, "*.puz")))[:num]
    results = []
    for path in paths:
        name = os.path.splitext(os.path.basename(path))[0]
        cache = os.path.join(out_dir, name + ".json")
        if os.path.exists(cache):
            results.append(json.load(open(cache)))
        else:
            puzzle = puz.read(path)
            try:
                r = score(engine.run(puzzle, spec), puzzle)
            except Exception as e:
                r = {"error": str(e)}
            json.dump(r, open(cache, "w"))
            results.append(r)
        print(f"{name}: {results[-1]}")

    ok = [r for r in results if "error" not in r]
    if ok:
        print(f"\n{variant}: {len(ok)} puzzles | "
              f"cell {sum(r['cell_acc'] for r in ok)/len(ok):.1%} | "
              f"word {sum(r['word_acc'] for r in ok)/len(ok):.1%} | "
              f"solved {sum(r['solved'] for r in ok)}/{len(ok)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default=config.DEFAULT_VARIANT)
    ap.add_argument("--num", type=int, default=config.NUM_CROSSWORDS)
    args = ap.parse_args()
    run(args.variant, args.num)
