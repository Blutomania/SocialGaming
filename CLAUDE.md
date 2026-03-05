# CLAUDE.md — Session Context Protocol
## Choose Your Mystery — AI Development Guide

This file tells Claude what to read at the start of each session to maintain
continuity without repeating work already done.

---

## What to Read (In Priority Order)

### 1. Active Tasks
Read all task or issue files with `status: active` or `status: in_progress`.
These tell you what is currently broken or in-flight.

### 2. Recent Resolved Tasks
Read the most recent 20 files with `status: resolved` or `status: completed`.
This prevents duplicate solutions and shows what patterns were just established.

### 3. Active Implementation Plans
Read any implementation guide files for features currently being built.

### 4. Git History
Run: `git log --oneline -20`
This shows recent coding patterns and what has changed.

### 5. Dev Logs
Read the last 3-5 entries from any dev log or session notes.
These provide milestone context.

### 6. Architecture Documentation
- `MYSTERY_EXTRACTION_REQUIREMENTS.md` — canonical schema spec (READ THIS FIRST if working on schema)
- `mystery_database_plan.md` — strategic roadmap and production architecture

**Why this order:**
Active tasks tell you what's broken. Resolved tasks prevent duplicate solutions.
Git history shows coding patterns. Architecture docs provide the stable foundation.

---

## Project Summary

**What this is:** AI-powered mystery game database system for "Choose Your Mystery" —
a social deduction game where players investigate mysteries generated from user prompts.

**Core mechanic:** Players receive clues by investigating scenes (physical clues) or
interrogating NPCs (testimonial revelations). Each round, players must share 75% of
what they discovered, keeping 25% private. This creates strategic tension.

**The pipeline:**
```
User prompt ("Murder on Mars")
  → MysteryGenerator (RAG-based, grounded by database patterns)
  → MysteryScenario (canonical schema)
  → MysteryGameplayValidator (automated quality checks)
  → Ready for gameplay
```

---

## Canonical Schema

The schema is defined in `MYSTERY_EXTRACTION_REQUIREMENTS.md`.
The implementation is in `mystery_data_acquisition.py`.

**Key schema facts:**
- Evidence is split: `PhysicalClue` (scene investigation) vs `TestimonialRevelation` (NPC interrogation)
- Exactly ONE character has `is_culprit=True` per mystery
- Every red herring must have `what_disproves_it` populated (fairness rule)
- `world_tech_level` constrains which `category` values are valid in `PhysicalClue`
- `SolutionStep` is an ordered logical chain — each step references real clue IDs
- Scenario IDs are UUIDs (not title slugs)

**Tech level → valid evidence categories:**
```
pre_industrial: physical, chemical, documentary, testimonial, environmental
industrial:     physical, chemical, documentary, testimonial, environmental
contemporary:   + digital
advanced/sci_fi: + biological
```

---

## The Six Test Queries

These are the canonical test set. Any schema change must be validated against all six.
See `test_queries/` for structured per-query files.

1. Murder on Mars                              (sci_fi, locked_room, political stakes)
2. Art Theft in Amazonia                       (contemporary, heist, cultural property)
3. The Alchemical Forgery of the Abbasid Court (pre_industrial, procedural, medieval)
4. The Ghost-Signal of the Victorian Deep      (industrial, locked_room, victorian)
5. A Steampunk Sabotage                        (industrial, whodunit, alternate_history)
6. The Genetic Identity Heist of New Tokyo     (sci_fi, heist, near_future)

---

## File Map

| File | Purpose | Last Updated |
|------|---------|--------------|
| `mystery_data_acquisition.py` | Pipeline + all schema dataclasses | 2026-03-05 |
| `mystery_generator.py` | RAG-based generator from prompts | 2026-03-05 |
| `gameplay_validator.py` | Automated quality validation | 2026-03-05 |
| `demo_acquisition.py` | No-API demo (Victorian locked room) | 2026-03-05 |
| `MYSTERY_EXTRACTION_REQUIREMENTS.md` | Canonical schema spec | 2026-03-05 |
| `mystery_database_plan.md` | Strategic roadmap | 2026-03-05 |
| `README.md` | User-facing guide | 2026-03-05 |
| `GETTING_STARTED.md` | Quickstart | 2026-03-05 |
| `test_queries/` | Six test query definitions | 2026-03-05 |
| `requirements.txt` | Python dependencies | original |

---

## What Was Decided (Don't Re-debate These)

1. **Location/setting is player-chosen, not extracted.**
   The user prompt supplies the world. The pipeline extracts *world context*
   (era, tech_level, cultural_context) for RAG retrieval quality — not to
   recreate the setting from source text.

2. **Evidence is split into two types, not one.**
   `PhysicalClue` (from examining scenes) and `TestimonialRevelation` (from
   interrogating NPCs) are separate because they map to different gameplay actions
   and different strategic decisions in the 75/25 sharing mechanic.

3. **Exactly one culprit per mystery.**
   `is_culprit=True` on exactly one Character. The game engine uses this for
   accusation evaluation. Ambiguous culprits are not supported.

4. **Red herrings must be disprovable.**
   `what_disproves_it` is required on all red herrings. A mystery with an
   undisprovable red herring fails validation (unfair to players).

5. **Solution steps are ordered and reference real clue IDs.**
   `SolutionStep.clue_ids` must reference actual `clue_XXX` or `testimony_XXX`
   IDs in the same mystery. The validator checks this.

6. **Scenario IDs are UUIDs.**
   No more title-slug collisions. The demo also saves a slug-named copy for
   easy validator access during development.

7. **`world_tech_level` gates evidence categories.**
   Generator prompts must specify valid categories. Validator checks all
   `PhysicalClue.category` values against the tech level matrix.

---

## Current Status (as of 2026-03-05)

### Complete
- Full schema dataclasses in `mystery_data_acquisition.py`
- Generator with updated schema in `mystery_generator.py`
- Validator with full checks including red herring fairness, interrogation coverage, setting coherence
- Demo with fully structured Victorian locked room mystery
- Six test query definitions in `test_queries/`
- `MYSTERY_EXTRACTION_REQUIREMENTS.md` spec

### Next Steps
- Run the demo: `python demo_acquisition.py`
- Run the validator: `python gameplay_validator.py`
- Generate the first test query: `python mystery_generator.py`
- Generate and validate all six test queries
- Process 3-5 real mysteries from Project Gutenberg
- Manual review of generated outputs for quality

### Not Yet Done
- Parquet dataset parsing (dataset source not yet confirmed)
- Production database (PostgreSQL + pgvector) — see `mystery_database_plan.md`
- Game server integration
- Character dialogue generation (NPC conversations)
- Player knowledge tracking (75% sharing interface)

---

## Parquet Parsing — Status

The branch name `claude/confirm-parquet-parsing-Rqios` indicates parquet parsing
was a planned work item. As of 2026-03-05, no parquet file exists in the repo
and no parsing script has been written.

The current pipeline uses:
- **Source data:** Project Gutenberg (web scraping)
- **Storage:** JSON files
- **Future:** PostgreSQL + pgvector

If a parquet dataset becomes available, add a `parquet_ingestion.py` script
that reads parquet records into the `MysteryScenario` schema and passes them
to `MysteryDatabase.save_scenario()`.

---

*Session: claude/confirm-parquet-parsing-Rqios*
*Last updated: 2026-03-05*
