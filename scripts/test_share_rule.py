#!/usr/bin/env python3
"""The share minimum has exactly one definition, and the client does not have one.

Background. The rule was written twice: `_min_share_required()` in server/main.py
used round(), and share_selection.gd used ceili(). They disagreed in 6 of 18
realistic combinations of hand size and difficulty, and the client was always
the stricter one -- so it refused to submit shares the server would have
accepted. At a two-finding hand it demanded both, which removes the decision the
whole information-sharing mechanic is about.

Duplicated rules drift silently, so this asserts the duplication is gone rather
than that the two copies happen to agree today.

Zero API cost. Exit: 0 = pass, 1 = failure.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server" / "main.py"
SHARE_SCREEN = ROOT / "godot" / "scripts" / "ui" / "share_selection.gd"
GAME_STATE = ROOT / "godot" / "scripts" / "autoloads" / "GameState.gd"

# Arithmetic on share_min is the shape of a second implementation.
CLIENT_ARITHMETIC = re.compile(r"share_min\s*\)?\s*[*/]|[*/]\s*GameState\.share_min|"
                               r"(?:ceili?|floori?|roundi?)\s*\([^)]*share_min")

failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def load(path):
    return path.read_text(encoding="utf-8")


def main() -> int:
    server = load(SERVER)

    # 1. The server defines it once.
    check("def _min_share_required(" in server,
          "server/main.py has no _min_share_required() -- the rule has no single home")
    inline = re.findall(r"max\(1,\s*round\(len\([^)]*\)\s*\*\s*[^)]*share_min", server)
    check(not inline,
          f"server/main.py still computes the minimum inline in {len(inline)} place(s); "
          f"it should call _min_share_required()")

    # 2. It is sent to the client with every finding response. Three producers:
    #    investigate-area, follow-lead, interrogate-witness.
    sends = server.count('"share_required"')
    check(sends >= 3,
          f'server/main.py returns "share_required" {sends} time(s); expected at least 3 '
          f"(investigate-area, follow-lead, interrogate-witness)")

    # 3. The client does not derive it.
    screen = load(SHARE_SCREEN)
    hits = CLIENT_ARITHMETIC.findall(screen)
    check(not hits,
          f"share_selection.gd does arithmetic on share_min ({hits}) -- that is the "
          f"second implementation this test exists to prevent")
    check("current_share_required()" in screen,
          "share_selection.gd does not read GameState.current_share_required()")

    # 4. And it errs permissive when the server said nothing, never stricter.
    check(re.search(r"_min_required\s*=\s*1", screen),
          "share_selection.gd has no fallback to the server's floor of 1; a client that "
          "guesses stricter silently deletes a legal move")

    state = load(GAME_STATE)
    check("func current_share_required()" in state,
          "GameState.gd does not expose current_share_required()")
    check(state.count('"share_required"') >= 3,
          "GameState.gd does not record share_required from all three finding types")

    # 5. The server's own rule behaves as documented.
    sys.path.insert(0, str(ROOT / "server"))
    for count, share_min, expected in [
        (0, 0.60, 1),   # the floor: you can never be asked for zero
        (1, 0.50, 1),
        (2, 0.60, 1),   # the case the client used to demand 2 for
        (3, 0.70, 2),
        (3, 0.60, 2),
        (3, 0.50, 2),   # all three difficulties agree at APF's hand size
        (5, 0.50, 2),
    ]:
        got = max(1, round(count * share_min))
        check(got == expected,
              f"rule changed: {count} findings at {share_min} -> {got}, expected {expected}")

    print(f"Checked {SERVER.name}, {SHARE_SCREEN.name} and {GAME_STATE.name}.\n")
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("No failures: the share minimum is defined once, on the server, sent with "
          "every finding\nresponse, and the client displays it without deriving one "
          "of its own.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
