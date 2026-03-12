# Choose Your Mystery — Session State
> **Read this at the start of every new session.** Update the "Current State"
> and "Last Session" sections before running `end_of_session.sh`.

---

## Project Overview

**What it is:** An AI-powered mystery game backend.
Players are assigned suspect roles and must investigate, share 75% of their
clues, and accuse the culprit. Mysteries are generated on-demand via RAG +
Claude.

**Core files:**

| File | Purpose |
|---|---|
| `mystery_data_acquisition.py` | Scrapes Project Gutenberg, uses Claude to extract structured mystery data into `./mystery_database/` |
| `mystery_generator.py` | RAG-based generator — takes a user prompt, retrieves similar scenarios, generates a complete mystery JSON via Claude |
| `gameplay_validator.py` | Checks solvability, 75%-sharing strategic depth, and difficulty of a generated mystery |
| `coherence_validator.py` | **TO BUILD** — pre-generation parts gate + post-generation logical coherence checks (P1 chain, interrogation anchors, scene investigation) |
| `demo_acquisition.py` | No-API demo that runs the pipeline against a bundled sample |

**Mystery JSON schema** (used by generator and validators):
```
title, setting, crime, characters[], evidence[], solution,
investigation_locations[], gameplay_notes
```
- `characters[].role` → `victim | suspect | witness | detective`
- `evidence[].relevance` → `critical | supporting | red_herring`
- `evidence[].type` (or `.evidence_type`) → `physical | testimonial | documentary | circumstantial`

---

## Current State

**Branch:** `claude/coherence-validator-review-ekzqO`
**Last pushed commit:** `45f4980` (original file upload — no new code pushed yet)

### What is DONE
- [x] Data acquisition pipeline (`mystery_data_acquisition.py`)
- [x] RAG mystery generator (`mystery_generator.py`)
- [x] Gameplay validator (`gameplay_validator.py`)
- [x] Demo script + sample database (`demo_acquisition.py`)

### What is NOT YET DONE
- [ ] `coherence_validator.py` — the main task for this feature branch
- [ ] `SESSION_STATE.md` + `end_of_session.sh` — meta tooling (added this session)

---

## coherence_validator.py — Design Contract

### Three check families (all inside `check_mystery(mystery) -> List[Issue]`)

**1. P1 chain** — BLOCKING if broken
- `crime.what_happened` ≥ 30 chars
- A `victim` character exists
- At least one `suspect` character exists
- `solution.culprit` is in the character list
- Culprit has a non-vague motive (both in character record and solution)
- `solution.key_evidence` IDs all exist in the evidence list
- `solution.how_to_deduce` ≥ 40 chars

**2. Interrogation anchors** — WARNING if broken
- Every `suspect` and `witness`:
  - `alibi` > 20 chars, not "—"
  - `secrets` > 30 chars, not a label like "has a dark past"
  - `motive` (suspects only) — specific, > 15 chars, not "—"
- Victim has a documented `secrets` or a rich `personality` (≥ 40 chars)

**3. Scene investigation** — WARNING if broken
- ≥ 5 total evidence items (75% sharing mechanic needs depth)
- ≥ 2 `physical` evidence items
- ≥ 1 `red_herring` that is `physical` or `documentary` (not testimonial-only)
- Evidence uses ≥ 2 distinct types (variety)
- Every evidence `description` ≥ 40 chars
- ≥ 2 `critical` evidence items (backup deduction path)

### `check_parts(parts) -> List[Issue]` — pre-generation gate
Validates individual registry parts **before** any Claude API call.
Each issue carries a `repair_hint` naming the `part_type` to re-sample.

### `Issue` dataclass
```python
@dataclass
class Issue:
    severity: str      # "BLOCKING" | "WARNING"
    family: str        # "p1_chain" | "interrogation" | "scene" | "parts"
    message: str
    repair_hint: str   # which part_type to re-sample from registry
```

### Generation prompt improvements (in `mystery_generator.py`)
Add concrete good/bad examples to the alibi and secret fields in the
`_generate_with_claude` prompt so the first call passes validation most
of the time.

---

## Key Decisions

- **Cost discipline:** `repair_hint` always says *which part_type to re-sample*,
  never "call Claude again on the whole mystery". `check_parts()` runs before
  any API call; targeted re-samples are cheap.
- **Severity levels:** P1 chain breaks → BLOCKING (mystery unplayable).
  Interrogation/scene gaps → WARNING (degrades quality but still playable).
- **Schema tolerance:** validator accepts both `evidence[].type` and
  `evidence[].evidence_type` keys (generator uses `type`; acquisition pipeline
  uses `evidence_type`).

---

## Next Session Checklist

1. Read this file.
2. Run `git status` and `git log --oneline -5` to orient yourself.
3. Pick up from "What is NOT YET DONE" above.
4. When finished, update this file's "Current State" section and run
   `./end_of_session.sh "Your commit message here"`.
