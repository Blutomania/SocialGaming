"""
Extract mystery parts from local PDF files.
============================================

Slots into the existing extraction pipeline — same Claude prompts, same
output format as run_corpus_pipeline.py, same output directory.

Usage:
    # Single file
    python scripts/extract_from_pdfs.py mystery_database/new_sources/clue.pdf

    # All PDFs in a directory
    python scripts/extract_from_pdfs.py mystery_database/new_sources/

    # Explicit glob
    python scripts/extract_from_pdfs.py mystery_database/new_sources/*.pdf

    # Protocol and dry-run flags
    python scripts/extract_from_pdfs.py mystery_database/new_sources/ --protocol P1 --dry-run

Requires:
    pip install pypdf

API key: set ANTHROPIC_API_KEY in environment (or add to a .env file).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Ensure repo root is on path so we can import project modules
# ---------------------------------------------------------------------------
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from extraction_protocols import extraction_prompt, get_protocol, PROTOCOLS
except ImportError as e:
    sys.exit(f"ERROR: Could not import extraction_protocols — run from repo root.\n{e}")

try:
    import anthropic
except ImportError:
    sys.exit("ERROR: anthropic not installed — run: pip install anthropic")

try:
    import pypdf
except ImportError:
    sys.exit(
        "ERROR: pypdf not installed — run: pip install pypdf\n"
        "(pypdf is the modern replacement for PyPDF2)"
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DB_DIR       = "./mystery_database"
DEFAULT_PROTOCOL     = "P1"
DEFAULT_MODEL        = "claude-haiku-4-5-20251001"   # ~20x cheaper than Sonnet; good for P1
SONNET_MODEL         = "claude-sonnet-4-6"            # fallback if quality matters
DELAY_SECS           = 1.5    # pause between API calls
MAX_TEXT_CHARS       = 6000   # matches run_corpus_pipeline.py — novel-length sampling budget
RESOLUTION_END_CHARS = 3000   # chars sampled from end for --fill-resolution pass
MIN_TEXT_CHARS       = 200    # below this, a "story" is probably a mis-detected fragment

# Anthology mode (--anthology): unlike a novel, a short story has no slack to sample
# away — MAX_TEXT_CHARS' begin/middle/end sampling would cut most of a dense ~5-15
# page story into three disconnected chunks. Below this threshold, feed the whole
# story; only fall back to begin/middle/end sampling for an outlier long story.
ANTHOLOGY_FULLTEXT_THRESHOLD = 25000

# Many classic/Gutenberg-style mysteries open with license boilerplate, a
# title page, table of contents, and a dedication before the story starts —
# a "Characters of the Book" list often sits right before Chapter One and
# gets clipped by a flat text[:chunk] slice. Detect that marker near the
# start of the book and anchor + widen the beginning slice on it so both
# the cast list and the opening of the crime narrative survive sampling.
CAST_LIST_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:"
    r"cast of characters|characters (?:of|in) th(?:e|is) (?:book|story|play)|"
    r"dramatis personae|principal characters(?: in the book)?|"
    r"list of characters"
    r")[ \t]*:?[ \t]*$"
)
CAST_LIST_SEARCH_CHARS = 8000   # only look for the marker in early front matter
CAST_LIST_EXPANSION_CHARS = 3000   # extra budget granted to the beginning slice when found


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> tuple[str, str]:
    """Return (sampled_text, full_text) from a PDF.
    sampled_text: beginning+middle+end capped at MAX_TEXT_CHARS.
    full_text: complete extracted text (used for resolution-only pass)."""
    reader = pypdf.PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")

    full_text = "\n".join(pages).strip()

    if len(full_text) <= MAX_TEXT_CHARS:
        return full_text, full_text

    # Sample beginning + middle + end so Claude sees the full arc
    chunk = MAX_TEXT_CHARS // 3
    mid_start = (len(full_text) - chunk) // 2

    # If a cast-of-characters marker sits in the front matter, anchor the
    # beginning slice on it (skipping license text / title page / TOC /
    # dedication before it) and widen it so it also reaches past the cast
    # list into the opening of Chapter One, not just the list itself.
    # Never let it run into the middle slice's start.
    cast_match = CAST_LIST_PATTERN.search(full_text[:CAST_LIST_SEARCH_CHARS])
    if cast_match:
        beginning_start = cast_match.start()
        beginning_end   = min(beginning_start + chunk + CAST_LIST_EXPANSION_CHARS, mid_start)
        beginning = full_text[beginning_start:beginning_end]
    else:
        beginning = full_text[:chunk]

    middle = full_text[mid_start: mid_start + chunk]
    end    = full_text[-chunk:]
    sampled = f"{beginning}\n\n[... middle ...]\n\n{middle}\n\n[... end ...]\n\n{end}"
    return sampled, full_text


def _sample_text_bme(full_text: str, max_chars: int) -> str:
    """Generic begin+middle+end sampler for a single story's text (no
    cast-list anchoring — that heuristic is novel-front-matter-specific)."""
    if len(full_text) <= max_chars:
        return full_text
    chunk = max_chars // 3
    mid_start = (len(full_text) - chunk) // 2
    beginning = full_text[:chunk]
    middle = full_text[mid_start: mid_start + chunk]
    end = full_text[-chunk:]
    return f"{beginning}\n\n[... middle ...]\n\n{middle}\n\n[... end ...]\n\n{end}"


# ---------------------------------------------------------------------------
# Anthology splitting (--anthology)
# ---------------------------------------------------------------------------
#
# Many classic short-story anthologies format every story identically: an
# ALL-CAPS byline immediately followed by a title-cased title, at the very
# top of that story's first page — e.g.
#     EDWARD D. HOCH
#     Winter Run
# Detect that pattern per-page to find story boundaries, rather than trying
# to match a Contents-page listing against body text (title punctuation and
# capitalization frequently differ between the two).

_FRONT_MATTER_MARKER_RE = re.compile(r"(?im)^[ \t]*CONTENTS[ \t]*$")
_TOC_ENTRY_RE = re.compile(r"^(.{2,80}?)\s*[—–-]\s*(.{2,60})$")


def _is_caps_byline(line: str) -> bool:
    """True if `line` looks like an ALL-CAPS author byline (tolerating
    lowercase connector words like 'and' in multi-author bylines)."""
    line = line.strip()
    if not (3 <= len(line) <= 70):
        return False
    words = line.split()
    if not (2 <= len(words) <= 6):
        return False
    if any(ch.isdigit() for ch in line):
        return False
    letters = [c for c in line if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper_ratio >= 0.85


def _is_title_line(line: str) -> bool:
    """True if `line` looks like a title-cased story title (not itself
    all-caps, so it's distinguishable from a second byline-shaped line)."""
    line = line.strip()
    if not (2 <= len(line) <= 80):
        return False
    words = line.split()
    if not (1 <= len(words) <= 12):
        return False
    letters = [c for c in line if c.isalpha()]
    # A title with no alphabetic characters at all (e.g. "#8") can't be
    # judged "all-caps" one way or the other — skip that check rather than
    # rejecting it outright.
    if letters:
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio >= 0.85:
            return False
    # Titles are usually capitalized, but don't require an alphabetic first
    # character — some titles start with a digit or symbol (e.g. "#8").
    return not line[0].islower()


def _read_pdf_pages(pdf_path: Path) -> list[str]:
    reader = pypdf.PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


def _find_front_matter_end(pages: list[str], search_pages: int = 30) -> int:
    """Return the first page index safe to scan for story headings — the
    page after the last standalone 'CONTENTS' heading in the front matter
    (title/copyright/acknowledgments/contents pages routinely contain
    byline-shaped text of their own, e.g. an editor's name over the book
    title). Returns 0 if no Contents page is found."""
    last = -1
    for i, page_text in enumerate(pages[:search_pages]):
        if _FRONT_MATTER_MARKER_RE.search(page_text):
            last = i
    return last + 1 if last >= 0 else 0


def _detect_story_boundaries(pages: list[str]) -> list[int]:
    start = _find_front_matter_end(pages)
    boundaries = []
    for i in range(start, len(pages)):
        lines = [l.strip() for l in pages[i].split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        if _is_caps_byline(lines[0]) and _is_title_line(lines[1]):
            boundaries.append(i)
    return boundaries


def _split_anthology_stories(pdf_path: Path) -> list[dict]:
    """Split an anthology PDF into per-story dicts: index, title, author,
    start_page/end_page (0-indexed, inclusive), and text."""
    pages = _read_pdf_pages(pdf_path)
    boundaries = _detect_story_boundaries(pages)
    stories = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(pages)
        lines = [l.strip() for l in pages[start].split("\n") if l.strip()]
        author, title = lines[0], lines[1]
        text = "\n".join(pages[start:end]).strip()
        stories.append({
            "index": idx + 1,
            "title": title,
            "author": author,
            "start_page": start,
            "end_page": end - 1,
            "text": text,
        })
    return stories


def _count_toc_entries(full_text: str, search_chars: int = 20000) -> int:
    """Best-effort count of 'Title—Author' lines under the first Contents
    heading, for a sanity-check against the detected story count. Not used
    to source titles — only to flag a suspicious mismatch."""
    head = full_text[:search_chars]
    m = _FRONT_MATTER_MARKER_RE.search(head)
    if not m:
        return 0
    count = 0
    for line in head[m.end():].split("\n"):
        line = line.strip()
        if not line:
            if count > 0:
                break
            continue
        if _TOC_ENTRY_RE.match(line):
            count += 1
        elif count > 0:
            break
    return count


def extract_pdf_anthology(
    pdf_path: Path,
    client: "anthropic.Anthropic",
    protocol_ids: list[str],
    db_dir: Path,
    model: str = DEFAULT_MODEL,
    verbose: bool = True,
) -> tuple[int, int]:
    """Extract each detected short story in an anthology PDF as its own
    corpus source. Returns (success_count, failed_count)."""

    book_slug = _slug(pdf_path.stem)
    stories = _split_anthology_stories(pdf_path)

    if len(stories) < 2:
        print(f"  ERROR  {pdf_path.name} — detected {len(stories)} story heading(s); "
              f"this doesn't look like a multi-story anthology. Skipping.")
        return 0, 1

    if verbose:
        toc_count = _count_toc_entries("\n".join(_read_pdf_pages(pdf_path)))
        note = f" (Contents page lists ~{toc_count})" if toc_count else ""
        print(f"  Detected {len(stories)} stories in {pdf_path.name}{note}")
        if toc_count and abs(toc_count - len(stories)) > max(2, toc_count // 10):
            print(f"  WARNING: detected story count differs from the Contents count "
                  f"by more than 10% — verify the split (--dry-run) before trusting it.")

    success, failed = 0, 0
    for story in stories:
        title_slug = _slug(story["title"])[:40]
        out_path = db_dir / "extractions" / f"pdf_{book_slug[:30]}__story{story['index']:02d}_{title_slug}.json"

        if out_path.exists():
            if verbose:
                print(f"  SKIP  story {story['index']:02d}: {story['title']}  (already extracted)")
            success += 1
            continue

        text = story["text"]
        if len(text) < MIN_TEXT_CHARS:
            if verbose:
                print(f"  SKIP  story {story['index']:02d}: {story['title']}  — too short ({len(text)} chars)")
            continue

        sampled_text = (
            text if len(text) <= ANTHOLOGY_FULLTEXT_THRESHOLD
            else _sample_text_bme(text, ANTHOLOGY_FULLTEXT_THRESHOLD)
        )

        if verbose:
            note = "full text" if len(sampled_text) == len(text) else f"sampled from {len(text):,} chars"
            print(f"  READ  story {story['index']:02d}: {story['title']} — {story['author']}  ({note})")

        merged: dict = {}
        story_failed = False
        for pid in protocol_ids:
            prompt = extraction_prompt(pid, sampled_text, max_text_chars=len(sampled_text))
            try:
                message = client.messages.create(
                    model=model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                )
            except Exception as e:
                print(f"  ERROR calling Claude for story {story['index']:02d}: {e}")
                story_failed = True
                break

            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.rsplit("```", 1)[0]

            try:
                extracted = json.loads(raw.strip())
            except json.JSONDecodeError:
                protocol = get_protocol(pid)
                extracted = {
                    p.json_key: {"value": None, "confidence": "low", "quote": None}
                    for p in protocol.parts
                }
            merged.update(extracted)

        if story_failed:
            failed += 1
            continue

        merged["_meta"] = {
            "source": str(pdf_path),
            "filename": pdf_path.name,
            "text_len": len(sampled_text),
            "protocols": protocol_ids,
            "title": story["title"],
            "author": story["author"],
            "anthology_title": pdf_path.stem,
            "story_index": story["index"],
            "story_count": len(stories),
        }

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(merged, f, indent=2)

        if verbose:
            print(f"        saved -> {out_path.name}")
        success += 1
        time.sleep(DELAY_SECS)

    return success, failed


def fill_resolution(
    out_path: Path,
    full_text: str,
    client: "anthropic.Anthropic",
    model: str,
    verbose: bool = True,
) -> None:
    """If the saved extraction has resolution: null, make a targeted second call
    using only the final RESOLUTION_END_CHARS of the book."""
    with open(out_path) as f:
        data = json.load(f)

    resolution = data.get("resolution", {})
    if resolution.get("confidence", "low") != "low":
        if verbose:
            print(f"        resolution already present — skipping fill pass")
        return

    end_chunk = full_text[-RESOLUTION_END_CHARS:]
    prompt = (
        "You are extracting structured data from the ending of a mystery novel.\n\n"
        "Read the following excerpt (the final pages of the book) and identify:\n"
        "- resolution: how the mystery is finally solved and by whom\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"resolution": {"value": "...", "confidence": "high|medium|low", "quote": "..."}}\n\n'
        "If the resolution is not present in this excerpt, set value to null, "
        'confidence to "low", and quote to null.\n\n'
        f"EXCERPT:\n{end_chunk}"
    )

    try:
        message = client.messages.create(
            model      = model,
            max_tokens = 500,
            messages   = [{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"        ERROR in resolution fill pass: {e}")
        return

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]

    try:
        patch = json.loads(raw.strip())
        new_res = patch.get("resolution", {})
        if new_res.get("confidence", "low") != "low":
            data["resolution"] = new_res
            data["_meta"]["resolution_filled"] = True
            with open(out_path, "w") as f:
                json.dump(data, f, indent=2)
            if verbose:
                print(f"        resolution filled (confidence: {new_res['confidence']})")
        else:
            if verbose:
                print(f"        resolution still null after fill pass — not in final pages")
    except json.JSONDecodeError:
        print(f"        ERROR: could not parse resolution fill response")


# ---------------------------------------------------------------------------
# Slug helper for output filename
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:60]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_pdf(
    pdf_path: Path,
    client: "anthropic.Anthropic",
    protocol_ids: list[str],
    db_dir: Path,
    model: str = DEFAULT_MODEL,
    verbose: bool = True,
) -> tuple[Path | None, str]:
    """Extract a single PDF and save results.
    Returns (output_path, full_text). full_text is needed for --fill-resolution."""

    slug      = _slug(pdf_path.stem)
    out_path  = db_dir / "extractions" / f"pdf_{slug}.json"

    if out_path.exists():
        if verbose:
            print(f"  SKIP  {pdf_path.name}  (already extracted → {out_path.name})")
        # Still need full_text for a potential fill-resolution pass
        try:
            _, full_text = extract_text_from_pdf(pdf_path)
        except Exception:
            full_text = ""
        return out_path, full_text

    if verbose:
        print(f"  READ  {pdf_path.name}")

    try:
        text, full_text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        print(f"  ERROR reading PDF: {e}")
        return None, ""

    if len(text.strip()) < MIN_TEXT_CHARS:
        print(f"  SKIP  {pdf_path.name}  — too short ({len(text)} chars), skipping")
        return None, ""

    if verbose:
        print(f"        {len(text):,} chars extracted from PDF")

    merged: dict = {}
    for pid in protocol_ids:
        # `text` has already been sampled (and possibly cast-list-expanded)
        # by extract_text_from_pdf; pass its own length through so
        # extraction_prompt's internal _sample_text doesn't re-truncate it.
        prompt = extraction_prompt(pid, text, max_text_chars=len(text))

        try:
            message = client.messages.create(
                model      = model,
                max_tokens = 1000,
                messages   = [{"role": "user", "content": prompt}],
            )
        except Exception as e:
            print(f"  ERROR calling Claude: {e}")
            return None, ""

        raw = message.content[0].text.strip()

        # Strip markdown fences if Claude added them
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0]

        try:
            extracted = json.loads(raw.strip())
        except json.JSONDecodeError:
            protocol = get_protocol(pid)
            extracted = {
                p.json_key: {"value": None, "confidence": "low", "quote": None}
                for p in protocol.parts
            }

        merged.update(extracted)

    merged["_meta"] = {
        "source":    str(pdf_path),
        "filename":  pdf_path.name,
        "text_len":  len(text),
        "protocols": protocol_ids,
        "title":     pdf_path.stem,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)

    if verbose:
        print(f"        saved → {out_path}")

    return out_path, full_text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _collect_pdfs(sources: list[str]) -> list[Path]:
    """Expand paths/directories into a sorted list of PDF files."""
    pdfs = []
    for src in sources:
        p = Path(src)
        if p.is_dir():
            pdfs.extend(sorted(p.glob("**/*.pdf")))
        elif p.suffix.lower() == ".pdf" and p.exists():
            pdfs.append(p)
        else:
            # Treat as glob
            import glob
            matched = sorted(Path(m) for m in glob.glob(src))
            pdfs.extend(m for m in matched if m.suffix.lower() == ".pdf")
    return list(dict.fromkeys(pdfs))  # deduplicate, preserve order


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract mystery parts from local PDF files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "sources", nargs="+", metavar="PATH",
        help="PDF file(s) or directory containing PDFs",
    )
    parser.add_argument(
        "--protocol", default=DEFAULT_PROTOCOL,
        choices=list(PROTOCOLS.keys()),
        help=f"Extraction depth (default: {DEFAULT_PROTOCOL})",
    )
    parser.add_argument(
        "--db-dir", default=DEFAULT_DB_DIR, metavar="DIR",
        help=f"Mystery database directory (default: {DEFAULT_DB_DIR})",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Claude model to use (default: {DEFAULT_MODEL}). Use '{SONNET_MODEL}' for higher quality.",
    )
    parser.add_argument(
        "--fill-resolution", action="store_true",
        help="After extraction, make a targeted second call on the final pages for any "
             "file where resolution confidence is low. Adds ~$0.001 per affected file.",
    )
    parser.add_argument(
        "--anthology", action="store_true",
        help="Treat each PDF as a short-story anthology rather than a single novel: "
             "detect per-story boundaries (ALL-CAPS byline + title at the top of each "
             "story's first page) and extract every story as its own corpus source, "
             "using each story's full text rather than begin/middle/end sampling. "
             "Use --dry-run first to review the detected split before spending API calls.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List PDFs (and, with --anthology, detected per-story splits) that would "
             "be processed without making API calls",
    )

    args = parser.parse_args()

    db_dir = Path(args.db_dir)
    protocol_ids = args.protocol.replace("P", " P").split()  # "P1P2" → ["P1","P2"]

    pdfs = _collect_pdfs(args.sources)

    if not pdfs:
        sys.exit("No PDF files found at the given path(s).")

    print(f"\nFound {len(pdfs)} PDF(s)  |  protocol: {args.protocol}\n")
    for p in pdfs:
        print(f"  {p}")

    if args.dry_run:
        print("\nDry run — no API calls made.")
        if args.anthology:
            for p in pdfs:
                stories = _split_anthology_stories(p)
                print(f"\n{p.name}: {len(stories)} stories detected")
                if len(stories) < 2:
                    print("  WARNING: fewer than 2 stories detected — this may not "
                          "actually be a multi-story anthology, or the heading "
                          "pattern didn't match this PDF's formatting.")
                for s in stories:
                    print(f"  [{s['index']:02d}] {s['title']} — {s['author']}  "
                          f"(pages {s['start_page']+1}-{s['end_page']+1}, {len(s['text']):,} chars)")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set in environment.")

    client = anthropic.Anthropic(api_key=api_key)

    success, failed = 0, 0
    for i, pdf_path in enumerate(pdfs):
        print(f"\n[{i+1}/{len(pdfs)}]")

        if args.anthology:
            s, f_ = extract_pdf_anthology(pdf_path, client, protocol_ids, db_dir, model=args.model)
            success += s
            failed += f_
            continue

        out_path, full_text = extract_pdf(pdf_path, client, protocol_ids, db_dir, model=args.model)
        if out_path is None:
            failed += 1
        else:
            success += 1
            if args.fill_resolution and full_text:
                fill_resolution(out_path, full_text, client, model=args.model)
        if i < len(pdfs) - 1:
            time.sleep(DELAY_SECS)

    print(f"\n=== Done ===")
    print(f"  Processed : {success}")
    print(f"  Failed    : {failed}")
    print(f"  Output    : {db_dir}/extractions/")


if __name__ == "__main__":
    main()
