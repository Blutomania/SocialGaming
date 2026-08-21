#!/usr/bin/env python3
"""
Model bake-off for P1->P2 extraction: run one source through several models and
score the results mechanically.

WHY THIS EXISTS
---------------
"Which model should the P1->P2 re-extraction use?" is an empirical question, and
this repo can answer it objectively rather than by reading outputs and forming an
impression. Extractions are not the product -- `part_registry._atomize_extraction`
is what consumes them, turning extraction fields into sampling parts across 8
axes. So the metric that matters is not how good the prose reads, it is **how many
parts the extraction yields and which axes it fills.** An extraction that reads
beautifully and atomizes to nothing is worth nothing to generation.

The three P2-only axes are the whole point of the re-extraction:
  axis 4  suspect_archetype  <- suspect_architecture
  axis 5  red_herring        <- red_herring / clue_fairness
  axis 8  alibi              <- alibi
A P1-only source fills 5 of 8. If a model cannot reliably populate those three
fields, it has failed at the only job this run exists to do.

Usage:
    python3 scripts/compare_extraction_models.py <source.pdf> [--story N]
        [--models claude-haiku-4-5,claude-sonnet-4-6,claude-opus-5]
        [--out DIR]

Cost: one call per model per source. Printed per run, and it is small -- see the
per-source figures in the summary table.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import extraction_protocols as ep
import part_registry as pr

# $ per million tokens, input/output.
PRICES = {
    "claude-haiku-4-5":  (1.00, 5.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-5":     (5.00, 25.00),
}

P2_FIELDS = ["suspect_architecture", "red_herring", "clue_fairness", "alibi",
             "reveal_mechanic", "social_world"]
P1_FIELDS = ["crime", "victim", "closed_world", "culprit_and_motive",
             "resolution", "investigator"]

# Phrases that mean "I could not find anything specific". A field can be
# populated and still say nothing, which no field-count would catch.
VAGUE = ["not specified", "not stated", "unclear", "unknown", "none identified",
         "no explicit", "not applicable", "cannot be determined", "not present",
         "n/a"]


def value_of(field):
    """Extraction fields are {value, confidence, ...} dicts; some are bare."""
    if isinstance(field, dict):
        return (field.get("value") or "", (field.get("confidence") or "").lower())
    return (str(field or ""), "")


def score(data: dict) -> dict:
    """Mechanical quality of one extraction."""
    out = {"populated": {}, "vague": [], "conf": {"high": 0, "medium": 0, "low": 0}}
    lengths = []
    for key in P1_FIELDS + P2_FIELDS:
        val, conf = value_of(data.get(key))
        val = val.strip()
        filled = bool(val) and not any(v in val.lower()[:80] for v in VAGUE)
        out["populated"][key] = filled
        if val and not filled:
            out["vague"].append(key)
        if filled:
            lengths.append(len(val))
        if conf in out["conf"]:
            out["conf"][conf] += 1

    out["p1_filled"] = sum(out["populated"][k] for k in P1_FIELDS)
    out["p2_filled"] = sum(out["populated"][k] for k in P2_FIELDS)
    out["mean_len"] = round(sum(lengths) / len(lengths)) if lengths else 0

    # The metric that actually matters: what the registry gets out of it.
    # _atomize_extraction appends to registry.parts and returns None. Call it the
    # way load_registry does, so this count is exactly what generation would get.
    #
    # Note what it does on the way: any field whose confidence is "low" is
    # SKIPPED ENTIRELY, as is any value under 10 characters. So a model that
    # hedges contributes nothing even when the field is populated -- which is
    # why confidence is scored here as a first-class number rather than trivia.
    reg = pr.PartRegistry.__new__(pr.PartRegistry)
    reg.parts = []
    reg._atomize_extraction(data, "bakeoff", "bakeoff")
    out["parts"] = len(reg.parts)
    out["axes"] = sorted({p.part_index for p in reg.parts})
    out["p2_axes"] = sorted(set(out["axes"]) & {4, 5, 8})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="PDF (or .txt) to extract from")
    ap.add_argument("--story", type=int, default=None,
                    help="1-based story index, for an anthology PDF")
    ap.add_argument("--models", default="claude-haiku-4-5,claude-sonnet-4-6,claude-opus-5")
    ap.add_argument("--out", default=None, help="directory to write raw outputs")
    args = ap.parse_args()

    src = Path(args.source)
    if src.suffix.lower() == ".txt":
        text = src.read_text(errors="ignore")
        label = src.stem
    else:
        import extract_from_pdfs as efp
        _, text = efp.extract_text_from_pdf(src)
        label = src.stem
        if args.story:
            stories = efp._split_anthology_stories(src)
            s = stories[args.story - 1]
            text = s.get("text", "")
            label = f'{s.get("title", "story")} ({s.get("author", "?")})'
            print(f"  anthology: story {args.story} of {len(stories)}")

    prompt = ep.combined_prompt(["P1", "P2"], text)
    print(f"source: {label}")
    print(f"  {len(text):,} chars of source -> {len(prompt):,} char prompt\n")

    from anthropic import Anthropic
    tok = Path("/home/claude/.claude/remote/.session_ingress_token")
    client = Anthropic(auth_token=tok.read_text().strip()) if tok.exists() else Anthropic()

    results = {}
    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        print(f"→ {model}")
        t = time.time()
        try:
            r = client.messages.create(
                model=model, max_tokens=8000,
                system="You are a literary analyst. Return only valid JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            print(f"   API ERROR: {type(exc).__name__}: {str(exc)[:100]}\n")
            results[model] = {"error": str(exc)[:200]}
            continue
        elapsed = time.time() - t
        raw = r.content[0].text
        try:
            data = ep.parse_extraction_response(raw) if hasattr(ep, "parse_extraction_response") \
                   else json.loads(raw.split("```json")[1].split("```")[0] if "```json" in raw else raw)
            parsed = True
        except Exception as exc:
            print(f"   PARSE FAILED: {exc}")
            data, parsed = {}, False

        pin, pout = PRICES.get(model, (3.0, 15.0))
        cost = r.usage.input_tokens * pin / 1e6 + r.usage.output_tokens * pout / 1e6
        s = score(data) if parsed else {}
        results[model] = {"parsed": parsed, "elapsed": elapsed, "cost": cost,
                          "in": r.usage.input_tokens, "out": r.usage.output_tokens,
                          "score": s, "data": data}
        if parsed:
            print(f"   P1 {s['p1_filled']}/6  P2 {s['p2_filled']}/6  "
                  f"parts {s['parts']}  axes {s['axes']}  P2-axes {s['p2_axes']}")
            if s["vague"]:
                print(f"   vague: {', '.join(s['vague'])}")
        print(f"   {r.usage.output_tokens:,} out tok, {elapsed:.0f}s, ${cost:.4f}\n")

    print(f"{'model':28} {'JSON':5} {'P1':5} {'P2':5} {'parts':6} {'P2 axes':10} "
          f"{'conf hi':8} {'$/src':8} {'$/75':8}")
    for m, r in results.items():
        if r.get("error"):
            print(f"{m:28} ERROR {r['error'][:40]}"); continue
        s = r["score"]
        if not r["parsed"]:
            print(f"{m:28} {'NO':5} {'-':5} {'-':5} {'-':6} {'-':10} {'-':8} "
                  f"${r['cost']:.4f}  (wasted)"); continue
        print(f"{m:28} {'yes':5} {s['p1_filled']}/6   {s['p2_filled']}/6   "
              f"{s['parts']:<6} {str(s['p2_axes']):10} {s['conf']['high']:<8} "
              f"${r['cost']:.4f}  ${r['cost']*75:.2f}")

    if args.out:
        d = Path(args.out); d.mkdir(parents=True, exist_ok=True)
        for m, r in results.items():
            (d / f"{label}__{m.replace('.','-')}.json").write_text(
                json.dumps(r.get("data", {}), indent=2))
        print(f"\nraw outputs -> {d}")


if __name__ == "__main__":
    main()
