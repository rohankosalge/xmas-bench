"""LLM agents for the crossword XMAS: word proposer + cell-letter guesser."""

import json
import re

import config
import llm

PROPOSE_SYS = (
    "You are an expert crossword solver. Given a clue, its answer length, and a letter "
    "pattern ('?' = unknown), return the most likely answers. Answers are UPPERCASE A-Z "
    "only: drop spaces/punctuation (\"I'll go\" -> ILLGO) and match the length exactly. "
    'Reply with JSON only: {"answers": [{"word": "ILLGO", "confidence": 0.9}]}. '
    'If the clue is too hard to guess, reply {"answers": []}.'
)


def propose(clue, length, pattern, model=None, k=None):
    """Top-k (word, confidence) candidates matching length + pattern; [] to skip."""
    k = k or config.TOP_K
    msg = [
        {"role": "system", "content": PROPOSE_SYS},
        {"role": "user", "content": f"Clue: {clue}\nLength: {length}\nPattern: {pattern}\nGive up to {k}."},
    ]
    raw = llm.chat(msg, model=model or config.PROPOSER_MODEL)
    out = []
    for a in _parse_answers(raw):
        word = re.sub(r"[^A-Z]", "", str(a.get("word", "")).upper())
        if len(word) == length and _matches(word, pattern):
            out.append((word, float(a.get("confidence", 0.5))))
    return sorted(out, key=lambda x: -x[1])[:k]


def guess_letter(clues, model=None):
    """Most likely letter for one cell. `clues` = [(clue, pattern), ...] through it.
    Uses first-token logprobs (top-1), falling back to a temp-0 single letter."""
    model = model or config.CELL_MODEL
    ctx = "\n".join(f"- {c} (pattern {p})" for c, p in clues)
    msg = [
        {"role": "system", "content": "You solve crossword cells. Reply with ONE uppercase letter."},
        {"role": "user", "content": f"This cell belongs to:\n{ctx}\nMost likely letter?"},
    ]
    lp = llm.next_token_logprobs(msg, model)
    if lp:
        for tok, _ in sorted(lp, key=lambda x: -x[1]):
            ch = re.sub(r"[^A-Z]", "", tok.upper())
            if len(ch) == 1:
                return ch
    return re.sub(r"[^A-Z]", "", llm.chat(msg, model=model).upper())[:1] or None


def _parse_answers(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        return json.loads(m.group(0))["answers"] if m else []
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _matches(word, pattern):
    return all(p == "?" or p == w for w, p in zip(word, pattern))
