"""Tiny rule-based negation check used to drop regex hits like "no recurring fees".

A hit is treated as negated when a negation cue ("no", "not", "never", "without",
"doesn't", ...) appears at most ``MAX_GAP`` words before it inside the same clause.
Commas, semicolons, full stops and words like "but" / "then" end a clause, so
"No thanks, only 2 left" is NOT treated as negated.

Two refinements keep coordinated lists inside the scope of one cue:

* a hit introduced by "and" / "or" / "nor" ("no setup fees or *activation fees*") looks a
  few words further back, and
* a comma list that ends in "or" / "and" ("not intended to diagnose, treat, or *cure*")
  is read as one clause.
"""

import re

MAX_GAP = 5          # words allowed between the cue and the matched phrase
COORD_EXTRA = 4      # extra look-back when the hit follows "and" / "or" / "nor"

_BREAK_CHARS = r"[.,;:!?()\u2013\u2014]"
_CLAUSE_BREAK = re.compile(_BREAK_CHARS + r"|\b(?:but|however|except|then|unless|although)\b", re.I)
_WORD = re.compile(r"[a-z']+")
_CONJ = {"and", "or", "nor"}
_CUES = {"no", "not", "never", "without", "nothing", "none", "neither", "nor"}
# "can't" / "cannot" restrict the customer ("you can't cancel online"), so they are not cues.
_NOT_CUES = {"can't", "cant", "cannot", "couldn't"}


def _is_cue(word: str) -> bool:
    if word in _NOT_CUES:
        return False
    return word in _CUES or word.endswith("n't")


def _last_word(text: str) -> str:
    words = _WORD.findall(text.lower())
    return words[-1] if words else ""


def _clause_before(prefix: str) -> str:
    """The clause that ends at the hit; a comma list ending in "or"/"and" counts as one."""
    parts = re.split(f"({_BREAK_CHARS}|\\b(?:but|however|except|then|unless|although)\\b)", prefix,
                     flags=re.I)
    segments, seps = parts[0::2], parts[1::2]
    i = len(segments) - 1
    clause = segments[i]
    if i > 0 and seps[i - 1] == "," and _last_word(clause) in _CONJ:
        # ", or cure": step back over the short comma-separated items of the list
        while i > 0 and seps[i - 1] == "," and (i == len(segments) - 1 or len(segments[i].split()) <= 3):
            i -= 1
            clause = segments[i] + " " + clause
    return clause


def is_negated(text: str, start: int) -> bool:
    """True if the phrase starting at ``start`` is negated by a cue just before it."""
    prefix = text[:start].replace("\u2019", "'")
    clause = _clause_before(prefix).lower()
    words = _WORD.findall(clause)
    window = MAX_GAP + 1 + (COORD_EXTRA if words and words[-1] in _CONJ else 0)
    return any(_is_cue(w) for w in words[-window:])
