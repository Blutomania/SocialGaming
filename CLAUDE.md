# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Choose Your Mystery** is a Python-based system for acquiring, processing, generating, and validating mystery game scenarios. It powers a social deduction game where players share clues under a **75% sharing rule** — players must share 75% of discovered information and may hide 25%.

The system uses Claude (Anthropic) as its AI backbone and Project Gutenberg as its primary source of public domain mystery texts.

**Current Phase:** Proof of Concept → Early Production

---

## Running the Code

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (required for real Claude calls)
export ANTHROPIC_API_KEY="your-key-here"

# Demo pipelines — no API key needed, validate data structures first
python demo_acquisition.py                  # Original pipeline demo (MysteryScenario schema)
python pull_script_03_causal_chain.py       # Causal chain demo (PlayableMystery schema)

# Real pipelines (require ANTHROPIC_API_KEY)
python mystery_data_acquisition.py          # Scrape Gutenberg + Claude extraction
python mystery_generator.py                 # RAG-based mystery generation
python gameplay_validator.py                # Validate a scenario file
python pull_script_03_causal_chain.py --real  # Causal chain extraction with Claude
```

No test framework exists yet — manual verification via the demo scripts is the current standard.

---

## Two-Schema Architecture

The codebase has two distinct data schemas serving different purposes:

### 1. `MysteryScenario` (source schema)
Defined in `mystery_data_acquisition.py`. Represents a mystery as extracted from raw literary text — setting-specific, named characters, flat evidence list. Stored under `mystery_database/scenarios/`.

### 2. `PlayableMystery` (target schema)
Defined in `pull_script_03_causal_chain.py`. The canonical output format for all pull scripts. Represents a mystery as a **causal clue graph** with abstract roles (not named characters), optimised for game evaluation. Stored under `causal_chain_output/`.

The **pull scripts** (`pull_script_03_causal_chain.py`, and future scripts 1, 2, 4–7) each take source text and produce a `PlayableMystery` JSON. They differ in extraction strategy; all output the same schema.

**Data flow:**
```
Raw text (Gutenberg / dataset)
    → mystery_data_acquisition.py  →  MysteryScenario (mystery_database/)
    → pull_script_0N_*.py          →  PlayableMystery (causal_chain_output/)
                                              ↓
                                    PlayabilityCalculator
                                    (MCD · RSE · UST · score)
```

---

## Playability Metrics (PlayableMystery)

These metrics live in `PlayabilityCalculator` inside `pull_script_03_causal_chain.py`:

| Metric | Target | Description |
|--------|--------|-------------|
| **MCD** (Minimum Clue Depth) | 4–8 clues | BFS over the clue graph — fewest clues needed to uniquely identify the culprit |
| **RSE** (Round-to-Solution Estimate) | ≤4 rounds | Monte Carlo simulation (200 trials) of N-player gameplay with 75% sharing |
| **UST** (Unique Solution Test) | Pass | All real clues → exactly one valid culprit |
| **RHR** (Red Herring Ratio) | 20–40% | Fraction of clues that misdirect |
| **Playability Score** | 0.0–1.0 | Weighted composite: UST (0.4) + MCD (0.3) + RSE (0.2) + RHR (0.1). UST failure → 0.0 |

The 75% sharing rule is **core to gameplay** — any change touching clue sharing, `shareable` flags, or `PlayabilityCalculator._rse()` must preserve this mechanic.

---

## Key Classes

### `mystery_data_acquisition.py`
- `Character`, `Evidence`, `MysteryScenario` — source schema dataclasses
- `GutenbergScraper` — scrapes Project Gutenberg search + downloads plain text
- `MysteryProcessor` — 4-step Claude extraction: classify → characters → evidence → summary
- `MysteryDatabase` — JSON storage at `mystery_database/`, maintains `index.json`

### `mystery_generator.py`
- `MysteryGenerator` — RAG pipeline: extract themes → retrieve DB examples → extract patterns → generate with Claude. Requires `mystery_database/` to exist (run acquisition first).

### `gameplay_validator.py`
- `MysteryGameplayValidator` — validates a `MysteryScenario` JSON file. Checks solvability, information-sharing depth, and estimates difficulty/playtime. Operates on the **source schema**, not `PlayableMystery`.

### `pull_script_03_causal_chain.py`
- `PlayableClue`, `PlayableCharacter`, `PlayableMystery` — target schema dataclasses
- `CausalChainExtractor` — 3-step Claude extraction: characters → clue graph → solution
- `MockCausalChainExtractor` — deterministic demo, no API needed
- `PlayabilityCalculator` — computes MCD (BFS), RSE (simulation), UST, score
- `CausalChainDatabase` — saves `PlayableMystery` JSON to `causal_chain_output/`

### `demo_acquisition.py`
- `MockMysteryProcessor` — stand-in for `MysteryProcessor`, no API calls, validates source schema

---

## Coding Conventions

**Type hints on every function:**
```python
def search_mysteries(self, query: str = "detective mystery", limit: int = 10) -> List[Dict]:
```

**Dataclasses for all data models** — use `field(default_factory=list)` for mutable defaults.

**Docstrings explain the "Why":**
```python
"""
Why BFS: We want the minimum number of clues, not the first path found.
BFS guarantees the shortest path in an unweighted graph.
"""
```

**Claude API pattern** — all Claude calls follow: send prompt → strip markdown fences → `json.loads()` → fallback dict on `JSONDecodeError`.

**Section headers:**
```python
# ============================================================
# DATA MODELS
# ============================================================
```

**JSON storage:** Always `indent=2`. Source schema → `mystery_database/`. Target schema → `causal_chain_output/`.

**Model to use:** `claude-sonnet-4-6` (some older files still reference `claude-sonnet-4-20250514` — update when touching those files).

---

## Architecture Patterns

- **Pipeline Pattern** — sequential steps with per-step error handling and fallbacks
- **Strategy Pattern** — `MockMysteryProcessor` / `CausalChainExtractor` are swappable; add new extractors without changing the pipeline runner
- **Graph evaluation** — `PlayableMystery.clue_chain` is a DAG; `PlayabilityCalculator` walks it with BFS for MCD and Monte Carlo for RSE
- **RAG** — `MysteryGenerator` retrieves real examples before generating, ensuring structural authenticity

---

## Task Management

Track work in `tasks/todo.md` and capture lessons in `tasks/lessons.md`.

**`tasks/todo.md` format:**
```markdown
## Task: <name>
- [ ] Step
- [x] Done step

## Results
<verified outcome>
```

**`tasks/lessons.md` format:**
```markdown
## Lesson: <title>
**Date:** YYYY-MM-DD
**Mistake:** What went wrong
**Correction:** What the user said
**Rule:** Going forward, always/never...
```

Review `tasks/lessons.md` at session start. Update it after any correction.

---

## Test Dataset

**Location:** https://github.com/Blutomania/mystery-crime-books

HuggingFace-style dataset with `train-00000-of-00001.parquet` (mystery/crime book data). Use as reference input when testing the acquisition and processing pipeline. Read with `pd.read_parquet(...)`. Do not commit processed outputs back.

---

## Notes

- Always run the relevant demo script first (`demo_acquisition.py` or `pull_script_03_causal_chain.py` without `--real`) to validate data structures before touching the real pipeline.
- JSON storage is intentional for POC — do not migrate to a database unless explicitly requested.
- `gameplay_validator.py` operates on `MysteryScenario` (source schema). `PlayabilityCalculator` in `pull_script_03_causal_chain.py` is the equivalent for the target schema — they are parallel, not interchangeable.
- Roadmap: Phase 2 = PostgreSQL + pgvector, Phase 3 = async/batch, Phase 4 = game backend integration.
