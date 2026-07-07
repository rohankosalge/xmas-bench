"""Deterministic crossword grid."""

from dataclasses import dataclass


@dataclass
class Slot:
    id: str            # e.g. "1A"
    direction: str     # "A" or "D"
    cells: list        # grid indices, in order
    clue: str

    @property
    def length(self):
        return len(self.cells)


class GridManager:
    def __init__(self, puzzle):
        self.width, self.height = puzzle.width, puzzle.height
        self.answer = puzzle.solution                     # for scoring/reference
        self.letters = {}                                 # cell index -> letter
        self.slots = []
        n = puzzle.clue_numbering()
        for e in n.across:
            cells = [e["cell"] + i for i in range(e["len"])]
            self.slots.append(Slot(f"{e['num']}A", "A", cells, e["clue"]))
        for e in n.down:
            cells = [e["cell"] + i * self.width for i in range(e["len"])]
            self.slots.append(Slot(f"{e['num']}D", "D", cells, e["clue"]))

    def pattern(self, slot):
        """Current letters with '?' for blanks, e.g. 'S?I?K'."""
        return "".join(self.letters.get(c, "?") for c in slot.cells)

    def fits(self, slot, word):
        return len(word) == slot.length and all(
            self.letters.get(c, ch) == ch for c, ch in zip(slot.cells, word)
        )

    def place(self, slot, word):
        """Write a fitting word; return True on success."""
        if not self.fits(slot, word):
            return False
        self.letters.update(zip(slot.cells, word))
        return True

    def set_cell(self, index, letter):
        self.letters[index] = letter

    def missing_cells(self, slot):
        return [c for c in slot.cells if c not in self.letters]

    def crossing_slots(self, slot):
        cells = set(slot.cells)
        return [s for s in self.slots if s is not slot and cells & set(s.cells)]

    def unsolved_slots(self):
        return [s for s in self.slots if self.missing_cells(s)]

    def is_complete(self):
        return not self.unsolved_slots()

    def solution_string(self):
        """Filled grid aligned to puzzle.solution ('.' for black, '?' for blank)."""
        return "".join(
            "." if ch == "." else self.letters.get(i, "?")
            for i, ch in enumerate(self.answer)
        )

    def render(self):
        rows = []
        for r in range(self.height):
            row = self.solution_string()[r * self.width:(r + 1) * self.width]
            rows.append(" ".join(row))
        return "\n".join(rows)
