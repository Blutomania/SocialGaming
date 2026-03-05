# Choose Your Mystery — Development Guide

AI-powered mystery game database and generation system.

Players submit a prompt ("Murder on Mars", "Art Theft in Amazonia"). The system
generates a complete, validated mystery scenario ready for gameplay.

---

## Quick Start

```bash
# Install dependencies
pip install requests beautifulsoup4 anthropic python-dotenv

# Set API key
export ANTHROPIC_API_KEY=your-key

# Run the demo (no API needed)
python demo_acquisition.py

# Validate the demo mystery
python gameplay_validator.py

# Generate from a prompt (requires API key + database)
python mystery_generator.py
```

---

## Architecture

```
User Prompt: "Murder on Mars"
    ↓
[1] Theme Extraction
    era=near_future, tech_level=sci_fi, crime_type=murder
    ↓
[2] Database Retrieval
    Find similar mysteries by crime type, era, tech level
    ↓
[3] Pattern Extraction
    Character archetypes, motive types, clue structures
    ↓
[4] Generation (Claude)
    Prompt + patterns → complete MysteryScenario JSON
    ↓
[5] Validation
    Solvability, fairness, setting coherence, difficulty
    ↓
Ready for gameplay
```

---

## The Schema

See `MYSTERY_EXTRACTION_REQUIREMENTS.md` for full field documentation.

### Evidence: Two Types, Not One

Evidence is split by how it's discovered — because these map to two distinct
gameplay actions:

**`PhysicalClue`** — found by examining locations:
```python
category: physical | biological | digital | chemical | documentary | environmental
relevance: critical | supporting | red_herring
analysis_required: bool
analysis_method: "Toxicology lab" | "Gene sequencer" | "Alchemical reagents"
# Red herrings MUST have:
false_conclusion: str
why_misleading: str
what_disproves_it: "clue_id that disproves this"
```

**`TestimonialRevelation`** — extracted from NPC interrogation:
```python
providing_character: str
trigger_condition: "What question unlocks this"
relevance: critical | supporting | red_herring
```

### Tech Level Gates Evidence Categories

`world_tech_level` determines which `PhysicalClue.category` values are valid:

| Tech Level | Valid Categories |
|------------|-----------------|
| pre_industrial | physical, chemical, documentary, testimonial, environmental |
| industrial | same as pre_industrial |
| contemporary | + digital |
| advanced / sci_fi | + biological |

Validator checks this and fails incoherent mysteries.

### Characters — Designed for Interrogation

```python
is_culprit: bool          # Exactly ONE character per mystery
interrogation_behavior    # How they respond under questioning
what_they_hide            # What they actively conceal (everyone hides something)
knowledge_about_crime     # Their account of their own movements
knowledge_that_helps_solve  # Clue atoms players extract from them
```

### Solution Is an Ordered Chain

```python
solution_steps: [
    SolutionStep(
        step_number=1,
        clue_ids=["clue_005", "clue_006"],   # must reference real IDs
        logical_inference="...",
        conclusion="..."
    )
]
```

---

## The Six Test Queries

The canonical test set. Any schema change must work for all six.

| # | Query | Era | Tech Level | Crime |
|---|-------|-----|-----------|-------|
| 1 | Murder on Mars | near_future | sci_fi | murder |
| 2 | Art Theft in Amazonia | modern | contemporary | theft |
| 3 | Alchemical Forgery of the Abbasid Court | medieval | pre_industrial | forgery |
| 4 | Ghost-Signal of the Victorian Deep | victorian | industrial | disappearance |
| 5 | A Steampunk Sabotage | alternate_history | industrial | sabotage |
| 6 | Genetic Identity Heist of New Tokyo | near_future | sci_fi | identity_theft |

See `test_queries/` for per-query world context, expected faction structures,
evidence type hints, and validator expectations.

---

## File Structure

```
SocialGaming/
├── mystery_data_acquisition.py      # Pipeline + all schema dataclasses
├── mystery_generator.py             # RAG-based generator from prompts
├── gameplay_validator.py            # Automated quality validation
├── demo_acquisition.py              # No-API demo (Victorian locked room)
│
├── MYSTERY_EXTRACTION_REQUIREMENTS.md  # Canonical schema spec
├── mystery_database_plan.md            # Strategic roadmap
├── CLAUDE.md                           # Session context for Claude sessions
├── README.md                           # This file
├── GETTING_STARTED.md                  # Quickstart
├── requirements.txt
│
├── test_queries/                    # Six test query definitions
│   ├── README.md
│   ├── 01_murder_on_mars.json
│   ├── 02_art_theft_amazonia.json
│   ├── 03_alchemical_forgery_abbasid.json
│   ├── 04_ghost_signal_victorian_deep.json
│   ├── 05_steampunk_sabotage.json
│   └── 06_genetic_identity_heist_new_tokyo.json
│
└── mystery_database/               # Generated at runtime
    ├── index.json
    ├── scenarios/
    └── generated/
```

---

## Validation Rules

`gameplay_validator.py` enforces:

| Check | Rule |
|-------|------|
| Solvability | ≥2 critical physical clues, ≥1 critical testimonial |
| Culprit | Exactly 1 character with `is_culprit=True` matching `culprit_name` |
| Red herring fairness | Every red herring has `what_disproves_it` referencing a real clue ID |
| Setting coherence | All `PhysicalClue.category` values valid for `world_tech_level` |
| Interrogation coverage | Critical testimonials have `trigger_condition` |
| Motives | All suspects have `motive` populated |
| 75/25 rule | Total clues ≥8 for MEDIUM strategic depth |

---

## The 75/25 Sharing Rule

Each round, players must share 75% of what they discovered, keeping 25% private.

After 3 investigation turns (~6 items found):
- Must share: ~4-5 items
- Can withhold: ~1-2 items

This makes every clue a strategic decision: is this worth withholding to be
first to the solution, or worth sharing to get cooperation?

Mysteries need enough clues (≥8) and active-investigation clues (clues that
require effort to obtain) for this to be meaningful.

---

## API Costs

| Operation | Cost (Claude Sonnet) |
|-----------|---------------------|
| Process 1 Gutenberg mystery | ~$0.25 |
| Generate 1 new mystery | ~$0.15 |
| 50 processed + 50 generated | ~$20 |

---

## Production Roadmap

See `mystery_database_plan.md` for full detail.

| Phase | Status | Description |
|-------|--------|-------------|
| POC | Complete | JSON storage, Gutenberg scraper, RAG generator, validator |
| Quality | Next | Process 50+ mysteries, manual review, prompt tuning |
| Production | Future | PostgreSQL + pgvector, semantic search, API endpoint |
| Advanced | Future | NPC dialogue generation, player knowledge tracking |

---

## Legal

**Source content:**
- Project Gutenberg: Public domain (pre-1928) — safe
- Generated mysteries: Check Anthropic's terms for commercial use

**Before commercial launch:** Consult IP attorney regarding AI-generated content rights.

---

## Common Issues

**"No database found"** → Run `demo_acquisition.py` or `mystery_data_acquisition.py` first

**"API key not found"** → `export ANTHROPIC_API_KEY=your-key`

**Validator FAIL: red herring fairness** → Every red herring needs `what_disproves_it`

**Validator FAIL: setting coherence** → Check `PhysicalClue.category` against tech level matrix
