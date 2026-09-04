#!/usr/bin/env python3
"""Fixture tests for check_rule_coverage.py.

A coverage checker that cannot fail is worse than none: it reports a tidy
inventory, everybody believes the prompt is enforced, and the next
"EXACTLY 4 suspects" walks straight through. So the tests here are the two
failure modes, not the happy path.
"""

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import check_rule_coverage as C                        # noqa: E402

_failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n          {detail}" if detail else ""))
        _failures.append(name)


def _quiet(fn, *a, **kw):
    """Run something that prints a whole report, keeping only its exit code."""
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*a, **kw)
    return rc, buf.getvalue()


def _restore():
    C.PROMPT_FILE = _ROOT / "server" / "main.py"
    C.ASSERTIONS = list(_ORIGINAL)


_ORIGINAL = list(C.ASSERTIONS)


def test_clean():
    print("\nthe repository as it stands")
    rc, out = _quiet(C.main)
    check("the current inventory passes", rc == 0, out[-400:])
    check("and it reports the standing gaps rather than hiding them",
          "UNENFORCED" in out)


def test_new_assertion_fails():
    print("\na new assertion nobody triaged")
    # This is the "EXACTLY 4 suspects" shape: an imperative added to the prompt
    # with nothing enforcing it and nobody having decided that is acceptable.
    src = (_ROOT / "server" / "main.py").read_text(encoding="utf-8")
    patched = src.replace(
        "- key_evidence must list at least 2 evidence IDs.",
        "- key_evidence must list at least 2 evidence IDs.\n"
        "  - EVERY suspect must own a hat. Absolutely mandatory.", 1)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(patched)
        tmp = Path(f.name)
    try:
        C.PROMPT_FILE = tmp
        rc, out = _quiet(C.main)
        check("an untriaged imperative fails the check", rc == 1, out[-300:])
        check("and the report names it", "must own a hat" in out)
    finally:
        _restore()
        tmp.unlink(missing_ok=True)


def test_dead_rule_id_fails():
    print("\na rule id that no longer exists")
    # Renaming a rule leaves an inventory entry claiming coverage that is gone.
    try:
        C.ASSERTIONS = _ORIGINAL + [
            ("bogus", "EXACTLY 4 suspects", "enforced", ["NARR.NOT_A_REAL_RULE"])]
        rc, out = _quiet(C.main)
        check("claiming a non-existent rule fails the check", rc == 1, out[-300:])
        check("and the report names the dead id", "NARR.NOT_A_REAL_RULE" in out)
    finally:
        _restore()


def test_stale_entry_fails():
    print("\nan assertion deleted from the prompt")
    try:
        C.ASSERTIONS = _ORIGINAL + [
            ("ghost", "this sentence is not in the prompt", "UNENFORCED", "n/a")]
        rc, out = _quiet(C.main)
        check("an inventory entry with no matching prompt text fails", rc == 1, out[-300:])
        check("and the report calls it stale", "STALE" in out and "ghost" in out)
    finally:
        _restore()


def test_wrapped_lines_are_not_phantoms():
    print("\nwrapped assertions")
    # The first run reported four phantom "new assertions" that were merely the
    # continuation lines of assertions already inventoried.
    lines = C.prompt_lines()
    check("a wrapped assertion is grouped into one entry, not several",
          any("implicated by at least one item" in ln
              and "implicates: names of suspects" in ln for ln in lines),
          "continuation lines are not being joined to their bullet")


if __name__ == "__main__":
    test_clean()
    test_new_assertion_fails()
    test_dead_rule_id_fails()
    test_stale_entry_fails()
    test_wrapped_lines_are_not_phantoms()

    print()
    if _failures:
        print(f"=== {len(_failures)} FAILED ===")
        for f in _failures:
            print(f"    {f}")
        raise SystemExit(1)
    print("=== ALL PASSED ===")
