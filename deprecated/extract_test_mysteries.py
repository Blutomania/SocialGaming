"""
Extract Test Mysteries
======================

Runs P1+P2 extraction against the 6 built-in test mysteries (A–F) using
Claude, as a surrogate for the full HuggingFace corpus pipeline.

This validates the extraction pipeline end-to-end without needing the
mystery-crime-books dataset.

Usage:
    python extract_test_mysteries.py
    python extract_test_mysteries.py --protocol P1
    python extract_test_mysteries.py --dry-run
    python extract_test_mysteries.py --ids A B C
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from test_mysteries import TEST_MYSTERIES, get_all_ids
from extraction_protocols import combined_prompt, extraction_prompt, get_protocol

load_dotenv()

OUTPUT_DIR = Path("./mystery_database/extractions")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_source_text(mystery: dict) -> str:
    """
    Construct a rich source text from a test mystery's metadata.
    This stands in for the raw novel text the corpus pipeline would use.
    """
    parts_lines = "\n".join(
        f"  - {pt}" for pt in mystery["part_types"]
    )
    return f"""Title: {mystery['title']}
Crime Type: {mystery['crime_type']}
Setting: {mystery['setting_location']} ({mystery['setting_time_period']})
Environment: {mystery['setting_environment']}
Genres: {', '.join(mystery['genre_tags'])}

Summary:
{mystery['description']}

Structural Elements Present:
{parts_lines}
"""


INGRESS_TOKEN_FILE = "/home/claude/.claude/remote/.session_ingress_token"
API_URL = "https://api.anthropic.com/v1/messages"


def _get_token(api_key: str | None) -> tuple[str, str]:
    """Return (auth_header_name, auth_header_value) for API calls."""
    if api_key:
        return "x-api-key", api_key
    if os.path.exists(INGRESS_TOKEN_FILE):
        token = open(INGRESS_TOKEN_FILE).read().strip()
        return "Authorization", f"Bearer {token}"
    raise ValueError("No API key found. Set ANTHROPIC_API_KEY or ensure ingress token exists.")


def call_claude(prompt: str, auth: tuple[str, str]) -> dict:
    """Make a single Claude API call. Returns {text, input_tokens, output_tokens}."""
    header_name, header_value = auth
    resp = requests.post(
        API_URL,
        headers={
            header_name: header_value,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["content"][0]["text"],
        "input_tokens": data["usage"]["input_tokens"],
        "output_tokens": data["usage"]["output_tokens"],
    }


def extract_mystery(
    auth: tuple[str, str],
    mystery_id: str,
    mystery: dict,
    protocol_ids: list[str],
    dry_run: bool = False,
) -> dict:
    """Run extraction for one mystery, return the structured result."""
    source_text = build_source_text(mystery)

    if len(protocol_ids) > 1:
        prompt = combined_prompt(protocol_ids, source_text)
    else:
        prompt = extraction_prompt(protocol_ids[0], source_text)

    print(f"  [{mystery_id}] {mystery['title']}")
    print(f"       protocol: {'+'.join(protocol_ids)}  |  source chars: {len(source_text)}")

    if dry_run:
        print(f"       [DRY RUN — skipping API call]")
        return {"mystery_id": mystery_id, "dry_run": True}

    result = call_claude(prompt, auth)
    raw_json = result["text"].strip()

    # Strip markdown code fences if present
    if raw_json.startswith("```"):
        lines = raw_json.splitlines()
        raw_json = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    extracted = json.loads(raw_json)

    return {
        "mystery_id": mystery_id,
        "title": mystery["title"],
        "protocols": protocol_ids,
        "source_text": source_text,
        "extracted": extracted,
        "usage": {
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        },
    }


def save_result(result: dict) -> Path:
    mid = result["mystery_id"]
    out_path = OUTPUT_DIR / f"test_{mid.lower()}_p1p2.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Extract P1+P2 from test mysteries")
    parser.add_argument("--protocol", default="P1P2",
                        choices=["P1", "P2", "P1P2", "P1P2P3"],
                        help="Extraction depth (default: P1P2)")
    parser.add_argument("--ids", nargs="+", metavar="ID",
                        help="Subset of mystery IDs to process (e.g. A B C)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts but skip API calls")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between API calls (default: 1.0)")
    args = parser.parse_args()

    protocol_ids = [c for c in args.protocol]  # "P1P2" → ["P", "1", "P", "2"] — wrong
    # Fix: split on P
    protocol_ids = ["P" + c for c in args.protocol.split("P") if c]

    target_ids = args.ids if args.ids else get_all_ids()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    auth = None
    if not args.dry_run:
        try:
            auth = _get_token(api_key)
        except ValueError as e:
            print(f"ERROR: {e}")
            return

    print(f"\n=== Extracting {len(target_ids)} test mysteries | protocol: {'+'.join(protocol_ids)} ===\n")

    total_input = 0
    total_output = 0
    saved_paths = []

    for i, mid in enumerate(target_ids):
        if mid not in TEST_MYSTERIES:
            print(f"  [{mid}] UNKNOWN — skipping")
            continue

        mystery = TEST_MYSTERIES[mid]
        try:
            result = extract_mystery(auth, mid, mystery, protocol_ids, dry_run=args.dry_run)
            if not args.dry_run:
                path = save_result(result)
                saved_paths.append(path)
                usage = result.get("usage", {})
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)
                print(f"       saved → {path}")
                print(f"       tokens: {usage.get('input_tokens')} in / {usage.get('output_tokens')} out")
        except Exception as e:
            print(f"  [{mid}] ERROR: {e}")

        if i < len(target_ids) - 1 and not args.dry_run:
            time.sleep(args.delay)

    print(f"\n=== Done ===")
    if not args.dry_run:
        print(f"Total tokens: {total_input} in / {total_output} out")
        print(f"Files written: {len(saved_paths)}")
        for p in saved_paths:
            print(f"  {p}")


if __name__ == "__main__":
    main()
