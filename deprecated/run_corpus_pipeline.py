"""
Run Corpus Pipeline
===================

End-to-end pipeline: load the mystery-crime-books corpus, extract structured
parts with Claude, and store results in the mystery database.

This script is designed to be:
  - RESUMABLE: tracks progress in a checkpoint file so a crash or interruption
    does not require restarting from row 0
  - COST-AWARE: prints an estimate before starting and asks for confirmation
  - CONFIGURABLE: start/end row, protocol level, batch size, and dry-run mode
    are all CLI flags

Usage:

  # Dry run — prints stats and cost estimate, does nothing
  python run_corpus_pipeline.py --dry-run

  # Full run at P1+P2 (recommended default)
  python run_corpus_pipeline.py

  # Only rows 0-49 (first 50 usable rows)
  python run_corpus_pipeline.py --start 0 --end 50

  # Resume from where a previous run left off (reads checkpoint automatically)
  python run_corpus_pipeline.py --resume

  # P1 only (cheapest, fastest — one Claude call per row)
  python run_corpus_pipeline.py --protocol P1

  # P1+P2+P3 (deep extraction — two Claude calls per row)
  python run_corpus_pipeline.py --protocol P1P2P3

Requirements:
  - ANTHROPIC_API_KEY set in environment or .env file
  - mystery-crime-books repo cloned at ./mystery-crime-books
    (or pass --corpus-dir /path/to/clone)
  - pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from corpus_loader import CorpusLoader, row_to_metadata
from mystery_data_acquisition import MysteryProcessor, MysteryDatabase
from extraction_protocols import get_protocol, extraction_prompt, PROTOCOLS


# ============================================================================
# CONFIGURATION DEFAULTS
# ============================================================================

DEFAULT_CORPUS_DIR   = "./mystery-crime-books"
DEFAULT_DB_DIR       = "./mystery_database"
DEFAULT_CHECKPOINT   = "./pipeline_checkpoint.json"
DEFAULT_PROTOCOL     = "P1P2"          # P1, P2, P1P2, P1P2P3
DEFAULT_BATCH_SIZE   = 10
DEFAULT_DELAY_SECS   = 1.0             # pause between API calls (rate-limit safety)

# Approximate cost per 1k tokens (Claude Sonnet, as of early 2026)
# Used only for the pre-run estimate — not charged by this script.
APPROX_INPUT_TOKENS_PER_ROW  = 2_000  # ~6k chars source + prompt overhead
APPROX_OUTPUT_TOKENS_PER_ROW = 800
COST_PER_1K_INPUT  = 0.003            # USD
COST_PER_1K_OUTPUT = 0.015            # USD


# ============================================================================
# CHECKPOINT
# ============================================================================

def load_checkpoint(path: str) -> dict:
    if Path(path).exists():
        with open(path) as f:
            return json.load(f)
    return {"completed_indices": [], "failed_indices": [], "last_corpus_index": -1}


def save_checkpoint(path: str, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


# ============================================================================
# COST ESTIMATE
# ============================================================================

def print_cost_estimate(usable_rows: int, protocol: str, calls_per_row: int) -> None:
    total_calls  = usable_rows * calls_per_row
    input_cost   = (APPROX_INPUT_TOKENS_PER_ROW  / 1000) * COST_PER_1K_INPUT  * total_calls
    output_cost  = (APPROX_OUTPUT_TOKENS_PER_ROW / 1000) * COST_PER_1K_OUTPUT * total_calls
    total_cost   = input_cost + output_cost

    print("\n=== Pre-run Estimate ===")
    print(f"  Usable rows    : {usable_rows}")
    print(f"  Protocol       : {protocol}")
    print(f"  API calls/row  : {calls_per_row}")
    print(f"  Total API calls: {total_calls:,}")
    print(f"  Estimated cost : ~${total_cost:.2f} USD  (rough — actual varies by text length)")
    print(f"  Estimated time : ~{total_calls * (DEFAULT_DELAY_SECS + 3) / 60:.0f} min")
    print()


# ============================================================================
# EXTRACTION
# ============================================================================

def calls_for_protocol(protocol_str: str) -> list[str]:
    """
    Map protocol string (e.g. "P1P2") to an ordered list of protocol IDs
    that will each generate one Claude call per row.

    P1      → ["P1"]
    P2      → ["P2"]          (not recommended alone — P1 must exist)
    P1P2    → ["P1", "P2"]
    P1P2P3  → ["P1", "P2", "P3"]
    """
    mapping = {
        "P1":     ["P1"],
        "P2":     ["P2"],
        "P1P2":   ["P1", "P2"],
        "P1P2P3": ["P1", "P2", "P3"],
    }
    if protocol_str not in mapping:
        raise ValueError(
            f"Unknown protocol '{protocol_str}'. "
            f"Valid options: {list(mapping.keys())}"
        )
    return mapping[protocol_str]


def extract_row(
    processor: MysteryProcessor,
    row: dict,
    protocol_ids: list[str],
) -> dict:
    """
    Run Claude extraction on one corpus row across one or more protocols.

    Returns a merged extraction result dict keyed by json_key, plus
    top-level fields: url, corpus_index, text_len.
    """
    text     = row["text"]
    metadata = row_to_metadata(row)

    merged_extraction: dict = {}

    for pid in protocol_ids:
        protocol = get_protocol(pid)
        prompt   = extraction_prompt(pid, text, max_text_chars=6000)

        message  = processor.client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 2000,
            messages   = [{"role": "user", "content": prompt}],
        )
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
            extracted = {p.json_key: {"value": None, "confidence": "low", "quote": None}
                         for p in protocol.parts}

        merged_extraction.update(extracted)

    merged_extraction["_meta"] = {
        "url":          row["url"],
        "corpus_index": row["index"],
        "text_len":     row["text_len"],
        "title":        metadata["title"],
        "protocols":    protocol_ids,
    }

    return merged_extraction


# ============================================================================
# STORAGE: save raw extraction alongside the MysteryDatabase
# ============================================================================

def save_extraction(extraction: dict, db_dir: str) -> str:
    """
    Save raw protocol extraction JSON.
    These are separate from the MysteryScenario objects — they are the
    intermediate representation that can be promoted to scenarios later.

    Returns the saved file path.
    """
    extractions_dir = Path(db_dir) / "extractions"
    extractions_dir.mkdir(parents=True, exist_ok=True)

    idx   = extraction["_meta"]["corpus_index"]
    title = extraction["_meta"]["title"].replace(" ", "_").replace("/", "_")[:40]
    fname = f"{idx:04d}_{title}.json"
    fpath = extractions_dir / fname

    with open(fpath, "w") as f:
        json.dump(extraction, f, indent=2)

    return str(fpath)


def build_extraction_index(db_dir: str) -> None:
    """
    Rebuild the extraction index from all saved extraction files.
    Writes mystery_database/extractions/index.json.
    """
    extractions_dir = Path(db_dir) / "extractions"
    index = []

    for fpath in sorted(extractions_dir.glob("*.json")):
        if fpath.name == "index.json":
            continue
        try:
            with open(fpath) as f:
                data = json.load(f)
            meta = data.get("_meta", {})
            index.append({
                "file":         fpath.name,
                "corpus_index": meta.get("corpus_index"),
                "url":          meta.get("url"),
                "title":        meta.get("title"),
                "protocols":    meta.get("protocols"),
                "text_len":     meta.get("text_len"),
            })
        except Exception:
            pass

    index_path = extractions_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"  Extraction index updated: {len(index)} entries → {index_path}")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_pipeline(args: argparse.Namespace) -> None:
    # 1. Load corpus
    loader = CorpusLoader(args.corpus_dir)
    loader.print_stats()

    protocol_ids  = calls_for_protocol(args.protocol)
    calls_per_row = len(protocol_ids)

    # 2. Load checkpoint (for --resume)
    checkpoint = load_checkpoint(args.checkpoint)
    done_set   = set(checkpoint["completed_indices"])
    failed_set = set(checkpoint["failed_indices"])

    # 3. Determine row range
    start = args.start
    end   = args.end if args.end is not None else None

    usable = loader.usable_rows()
    print_cost_estimate(usable, args.protocol, calls_per_row)

    if args.dry_run:
        print("Dry run complete. No API calls made.")
        return

    # 4. Confirm with user (skip if --yes)
    if not args.yes:
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    # 5. Init processor and database
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    processor = MysteryProcessor(api_key=api_key)
    database  = MysteryDatabase(args.db_dir)

    Path(args.db_dir).mkdir(parents=True, exist_ok=True)

    # 6. Run
    success_count = 0
    fail_count    = 0

    rows = list(loader.iter_rows(start=start, end=end))
    total = len(rows)

    print(f"\nProcessing {total} rows with protocols {protocol_ids}...\n")

    for i, row in enumerate(rows):
        idx = row["index"]

        if idx in done_set:
            print(f"  [{i+1}/{total}] #{idx} — already done, skipping")
            continue

        print(f"  [{i+1}/{total}] #{idx}  {row['url'][:70]}")
        print(f"         length: {row['text_len']:,} chars")

        try:
            extraction = extract_row(processor, row, protocol_ids)
            fpath      = save_extraction(extraction, args.db_dir)
            print(f"         saved : {fpath}")

            # Mark complete
            checkpoint["completed_indices"].append(idx)
            checkpoint["last_corpus_index"] = idx
            if idx in failed_set:
                checkpoint["failed_indices"].remove(idx)
            save_checkpoint(args.checkpoint, checkpoint)

            success_count += 1

        except Exception as e:
            print(f"         ERROR : {e}")
            fail_count += 1
            if idx not in failed_set:
                checkpoint["failed_indices"].append(idx)
            save_checkpoint(args.checkpoint, checkpoint)

        # Rate-limit pause
        if i < total - 1:
            time.sleep(args.delay)

    # 7. Rebuild extraction index
    print("\nRebuilding extraction index...")
    build_extraction_index(args.db_dir)

    # 8. Summary
    print(f"\n=== Pipeline Complete ===")
    print(f"  Succeeded : {success_count}")
    print(f"  Failed    : {fail_count}")
    print(f"  Checkpoint: {args.checkpoint}")
    print(f"  Database  : {args.db_dir}/extractions/")


# ============================================================================
# CLI
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run the mystery corpus extraction pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--corpus-dir", default=DEFAULT_CORPUS_DIR,
        help=f"Path to cloned mystery-crime-books repo (default: {DEFAULT_CORPUS_DIR})",
    )
    p.add_argument(
        "--db-dir", default=DEFAULT_DB_DIR,
        help=f"Path to mystery database output directory (default: {DEFAULT_DB_DIR})",
    )
    p.add_argument(
        "--checkpoint", default=DEFAULT_CHECKPOINT,
        help=f"Path to checkpoint file (default: {DEFAULT_CHECKPOINT})",
    )
    p.add_argument(
        "--protocol", default=DEFAULT_PROTOCOL,
        choices=["P1", "P2", "P1P2", "P1P2P3"],
        help=f"Extraction protocol level (default: {DEFAULT_PROTOCOL})",
    )
    p.add_argument(
        "--start", type=int, default=0,
        help="First corpus row index to process (default: 0)",
    )
    p.add_argument(
        "--end", type=int, default=None,
        help="Last corpus row index (exclusive). Default: process all rows.",
    )
    p.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help=f"Rows per progress checkpoint (default: {DEFAULT_BATCH_SIZE})",
    )
    p.add_argument(
        "--delay", type=float, default=DEFAULT_DELAY_SECS,
        help=f"Seconds to wait between API calls (default: {DEFAULT_DELAY_SECS})",
    )
    p.add_argument(
        "--resume", action="store_true",
        help="Skip rows already recorded in checkpoint file",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print stats and cost estimate only. No API calls.",
    )
    p.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt",
    )
    return p


if __name__ == "__main__":
    parser = build_parser()
    args   = parser.parse_args()
    run_pipeline(args)
