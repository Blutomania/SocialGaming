#!/usr/bin/env python3
"""Does an unrecoverable API error stop the batch, and a recoverable one not?

Zero API cost, no network, no anthropic SDK required (it is stubbed below).

The distinction under test is the whole point of the change: an exhausted
credit balance and an oversized single request are BOTH HTTP 400
invalid_request_error. The first means every remaining source will fail
identically and the batch should stop; the second means this one source is
too big and the batch should skip it and carry on. Keying off the status code
alone cannot tell them apart.
"""
import re
import sys
import tempfile
import types
from pathlib import Path

# extract_from_pdfs sys.exit()s at import if these are missing, and none of them
# are needed to exercise the classifier.
for name in ("anthropic", "pypdf"):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
if "dotenv" not in sys.modules:
    _dotenv = types.ModuleType("dotenv")
    _dotenv.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = _dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_from_pdfs as ex  # noqa: E402


class FakeAPIError(Exception):
    """Duck-types the SDK's APIStatusError: a message and a status_code."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


CREDIT = (
    "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
    "'message': 'Your credit balance is too low to access the Anthropic API. "
    "Please go to Plans & Billing to upgrade or purchase credits.'}}"
)

FATAL = [
    ("credit balance exhausted (the real Session 35 message)", FakeAPIError(CREDIT, 400)),
    ("credit balance, no status code at all",                  FakeAPIError(CREDIT)),
    ("bad api key",                                            FakeAPIError("invalid x-api-key", 401)),
    ("no permission",                                          FakeAPIError("forbidden", 403)),
    ("misspelled --model",                                     FakeAPIError("model: claude-opus-6", 404)),
]

SURVIVABLE = [
    ("rate limited",       FakeAPIError("rate_limit_error", 429)),
    ("server overloaded",  FakeAPIError("overloaded_error", 529)),
    ("transient 500",      FakeAPIError("internal server error", 500)),
    ("connection dropped", FakeAPIError("Connection error.")),
    # The one that matters most: same status as the credit error, different cause.
    ("one source too big for the context window",
     FakeAPIError("Error code: 400 - {'type': 'invalid_request_error', 'message': "
                  "'prompt is too long: 210000 tokens > 200000 maximum'}", 400)),
]

failures = 0

print("--- errors that must STOP the batch ---")
for label, exc in FATAL:
    reason = ex._fatal_reason(exc)
    if reason is None:
        print(f"  FAIL  {label}: treated as retryable, batch would grind on")
        failures += 1
    else:
        print(f"  PASS  {label}\n          → {reason}")

print("\n--- errors that must NOT stop the batch ---")
for label, exc in SURVIVABLE:
    reason = ex._fatal_reason(exc)
    if reason is not None:
        print(f"  FAIL  {label}: would abort the whole run ({reason})")
        failures += 1
    else:
        print(f"  PASS  {label}")

print("\n--- a fatal error is raised, not retried ---")


class OneShotClient:
    """Counts how many times the API is actually called."""
    def __init__(self, exc):
        self.exc = exc
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        raise self.exc


client = OneShotClient(FakeAPIError(CREDIT, 400))
try:
    ex._call_claude_for_protocol(client, "claude-opus-5", "prompt", "P1", "a source", verbose=False)
except ex.FatalAPIError as e:
    if client.calls == 1:
        print(f"  PASS  raised FatalAPIError after exactly 1 call, no pointless retry")
        print(f"          → {str(e).splitlines()[0]}")
    else:
        print(f"  FAIL  retried a call that cannot succeed ({client.calls} calls)")
        failures += 1
except Exception as e:
    print(f"  FAIL  raised {type(e).__name__} instead of FatalAPIError: {e}")
    failures += 1
else:
    print("  FAIL  no exception raised at all")
    failures += 1

print("\n--- a survivable error still retries, then raises ExtractionAPIError ---")
client = OneShotClient(FakeAPIError("Connection error."))
try:
    ex._call_claude_for_protocol(client, "claude-opus-5", "prompt", "P1", "a source", verbose=False)
except ex.ExtractionAPIError:
    if client.calls == 2:
        print("  PASS  retried once, then gave up on this source only (2 calls)")
    else:
        print(f"  FAIL  expected 2 calls, got {client.calls}")
        failures += 1
except Exception as e:
    print(f"  FAIL  raised {type(e).__name__}: {e}")
    failures += 1

print("\n--- FatalAPIError must escape the per-source handlers ---")
if issubclass(ex.FatalAPIError, ex.ExtractionAPIError):
    print("  FAIL  FatalAPIError subclasses ExtractionAPIError, so `except "
          "ExtractionAPIError` in\n        extract_pdf/extract_pdf_anthology would "
          "swallow it and the batch would continue")
    failures += 1
else:
    print("  PASS  it is not an ExtractionAPIError, so it propagates to main()")

print("\n--- and it really does escape extract_pdf(), not just in theory ---")

# extract_pdf() wraps its protocol loop in `except ExtractionAPIError: return None`.
# Class hierarchy says FatalAPIError slips past that; this runs it and checks.
import tempfile  # noqa: E402

_real_read = ex.extract_text_from_pdf
ex.extract_text_from_pdf = lambda path, max_chars=None: ("x" * 5000, "x" * 5000)
try:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp)
        (db / "extractions").mkdir(parents=True)
        client = OneShotClient(FakeAPIError(CREDIT, 400))
        try:
            ex.extract_pdf(Path("nonexistent.pdf"), client, ["P1"], db,
                           model="claude-opus-5", verbose=False)
        except ex.FatalAPIError:
            written = list((db / "extractions").glob("*.json"))
            if written:
                print(f"  FAIL  propagated, but wrote {[f.name for f in written]} anyway")
                failures += 1
            else:
                print("  PASS  propagated out of extract_pdf, and wrote no placeholder")
        except Exception as e:
            print(f"  FAIL  raised {type(e).__name__}: {e}")
            failures += 1
        else:
            print("  FAIL  extract_pdf swallowed it — the batch would carry on")
            failures += 1
finally:
    ex.extract_text_from_pdf = _real_read

print("\n--- the two scripts agree on what exit code 'fatal' is ---")

# upgrade_p1_to_p1p2.py runs extract_from_pdfs.py once per source as a subprocess
# and decides whether to keep going from the child's exit code alone. It cannot
# import the constant (that would drag anthropic/pypdf into merely planning a
# run), so it redeclares it — and a silent disagreement here would restore the
# exact bug this change removes, with every test above still passing.
_wrapper = (Path(__file__).resolve().parent / "upgrade_p1_to_p1p2.py").read_text()
_declared = re.search(r"^EXIT_FATAL\s*=\s*(\d+)", _wrapper, re.M)
if _declared is None:
    print("  FAIL  upgrade_p1_to_p1p2.py no longer declares EXIT_FATAL")
    failures += 1
elif int(_declared.group(1)) != ex.EXIT_FATAL:
    print(f"  FAIL  wrapper says EXIT_FATAL={_declared.group(1)}, "
          f"extract_from_pdfs says {ex.EXIT_FATAL} — the wrapper would not stop")
    failures += 1
elif ex.EXIT_FATAL == ex.EXIT_SOURCE_FAILED:
    print("  FAIL  fatal and per-source failure share an exit code, so they "
          "cannot be told apart")
    failures += 1
else:
    print(f"  PASS  both use exit {ex.EXIT_FATAL}, distinct from "
          f"{ex.EXIT_SOURCE_FAILED} for a single failed source")


# ---------------------------------------------------------------------------
# End-to-end: the exit code is the contract the wrapper actually depends on.
#
# upgrade_p1_to_p1p2.py runs this script as a SUBPROCESS, once per source, and
# has nothing to go on but the exit status. Every check above could pass while
# the process still exited 0 and the wrapper still marched through the corpus.
# So run the real script, with the SDK stubbed out on PYTHONPATH, and look at
# what the shell gets back.
# ---------------------------------------------------------------------------
import subprocess  # noqa: E402
import textwrap  # noqa: E402

SCRIPT = Path(__file__).resolve().parent / "extract_from_pdfs.py"

STUBS = {
    "pypdf.py": '''
class _Page:
    def extract_text(self):
        return "The body was found in the library. " * 400
class PdfReader:
    def __init__(self, path):
        self.pages = [_Page() for _ in range(12)]
''',
    "dotenv.py": "def load_dotenv(*a, **k):\n    pass\n",
}

ANTHROPIC_STUB = '''
class _APIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class _Messages:
    def create(self, **kwargs):
        if {message!r} == "KEYBOARD":
            raise KeyboardInterrupt
        raise _APIError({message!r}, {status!r})

class Anthropic:
    def __init__(self, **kwargs):
        self.messages = _Messages()
'''


def run_real_script(message, status):
    """Run extract_from_pdfs.py for real against a stubbed SDK. Returns (rc, output)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        stubs = tmp / "stubs"
        stubs.mkdir()
        for name, body in STUBS.items():
            (stubs / name).write_text(textwrap.dedent(body))
        (stubs / "anthropic.py").write_text(
            ANTHROPIC_STUB.format(message=message, status=status))

        pdf = tmp / "A Study in Scarlet.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")  # never parsed; pypdf is the stub above
        db = tmp / "db"
        (db / "extractions").mkdir(parents=True)

        env = dict(os.environ)
        env["PYTHONPATH"] = str(stubs)
        env["ANTHROPIC_API_KEY"] = "sk-ant-not-a-real-key"
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(pdf), "--protocol", "P1", "--db-dir", str(db)],
            capture_output=True, text=True, env=env, cwd=str(SCRIPT.parent.parent),
        )
        return proc.returncode, proc.stdout + proc.stderr


import os  # noqa: E402

print("\n--- the anthology path stops too, and keeps what it already earned ---")

# This is the path that actually ran in Session 35: upgrade_p1_to_p1p2.py sorts by
# extraction count descending, so a 63-story anthology goes first. Seven stories
# upgraded, then the credit balance died. extract_pdf_anthology has its own
# per-story `except ExtractionAPIError: continue`, so without the fix it would
# have failed the remaining 56 stories one at a time before the wrapper moved on
# to the novels.
class DiesAfter:
    """Succeeds for n calls, then fails fatally forever."""
    def __init__(self, n):
        self.n = n
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        if self.calls > self.n:
            raise FakeAPIError(CREDIT, 400)
        block = types.SimpleNamespace(type="text", text='{"crime_type": {"value": "murder", '
                                                        '"confidence": "high", "quote": "q"}}')
        return types.SimpleNamespace(content=[block], stop_reason="end_turn")


_real_split = ex._split_anthology_stories
ex._split_anthology_stories = lambda path: [
    {"index": i, "title": f"Story {i}", "author": "A. Writer",
     "text": "The body was found in the library. " * 200,
     "start_page": i, "end_page": i + 1}
    for i in range(1, 6)
]
try:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp)
        (db / "extractions").mkdir(parents=True)
        client = DiesAfter(2)  # two stories land, the third hits the dead balance
        try:
            ex.extract_pdf_anthology(Path("An Anthology.pdf"), client, ["P1"], db,
                                     model="claude-opus-5", verbose=False)
        except ex.FatalAPIError:
            saved = sorted(f.name for f in (db / "extractions").glob("*.json"))
            if len(saved) == 2:
                print(f"  PASS  stopped at story 3, kept the 2 already extracted")
            else:
                print(f"  FAIL  expected 2 saved stories, got {len(saved)}: {saved}")
                failures += 1
            if client.calls == 3:
                print("  PASS  and made no further calls — 2 successes + 1 fatal")
            else:
                print(f"  FAIL  kept calling after the fatal error ({client.calls} calls)")
                failures += 1
        except Exception as e:
            print(f"  FAIL  raised {type(e).__name__}: {e}")
            failures += 1
        else:
            print("  FAIL  ground through all 5 stories instead of stopping")
            failures += 1
finally:
    ex._split_anthology_stories = _real_split

print("\n--- end to end: what exit code does the shell actually get? ---")

rc, out = run_real_script(CREDIT, 400)
if rc == ex.EXIT_FATAL:
    print(f"  PASS  credit exhaustion exits {rc} (EXIT_FATAL) — the wrapper stops")
else:
    print(f"  FAIL  credit exhaustion exits {rc}, expected {ex.EXIT_FATAL}; "
          f"the wrapper would continue through the corpus")
    failures += 1
if "STOPPED" in out and "out of credits" in out:
    print("  PASS  and says plainly why it stopped")
else:
    print(f"  FAIL  unhelpful output:\n{out[-600:]}")
    failures += 1

rc, out = run_real_script("KEYBOARD", None)
if rc == ex.EXIT_INTERRUPTED:
    print(f"  PASS  Ctrl-C exits {rc} (EXIT_INTERRUPTED), no traceback")
else:
    print(f"  FAIL  Ctrl-C exits {rc}, expected {ex.EXIT_INTERRUPTED}")
    failures += 1
if "Traceback" not in out and "resume" in out:
    print("  PASS  and says how to resume instead of dumping a stack")
else:
    print(f"  FAIL  ugly interrupt output:\n{out[-500:]}")
    failures += 1

rc, out = run_real_script("Connection error.", None)
if rc == ex.EXIT_SOURCE_FAILED:
    print(f"  PASS  a network failure exits {rc} (EXIT_SOURCE_FAILED) — wrapper "
          f"counts it and carries on")
else:
    print(f"  FAIL  network failure exits {rc}, expected {ex.EXIT_SOURCE_FAILED}")
    failures += 1
if "STOPPED" not in out:
    print("  PASS  and does not claim the whole run is doomed")
else:
    print("  FAIL  treated a recoverable error as fatal")
    failures += 1

print()
if failures:
    print(f"=== {failures} FAILED ===")
    sys.exit(1)
print("=== ALL PASSED ===")
