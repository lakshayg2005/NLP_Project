"""Check (and optionally repair) span annotations against docs/annotation_guide.md.

    python scripts/lint_annotations.py            # report problems
    python scripts/lint_annotations.py --fix      # move offending edge words outside the span

Checked files: ``data/span_seed.txt``, ``data/span_test.txt`` and the template strings in
``scripts/generate_span_data.py``. Rules enforced:

* R1  a span has no leading or trailing whitespace or punctuation;
* R2  a span does not start with an article, demonstrative or possessive (the, a, this, our, ...);
* R3  a span does not start or end with a bare connective (and, or, but, so, then);
* R4  a span stays inside one sentence (except a SHAMING opt-out label, which is one unit).
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [ROOT / "data" / "span_seed.txt", ROOT / "data" / "span_test.txt",
         ROOT / "scripts" / "generate_span_data.py"]

SPAN = re.compile(r"\[\[(\w+)\|(.+?)\]\]")
DETERMINERS = r"(?:the|a|an|this|that|these|those|our|your|my|their|its)"
CONNECTIVES = r"(?:and|or|but|so|then)"
LEAD = re.compile(rf"^(\s*[,;:.!?\-\u2013\u2014]*\s*)((?:{DETERMINERS}|{CONNECTIVES})\s+)", re.I)
LEAD_JUNK = re.compile(r"^[\s,;:.!?\-\u2013\u2014]+")
TRAIL_JUNK = re.compile(r"[\s,;:.!?\-\u2013\u2014]+$")
TRAIL_CONN = re.compile(rf"(\s+{CONNECTIVES})$", re.I)


def split_edges(phrase: str) -> tuple[str, str, str]:
    """Return (moved_left, core, moved_right) so that ``core`` satisfies R1-R3."""
    left, right = "", ""
    changed = True
    while changed:
        changed = False
        for pattern in (LEAD_JUNK,):
            m = pattern.match(phrase)
            if m:
                left += m.group(0); phrase = phrase[m.end():]; changed = True
        m = re.match(rf"^({DETERMINERS}|{CONNECTIVES})\s+", phrase, re.I)
        if m and len(phrase) > m.end():
            left += m.group(0); phrase = phrase[m.end():]; changed = True
        m = TRAIL_JUNK.search(phrase)
        if m and not (phrase[m.start():].strip() in {"%", ")", "*"}):
            right = m.group(0) + right; phrase = phrase[:m.start()]; changed = True
        m = TRAIL_CONN.search(phrase)
        if m:
            right = m.group(1) + right; phrase = phrase[:m.start()]; changed = True
    return left, phrase, right


def problems(phrase: str, tag: str = "") -> list[str]:
    out = []
    if LEAD_JUNK.match(phrase) or TRAIL_JUNK.search(phrase) and not re.search(r"[%)*]$", phrase.rstrip()):
        out.append("R1 edge whitespace/punctuation")
    if re.match(rf"^{DETERMINERS}\s", phrase, re.I):
        out.append("R2 leading determiner")
    if re.match(rf"^{CONNECTIVES}\s", phrase, re.I) or TRAIL_CONN.search(phrase):
        out.append("R3 edge connective")
    # A confirm-shaming opt-out label is one unit even if it contains "!" ("No thanks! I ...").
    if tag != "SHAMING" and re.search(r"[.!?]\s+[A-Z]", phrase):
        out.append("R4 crosses sentence boundary")
    return out


def process(path: Path, fix: bool) -> int:
    text = path.read_text(encoding="utf-8")
    count = 0

    def repl(m):
        nonlocal count
        tag, phrase = m.group(1), m.group(2)
        bad = problems(phrase, tag)
        if not bad:
            return m.group(0)
        count += 1
        print(f"{path.name}: [{tag}] {phrase!r}: {', '.join(bad)}")
        if not fix:
            return m.group(0)
        left, core, right = split_edges(phrase)
        return f"{left}[[{tag}|{core}]]{right}"

    new = SPAN.sub(repl, text)
    if fix and new != text:
        path.write_text(new, encoding="utf-8")
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()
    total = sum(process(p, args.fix) for p in FILES)
    print(f"\n{total} span(s) {'repaired' if args.fix else 'violate the guide'}")
    sys.exit(0 if args.fix or total == 0 else 1)


if __name__ == "__main__":
    main()
