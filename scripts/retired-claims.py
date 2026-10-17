#!/usr/bin/env python3
"""Refuse a reader-facing surface that states something the code no longer does, or never did.

WHY THIS GATE EXISTS, AND WHY THE FIVE DOCUMENT GATES DID NOT CATCH ANY OF IT. Fifteen defects in one
work cycle were a surface a reader trusts claiming more than the implementation delivers, and the
repository caught ZERO of them mechanically: every one was found by a person reading. `stale-numbers`
is the closest and it compares a number against the same number in another document - it cannot
compare a sentence against the CODE, and it has no idea which values are RETIRED.

They were not one bug, though, and treating them as one produced instance-patching. Four mechanisms:

  A  a message built where the fact it states was never observed (a mode-0 FILE called "a directory",
     four call sites that passed no path at all). Controlled by the AST/arity pins in
     `bindings/python/tests/test_sandbox.py` and `bindings/node/test/sandbox.test.js`.
  B  a cause inferred from an incomplete signal (an EMPTY registry body read as a private repo, a
     `"code"` key found anywhere in a document). Controlled by the sabotage tests in `kern-oci`.
  C  prose left standing after the mechanism moved (three copies of "whatever was written between two
     measurements"; "floored at 2 ms" against a 1 ms floor; `docs/MCP.md`'s one-second poller).
     THIS GATE, rule 1.
  D  an absolute in an introduction that the product does not keep ("where it cannot touch your
     machine", "they are never in it"). THIS GATE, rule 2.

⛔ IT READS ONLY READER-FACING TEXT. Not `crates/**/*.rs`, not the SDK sources: a comment that says
"never" is usually recording a MEASUREMENT, and a gate that fires on evidence gets disabled within a
month - after which the class is back with a gate standing over it. The scope below is the text a user
meets, and nothing else.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The text a reader meets. Deliberately NOT the crates or the binding sources.
SCOPE = [
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "bindings/python/README.md",
    "bindings/node/README.md",
    "integrations/pi/README.md",
]
SCOPE_GLOBS = ["docs/*.md"]

# RULE 1: values and sentences the code has moved past. Each entry is the exact string a surface used
# to carry, with the date it stopped being true and what replaced it. A retired string is cheap to
# match and impossible to argue with, which is why this rule has no exceptions file.
RETIRED = [
    ("the overshoot is whatever was written between two measurements", "2026-10-17",
     "the interval scales to the headroom; the bound is one walk of the tree"),
    ("overshoot is whatever the box wrote between two measurements", "2026-10-17",
     "same"),
    ("bounded by the cap and not by the disk", "2026-10-17",
     "it is bounded by what the workspace costs to MEASURE"),
    ("bounds the overshoot by the CAP now, not by the disk", "2026-10-17", "same"),
    ("floored at 2 ms", "2026-10-17", "the floor is 1 ms, the granularity of the waits"),
    ("Measurements start one second apart", "2026-10-17",
     "the first interval is the probe's, scaled to the headroom"),
    ("one second can let ~800 MB past the cap", "2026-10-17",
     "the measured table, per workspace size"),
    ("cannot touch your machine", "2026-10-17",
     "it cannot reach your files unless you hand them over"),
    ("can't touch your machine", "2026-10-17", "same"),
    ("They are never in it", "2026-10-17",
     "nothing reaches the box by mount or by inheritance; `env=` does"),
]

# ⛔ THERE IS NO SECOND, GENERAL RULE, AND THE FIRST VERSION OF THIS GATE PROVED WHY. It flagged any
# sentence carrying an absolute ("never", "cannot", "always") next to a boundary word unless a hedge
# appeared in the same sentence. On its first run that fired 49 times and 47 were TRUE: "a box cannot
# remount its root writable", "credentials never touch argv", "a gate's exit code is read bare. Never
# through a pipe". Those are the sentences this project exists to be able to write.
#
# A gate with a 96% false-positive rate is disabled within a month, and then the class it was built for
# is back with a gate standing over it. So the only rule is the list above: EXACT strings, each with
# the date it stopped being true and what replaced it. A new entry is added when a mechanism moves -
# which is the moment somebody knows the old sentence is now false, and the cheapest moment to say so.
#
# What that gives up, named rather than hidden: it cannot find an over-claim nobody has noticed yet.
# It stops the SECOND appearance of one, in every surface, forever. The first appearance is still found
# by a person reading, and two of the four mechanisms in the header are controlled in code instead.


def files():
    seen = []
    for rel in SCOPE:
        p = ROOT / rel
        if p.is_file():
            seen.append(p)
    for g in SCOPE_GLOBS:
        seen.extend(sorted(ROOT.glob(g)))
    return seen


def check(paths, ok_set=None):
    bad = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            bad.append((p, 0, f"unreadable: {e}"))
            continue
        flat = " ".join(text.split())
        for needle, when, replacement in RETIRED:
            if needle.lower() in flat.lower():
                bad.append((p, 0, f"RETIRED since {when}: {needle!r} -> {replacement}"))
    return bad


def control():
    """A gate that cannot fail proves nothing, and one that fires on honest prose gets disabled.

    So the control asserts BOTH: a planted retired sentence is seen, and a true sentence carrying an
    absolute about a real boundary is NOT. The second half is this gate's own history - its first
    version flagged 49 sentences and 47 of them were true.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        planted = Path(d) / "planted.md"
        planted.write_text(
            "# probe\n\nIt runs where it cannot touch your machine.\n", encoding="utf-8"
        )
        if not check([planted], set()):
            return "a planted retired sentence was not seen"
        honest = Path(d) / "honest.md"
        honest.write_text(
            "# probe\n\nA box cannot remount its root writable, and credentials never touch argv.\n"
            "A gate's exit code is read bare. Never through a pipe.\n",
            encoding="utf-8",
        )
        noise = check([honest], set())
        if noise:
            return f"it fired on honest prose, which is how a gate dies: {noise[0][2][:80]}"
    return None


def main() -> int:
    failed = control()
    if failed is not None:
        print(f"  the gate's own control failed, so it proves nothing: {failed}")
        return 2
    paths = files()
    bad = check(paths)
    for p, lineno, why in bad:
        where = f"{p.relative_to(ROOT)}:{lineno}" if lineno else str(p.relative_to(ROOT))
        print(f"  {where}: {why}")
    print(
        f"  {len(paths)} reader-facing file(s) read, control passed, {len(bad)} claim(s) to fix"
        + ("" if bad else " - clean")
    )
    if bad:
        print(
            "  A sentence here is read as a promise, and the code stopped keeping this one. Say what\n"
            "  the code does now, in every surface that carries it."
        )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
