"""
Choose Your Mystery - CLI
==========================

Entry point that ties together:
  1. Part sampling (part_registry.py)       — cheap, zero API calls
  2. Pre-generation gate (check_parts)      — catch weak parts before Claude
  3. Mystery generation (mystery_generator) — single Claude call
  4. Post-generation check (check_mystery)  — validate before player sees it
  5. Save / display

Usage
-----
  python cli.py generate "A murder on a Mars colony" --players 4
  python cli.py generate "Art theft in Renaissance Venice" --players 5 --save
  python cli.py validate path/to/mystery.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

from coherence_validator import (
    Issue,
    check_mystery,
    check_parts,
    format_report,
)
from mystery_generator import MysteryGenerator
from part_registry import resample_part, sample_parts


# ============================================================================
# CONSTANTS
# ============================================================================

MAX_PART_RETRIES = 3   # how many times to re-sample a failing part before giving up
MAX_GEN_RETRIES  = 2   # how many generation attempts before aborting


# ============================================================================
# PRE-GENERATION GATE
# ============================================================================

def _parts_to_flat_list(parts: Dict) -> List[Dict]:
    """Flatten the sample_parts() dict into a list for check_parts()."""
    flat = [parts["crime"], parts["victim"]]
    flat.extend(parts["suspects"])
    flat.extend(parts["witnesses"])
    flat.extend(parts["evidence"])
    return flat


def _run_parts_gate(parts: Dict, verbose: bool = True) -> Dict:
    """
    Run check_parts() on the sampled parts dict.
    For each BLOCKING issue, attempt to resample the offending part up to
    MAX_PART_RETRIES times.  Returns the (possibly repaired) parts dict.

    This is the pre-generation gate — no Claude tokens spent yet.
    """
    for attempt in range(MAX_PART_RETRIES):
        flat = _parts_to_flat_list(parts)
        issues = check_parts(flat)

        if not issues:
            if verbose and attempt > 0:
                print(f"  Parts gate: PASS after {attempt} resample(s).")
            elif verbose:
                print("  Parts gate: PASS on first sample.")
            return parts

        if verbose:
            print(f"\n  Parts gate attempt {attempt + 1}: "
                  f"{len(issues)} issue(s) found — resampling ...")
            for issue in issues:
                print(f"    [{issue.severity}] {issue.message}")
                print(f"    Hint: {issue.repair_hint}")

        # Resample each failing part
        for issue in issues:
            hint = issue.repair_hint.lower()
            if "part_type='suspect'" in hint or "part_type=\"suspect\"" in hint:
                existing_names = [s.get("name") for s in parts["suspects"]]
                fresh = resample_part("suspect", exclude_names=existing_names)
                if fresh:
                    # Replace the first suspect that matches the failing name
                    # (best-effort: swap any suspect if name not found)
                    for i, s in enumerate(parts["suspects"]):
                        if s.get("name") == _extract_name_from_issue(issue) or i == 0:
                            parts["suspects"][i] = fresh
                            break

            elif "part_type='witness'" in hint or "part_type=\"witness\"" in hint:
                fresh = resample_part("witness")
                if fresh and parts["witnesses"]:
                    parts["witnesses"][0] = fresh

            elif "part_type='evidence'" in hint or "part_type=\"evidence\"" in hint:
                fresh = resample_part("evidence")
                if fresh:
                    # Replace the first offending evidence item
                    failing_name = _extract_name_from_issue(issue)
                    for i, e in enumerate(parts["evidence"]):
                        if e.get("name") == failing_name or i == 0:
                            fresh["id"] = parts["evidence"][i].get("id")
                            parts["evidence"][i] = fresh
                            break

            elif "part_type='crime'" in hint or "part_type=\"crime\"" in hint:
                fresh = resample_part("crime")
                if fresh:
                    parts["crime"] = fresh

    # Final check after all retries
    flat = _parts_to_flat_list(parts)
    remaining = check_parts(flat)
    if remaining and verbose:
        print(f"\n  Parts gate: {len(remaining)} issue(s) remain after "
              f"{MAX_PART_RETRIES} retries.  Proceeding anyway — "
              "post-generation validator will catch any problems.")
    return parts


def _extract_name_from_issue(issue: Issue) -> Optional[str]:
    """Pull the part name from an issue message (best-effort)."""
    import re
    m = re.search(r"'([^']+)'", issue.message)
    return m.group(1) if m else None


# ============================================================================
# GENERATION PROMPT ENRICHMENT
# ============================================================================

def _build_parts_context(parts: Dict) -> str:
    """
    Render sampled parts as concrete examples for the generation prompt.
    This tightens Claude's output so the post-generation check passes first time.

    Includes explicit good/bad examples for alibi and secret depth.
    """
    lines = []
    lines.append("SAMPLED PARTS — use these as the concrete depth standard:")
    lines.append("")

    # Crime anchor
    c = parts["crime"]
    lines.append(f"Crime anchor: {c.get('what_happened', '')}")
    lines.append("")

    # Victim context
    v = parts["victim"]
    lines.append(f"Victim context:")
    lines.append(f"  occupation: {v.get('occupation', '')}")
    lines.append(f"  personality: {v.get('personality', '')}")
    lines.append(f"  secrets: {v.get('secrets', '')}")
    lines.append("")

    # Suspect standard
    lines.append("Suspect depth standard (every suspect must match this quality):")
    for s in parts["suspects"][:2]:
        lines.append(f"  [{s.get('archetype', 'suspect')}]")
        lines.append(f"    motive : {s.get('motive', '')}")
        lines.append(f"    alibi  : {s.get('alibi', '')}")
        lines.append(f"    secrets: {s.get('secrets', '')}")
    lines.append("")

    lines.append("ALIBI QUALITY GUIDE:")
    lines.append("  GOOD: 'Claims she was playing whist with the vicar until eleven — "
                 "the vicar's wife recalls her leaving before the clock struck.'")
    lines.append("  BAD : 'Was at home.' / 'Out.' / '—'")
    lines.append("")
    lines.append("SECRET QUALITY GUIDE:")
    lines.append("  GOOD: 'He had purchased the poison from a back-street chemist under "
                 "a false name three days before the murder.'")
    lines.append("  BAD : 'Has a dark past.' / 'Hides something.' / '—'")
    lines.append("")

    # Evidence variety standard
    lines.append("Evidence variety required: mix physical, testimonial, and documentary.")
    lines.append("Red herrings MUST be physical or documentary (not testimonial-only).")
    lines.append("Every evidence description must be ≥40 chars and specific enough to reason about.")

    return "\n".join(lines)


# ============================================================================
# COMMANDS
# ============================================================================

def cmd_generate(prompt: str, num_players: int, save: bool, verbose: bool) -> None:
    """Generate a mystery, validate it, optionally save it."""

    print(f"\n{'='*60}")
    print(f"Generating: {prompt}")
    print(f"Players   : {num_players}")
    print(f"{'='*60}\n")

    # Check API key early
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    # ── Step 1: sample parts (zero API cost) ────────────────────────────
    n_suspects  = max(2, num_players - 1)
    n_witnesses = 1
    print("Step 1: Sampling parts from registry ...")
    parts = sample_parts(n_suspects=n_suspects, n_witnesses=n_witnesses)

    # ── Step 2: pre-generation gate ──────────────────────────────────────
    print("Step 2: Running pre-generation parts gate ...")
    parts = _run_parts_gate(parts, verbose=verbose)

    # ── Step 3: build enriched context and generate ──────────────────────
    parts_context = _build_parts_context(parts)

    generator = MysteryGenerator()

    mystery: Optional[Dict] = None
    for gen_attempt in range(1, MAX_GEN_RETRIES + 1):
        print(f"\nStep 3: Calling Claude (attempt {gen_attempt}/{MAX_GEN_RETRIES}) ...")

        # Inject parts context into the generator prompt
        original_prompt_builder = generator._generate_with_claude

        def patched_generate(**kwargs):
            # Prepend parts context to the user prompt so Claude sees the standard
            kwargs["user_prompt"] = (
                kwargs.get("user_prompt", "") +
                "\n\n" + parts_context
            )
            return original_prompt_builder(**kwargs)

        try:
            mystery = generator.generate_mystery(
                user_prompt=prompt,
                num_players=num_players,
            )
        except Exception as e:
            print(f"  Generation error: {e}")
            if gen_attempt == MAX_GEN_RETRIES:
                print("  All generation attempts failed. Exiting.")
                sys.exit(1)
            continue

        # ── Step 4: post-generation coherence check ──────────────────────
        print("Step 4: Running post-generation coherence check ...")
        issues = check_mystery(mystery)
        blocking = [i for i in issues if i.severity == "BLOCKING"]

        if verbose or issues:
            print(format_report(issues, f"Coherence report — attempt {gen_attempt}"))

        if not blocking:
            print("  Post-gen check: PASS — mystery is coherent.")
            break
        else:
            print(f"  Post-gen check: {len(blocking)} BLOCKING issue(s). "
                  f"{'Retrying ...' if gen_attempt < MAX_GEN_RETRIES else 'Proceeding with warnings.'}")
            if gen_attempt == MAX_GEN_RETRIES:
                # Don't silently deliver a broken mystery
                print("\nWARNING: Mystery has unresolved BLOCKING issues.")
                print("Review the report above before using in gameplay.")

    if mystery is None:
        print("Failed to generate a mystery. Exiting.")
        sys.exit(1)

    # ── Step 5: display summary ──────────────────────────────────────────
    _display_summary(mystery)

    # ── Step 6: optional save ────────────────────────────────────────────
    if save:
        path = generator.save_generated_mystery(mystery)
        print(f"\nSaved to: {path}")


def cmd_validate(path: str) -> None:
    """Run the coherence validator on an existing mystery JSON file."""
    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    with open(path, "r") as f:
        mystery = json.load(f)

    issues = check_mystery(mystery)
    title = mystery.get("title", path)
    print(format_report(issues, f"Coherence report — {title}"))

    blocking = [i for i in issues if i.severity == "BLOCKING"]
    sys.exit(1 if blocking else 0)


# ============================================================================
# DISPLAY
# ============================================================================

def _display_summary(mystery: Dict) -> None:
    print("\n" + "=" * 60)
    print("GENERATED MYSTERY")
    print("=" * 60)
    print(f"Title   : {mystery.get('title', '?')}")

    setting = mystery.get("setting", {})
    print(f"Setting : {setting.get('location', '?')} — {setting.get('time_period', '?')}")

    crime = mystery.get("crime", {})
    print(f"Crime   : {(crime.get('what_happened') or '')[:100]} ...")

    characters = mystery.get("characters", [])
    print(f"\nCharacters ({len(characters)}):")
    for c in characters:
        role = c.get("role", "?")
        name = c.get("name", "?")
        occ  = c.get("occupation", "")
        print(f"  [{role:8s}] {name} — {occ}")

    evidence = mystery.get("evidence", [])
    print(f"\nEvidence ({len(evidence)} items):")
    for e in evidence:
        rel  = e.get("relevance", "?")
        etype = (e.get("type") or e.get("evidence_type") or "?")
        name = e.get("name", "?")
        print(f"  [{rel:12s} / {etype:12s}] {name}")

    solution = mystery.get("solution", {})
    print(f"\nCulprit : {solution.get('culprit', '?')}")
    print(f"Method  : {(solution.get('method') or '')[:80]} ...")
    print("=" * 60)


# ============================================================================
# ARGUMENT PARSER
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Choose Your Mystery — CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py generate "A murder on a Mars colony" --players 4 --save
  python cli.py generate "Art theft in Prohibition Chicago" --players 5
  python cli.py validate ./mystery_database/generated/my_mystery.json
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    gen_p = sub.add_parser("generate", help="Generate a new mystery from a prompt.")
    gen_p.add_argument("prompt", help='e.g. "A murder on a Mars colony"')
    gen_p.add_argument("--players", type=int, default=4, help="Number of players (default: 4)")
    gen_p.add_argument("--save", action="store_true", help="Save generated mystery to disk")
    gen_p.add_argument("--verbose", action="store_true", help="Show detailed validation output")

    # validate
    val_p = sub.add_parser("validate", help="Validate an existing mystery JSON file.")
    val_p.add_argument("path", help="Path to the mystery JSON file")

    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(
            prompt=args.prompt,
            num_players=args.players,
            save=args.save,
            verbose=args.verbose,
        )
    elif args.command == "validate":
        cmd_validate(path=args.path)


if __name__ == "__main__":
    main()
