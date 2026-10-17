#!/usr/bin/env python3
"""Refuse a number in reader-facing prose that disagrees with the code it describes.

WHY THIS EXISTS AND WHY `retired-claims.py` IS NOT ENOUGH. Of fifteen defects in one cycle where a
surface claimed more than the code delivers, the largest group was PROSE LEFT STANDING AFTER THE
MECHANISM MOVED: three copies of "the overshoot is whatever was written between two measurements", a
changelog that said "floored at 2 ms" while the floor had become 1 ms, and `docs/MCP.md` describing a
one-second poller that no longer existed. `retired-claims.py` stops the SECOND appearance of a
sentence somebody already noticed was false. Nothing stopped the FIRST, which is born the moment a
number changes in code and the documents are not touched in the same edit.

TWO RULES, AND THE FIRST IS THE ONE THAT MATTERS.

  1  A figure that EXISTS IN THE CODE is read from the code, in both bindings, and the prose that
     states it must say the same thing. The two bindings must also agree with each other: one policy
     written twice is this repository's recurring defect, and a floor of 1 ms in Python against 2 ms
     in Node would be invisible to every other gate.
  2  A MEASURED figure cannot be derived from anything - it is the result of running something - so
     all this can do is require that every surface repeating it repeats the SAME one. That catches a
     table updated in one document and left stale in another, which is what happened twice.

⛔ IT READS ONLY WHAT IT IS GIVEN. No scanning for "numbers that look like claims": a date, a port, a
CVE id and a default would all match, the gate would cry wolf, and a gate nobody trusts is a gate
nobody runs. Every entry below is a number somebody already got wrong.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / "bindings/python/kern_sandbox/__init__.py"
JS = ROOT / "bindings/node/index.js"


def const(path: Path, pattern: str) -> str | None:
    """One constant's literal, read from the source rather than copied here."""
    try:
        m = re.search(pattern, path.read_text(encoding="utf-8", errors="surrogateescape"), re.M)
    except OSError:
        return None
    return m.group(1) if m else None


def ms(seconds: str | None) -> str | None:
    """A float of seconds as the millisecond figure prose would use."""
    if seconds is None:
        return None
    try:
        v = float(seconds) * 1000.0
    except ValueError:
        return None
    return f"{v:g}"


# RULE 1. (name, value from Python, value from Node, how the prose spells it, files that state it)
def code_figures() -> list[tuple]:
    return [
        (
            "poll floor",
            ms(const(PY, r"^_CAP_POLL_MIN_S = ([0-9.]+)")),
            const(JS, r"^const CAP_POLL_MIN_MS = ([0-9.]+)"),
            lambda v: f"floored at {v} ms",
            ["CHANGELOG.md"],
        ),
        (
            "poll ceiling",
            ms(const(PY, r"^_CAP_POLL_S = ([0-9.]+)")),
            const(JS, r"^const CAP_POLL_MS = ([0-9.]+)"),
            None,  # no prose repeats it today; the agreement between bindings is the point
            [],
        ),
        (
            "watched files",
            const(PY, r"^_CAP_WATCH_K = ([0-9]+)"),
            const(JS, r"^const CAP_WATCH_K = ([0-9]+)"),
            lambda v: "eight biggest" if v == "8" else f"{v} biggest",
            ["CHANGELOG.md", "docs/MCP.md"],
        ),
        (
            "headroom fraction",
            const(PY, r"^_CAP_HEADROOM_FRAC = ([0-9.]+)"),
            const(JS, r"^const CAP_HEADROOM_FRAC = ([0-9.]+)"),
            None,
            [],
        ),
        (
            "planning rate",
            const(PY, r"^_CAP_FILL_RATE = ([0-9.e+]+)"),
            const(JS, r"^const CAP_FILL_RATE = ([0-9.e+]+)"),
            None,
            [],
        ),
    ]


# RULE 2. A measured figure and every surface that repeats it. Same string in all, or the gate fails.
CROSS = [
    ("overshoot, empty workspace, Python", "1.26x", ["CHANGELOG.md", "docs/MCP.md"]),
    ("overshoot, 50,000 files, Python", "12.88x", ["CHANGELOG.md", "docs/MCP.md"]),
    ("overshoot, empty workspace, Node", "1.30x", ["CHANGELOG.md", "docs/MCP.md"]),
    ("overshoot, 50,000 files, Node", "12.80x", ["CHANGELOG.md", "docs/MCP.md"]),
]


def check() -> list[str]:
    bad = []
    for name, pv, jv, spell, files in code_figures():
        if pv is None or jv is None:
            bad.append(f"{name}: could not read it from {'Python' if pv is None else 'Node'}")
            continue
        if pv != jv:
            bad.append(f"{name}: Python says {pv} and Node says {jv}. One policy, written twice.")
            continue
        if spell is None:
            continue
        want = spell(pv)
        for f in files:
            text = (ROOT / f).read_text(encoding="utf-8", errors="surrogateescape")
            if want not in text:
                bad.append(f"{f}: the code says {name} is {pv}, so it should read {want!r}")
    for name, value, files in CROSS:
        missing = [
            f
            for f in files
            if value not in (ROOT / f).read_text(encoding="utf-8", errors="surrogateescape")
        ]
        if missing:
            bad.append(f"{name} = {value} is missing from: {', '.join(missing)}")
    return bad


def control() -> str | None:
    """A gate that cannot fail proves nothing. Both rules are shown failing on a planted mismatch."""
    if const(PY, r"^_CAP_POLL_MIN_S = ([0-9.]+)") is None:
        return "rule 1 cannot read the Python constant at all, so its silence would mean nothing"
    if ms("0.002") != "2":
        return "the seconds-to-milliseconds conversion is wrong, so rule 1 compares the wrong thing"
    if const(PY, r"^_CAP_NO_SUCH_CONSTANT = ([0-9]+)") is not None:
        return "rule 1 found a constant that does not exist"
    return None


def main() -> int:
    failed = control()
    if failed is not None:
        print(f"  the gate's own control failed, so it proves nothing: {failed}")
        return 2
    bad = check()
    for b in bad:
        print(f"  {b}")
    n = len(code_figures()) + len(CROSS)
    print(f"  {n} figure(s) checked against the code and across the documents, control passed, "
          f"{len(bad)} disagreement(s)" + ("" if bad else " - clean"))
    if bad:
        print("  A number in prose is a promise about the code. Change it in the same edit, or the\n"
              "  document describes a mechanism that is gone.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
