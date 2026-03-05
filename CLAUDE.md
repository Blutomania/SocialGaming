# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Choose Your Mystery** is a social mystery game backend. The system acquires public-domain mystery books, extracts structured data using Claude AI, stores them in a JSON database, and uses RAG (Retrieval Augmented Generation) to generate novel mystery scenarios on demand.

## Setup

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Running the Pipeline

```bash
# 1. Acquire and process mysteries from Project Gutenberg
python mystery_data_acquisition.py

# 2. Generate a new mystery from a prompt (requires populated database)
python mystery_generator.py

# 3. Validate a generated mystery's gameplay quality
python gameplay_validator.py

# 4. Demo mode (no API key or network needed)
python demo_acquisition.py
```

There is no test suite currently. The `requirements.txt` has pytest commented out as a future addition.

## Architecture

### Core Data Flow

```
Source text (Gutenberg / Parquet dataset)
    -> mystery_data_acquisition.py  (GutenbergScraper + MysteryProcessor)
    -> ./mystery_database/index.json + scenarios/*.json

User prompt ("Murder on Mars")
    -> mystery_generator.py  (MysteryGenerator)
        -> retrieves similar scenarios from index
        -> extracts patterns (archetypes, motives, evidence types)
        -> calls Claude API to generate a new mystery
    -> ./mystery_database/generated/*.json

Generated mystery JSON
    -> gameplay_validator.py  (MysteryGameplayValidator)
        -> checks solvability, difficulty, 75%-sharing mechanic depth
```

### Primary Test Dataset

359 mystery/crime books from `https://github.com/Blutomania/mystery-crime-books` (Hugging Face Parquet format, fields: `url`, `text`). Use this dataset during development — do not ask for it again.

### Schema B (Orthogonal Axes) — The Core Index Model

All mysteries are indexed using four independent, swappable axes. This is what makes combinatorial generation possible:

```
WORLD  : era, genre_modifier, environment, culture, special_tech
CRIME  : category, method, scale, macguffin
CAST   : culprit_archetype, victim_type, investigator_type, suspect_archetypes[]
PLOT   : crime_structure, motive, twist_type, red_herring_count, clue_trail_length, plot_beats[]
```

Each axis uses a controlled enum (defined as constants in `mystery_data_acquisition.py`, e.g. `ERA_VALUES`, `GENRE_MODIFIER_VALUES`). These enums are the single source of truth — always check them before adding new values.

Generation uses the recipe `A(WORLD) + B(CRIME) + C(CAST) + D(PLOT)`, combining axes from different source mysteries.

### Two-Layer Session Architecture

- **Layer 1 — Version Hash** (locked at game start): Encodes the mystery's logical content from all Schema B axes. Deterministic and reproducible.
- **Layer 2 — Session Config** (host-adjustable mid-game): `tone`, `rating`, `difficulty`, `pacing`. These control how the mystery is *expressed*, not what it *is*. `tone` (noir, cozy, thriller…) lives here, not in the version hash.

### Key Design Decisions

- `genre_modifier = null` means realistic (no world-physics modifier). Do not add a "realistic" enum value.
- `tone` is NOT a version-hash axis — a cyberpunk mystery can be noir or cozy. Keep it in Session Config.
- `noir` is tone, not genre. Do not add it to `GENRE_MODIFIER_VALUES`.
- `environment` (built/natural spaces) was renamed from `biome` — use `environment`.

### Gameplay Mechanic: 75% Sharing Rule

Players must share 75% of their collected evidence/interrogation findings at each sharing phase. `gameplay_validator.py` checks that this rule creates meaningful strategic decisions (i.e. there are enough information pieces and critical evidence is distributed across players).

## File Reference

| File | Purpose |
|---|---|
| `mystery_data_acquisition.py` | Main pipeline: scraping, Schema B extraction via Claude, JSON storage |
| `mystery_generator.py` | RAG-based mystery generation (`MysteryGenerator` class) |
| `gameplay_validator.py` | Gameplay quality checks (`MysteryGameplayValidator` class) |
| `demo_acquisition.py` | Offline demo with hardcoded sample data (no API/network needed) |
| `mystery_database_plan.md` | Phased strategy document (data sources, schema evolution, budget) |
| `SCHEMA_EXPLORATION.md` | Schema B design rationale and enum decisions with full justification |
| `mystery_database/` | Runtime output — index.json, scenarios/, generated/, raw_texts/ |

## Environment Variables

| Variable | Required | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — |
| `DATABASE_PATH` | No | `./mystery_database` |
| `LOG_LEVEL` | No | `INFO` |

## API Cost Reference

- Processing 1 source mystery (~50k words): ~$0.25
- Generating 1 new mystery: ~$0.15
- Building a 100-mystery database + 50 generated mysteries: ~$33 total

## Current Limitations (POC)

- Storage is flat JSON files; search is O(n) linear scan. Suitable for < 1,000 mysteries.
- API calls are synchronous/sequential. For production, migrate to async and PostgreSQL + pgvector.
- Claude occasionally wraps JSON output in markdown fences — the code strips these, but edge cases exist.

## Content Licensing

Only use Project Gutenberg (public domain, pre-1928) or Creative Commons sources. Do not store full copyrighted texts. Extracting structural patterns from copyrighted works is generally acceptable; storing full text is not.
