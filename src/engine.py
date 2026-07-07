"""Modular XMAS (Xword Multi-Agent System) engine: pluggable agent roles + a step pipeline.

A variant spec (see config.XMAS_VARIANTS) picks roles, their models, and the ordered
pipeline of steps. Roles emit Proposal diffs; the deterministic GridManager applies them.
"""

from dataclasses import dataclass, field

import agents
from grid import GridManager

ROLES = {}   # name -> Role subclass
STEPS = {}   # name -> step fn(ctx)


def register(cls):
    ROLES[cls.name] = cls
    return cls


def step(fn):
    STEPS[fn.__name__] = fn
    return fn


@dataclass
class Proposal:
    kind: str          # "word" | "cell"
    target: object     # slot id (word) or cell index (cell)
    value: str         # word or single letter
    confidence: float
    source: str        # role name


@dataclass
class Context:
    grid: GridManager
    roles: dict
    id2slot: dict
    proposals: list = field(default_factory=list)
    round_start: dict = field(default_factory=dict)
    round_no: int = 0
    trace: list = field(default_factory=list)   # ordered events for replays


# --- roles (agents as plugins) -------------------------------------------------

class Role:
    name = ""

    def __init__(self, model=None):
        self.model = model


@register
class ProposerRole(Role):
    name = "proposer"

    def propose(self, grid):
        out = []
        for s in grid.unsolved_slots():
            for word, conf in agents.propose(s.clue, s.length, grid.pattern(s), self.model):
                out.append(Proposal("word", s.id, word, conf, self.name))
        return out


@register
class CellRole(Role):
    name = "cell"

    def guess(self, grid, cell):
        through = [(t.clue, grid.pattern(t)) for t in grid.slots if cell in t.cells]
        letter = agents.guess_letter(through, self.model)
        return Proposal("cell", cell, letter, 1.0, self.name) if letter else None


# --- steps (procedure catalog) -------------------------------------------------

@step
def propose_words(ctx):
    new = ctx.roles["proposer"].propose(ctx.grid)
    ctx.proposals += new
    by_slot = {}
    for p in new:
        by_slot.setdefault(p.target, []).append(p)
    for sid, props in by_slot.items():
        s = ctx.id2slot[sid]
        ctx.trace.append({
            "type": "propose", "round": ctx.round_no, "role": "proposer",
            "slot": sid, "clue": s.clue, "pattern": ctx.grid.pattern(s),
            "candidates": [{"word": p.value, "conf": round(p.confidence, 3),
                            "fits": ctx.grid.fits(s, p.value)} for p in props],
        })


@step
def apply_greedy(ctx):
    """Place highest-confidence fitting word proposals, propagating after each."""
    g, words = ctx.grid, [p for p in ctx.proposals if p.kind == "word"]
    changed = True
    while changed:
        changed = False
        best = None
        for p in words:
            s = ctx.id2slot[p.target]
            if g.missing_cells(s) and g.fits(s, p.value) and (best is None or p.confidence > best.confidence):
                best = p
        if best:
            s = ctx.id2slot[best.target]
            g.place(s, best.value)
            ctx.trace.append({
                "type": "place", "round": ctx.round_no, "source": best.source,
                "slot": best.target, "clue": s.clue, "word": best.value,
                "conf": round(best.confidence, 3), "cells": list(s.cells),
            })
            changed = True
    ctx.proposals = [p for p in ctx.proposals if p.kind != "word"]


@step
def cell_cascade(ctx):
    """When words made no progress this round, guess stuck cells letter-by-letter (top-1)."""
    g = ctx.grid
    if g.letters != ctx.round_start:
        return
    role = ctx.roles["cell"]
    for s in sorted(g.unsolved_slots(), key=lambda s: len(g.missing_cells(s))):
        for cell in g.missing_cells(s):
            p = role.guess(g, cell)
            if p:
                g.set_cell(p.target, p.value)
                ctx.trace.append({
                    "type": "guess", "round": ctx.round_no, "source": p.source,
                    "cell": p.target, "letter": p.value,
                })


# --- engine --------------------------------------------------------------------

def _run(puzzle, spec):
    """Run an XMAS variant spec; return the full Context (grid + trace)."""
    grid = GridManager(puzzle)
    ctx = Context(
        grid=grid,
        roles={n: ROLES[n](m) for n, m in spec["roles"].items()},
        id2slot={s.id: s for s in grid.slots},
    )
    for i in range(spec["rounds"]):
        if grid.is_complete():
            break
        before = dict(grid.letters)
        ctx.round_no, ctx.round_start, ctx.proposals = i, before, []
        for name in spec["pipeline"]:
            STEPS[name](ctx)
        if grid.letters == before:
            break
    return ctx


def run(puzzle, spec):
    """Run an XMAS variant spec on a puz.Puzzle; return the (possibly partial) GridManager."""
    return _run(puzzle, spec).grid
