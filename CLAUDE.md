# CLAUDE.md — AI Assistant Guide for SocialGaming/Choose Your Mystery

This file provides guidance for AI assistants working on this codebase. Read it fully before starting any task.

---

## Project Overview

**Choose Your Mystery** is a Python-based system for acquiring, processing, generating, and validating mystery game scenarios. It powers a social deduction game where players share clues under a 75% sharing rule (players must share 75% of discovered information and may hide 25%).

The system uses Claude (Anthropic) as its AI backbone for content extraction and generation, and Project Gutenberg as its primary source of public domain mystery texts.

**Current Phase:** Proof of Concept → Early Production

---

## Repository Structure

```
/home/user/SocialGaming/
├── mystery_data_acquisition.py   # Data pipeline: scrape + AI-extract mysteries (600 lines)
├── mystery_generator.py          # RAG-based mystery generation via Claude (432 lines)
├── gameplay_validator.py         # Gameplay quality validation (366 lines)
├── demo_acquisition.py           # Demo pipeline with mock data, no API required (493 lines)
├── requirements.txt              # Python dependencies
├── README.md                     # Full usage guide and architecture overview
├── GETTING_STARTED.md            # Quick start guide
├── mystery_database_plan.md      # Database strategy and roadmap
├── tasks/
│   ├── todo.md                   # Task tracking (create if absent)
│   └── lessons.md                # Self-improvement log (create if absent)
└── mystery_database/             # Runtime output (generated)
    ├── index.json
    ├── scenarios/
    ├── generated/
    └── raw_texts/
```

---

## Source Modules

### `mystery_data_acquisition.py`
Acquires public domain mystery texts and uses Claude to extract structured data.

**Key classes:**
- `Character` — dataclass: name, role, archetype, motive, quotes
- `Evidence` — dataclass: description, type, relevance, context
- `MysteryScenario` — complete mystery structure (characters, evidence, solution)
- `GutenbergScraper` — scrapes Project Gutenberg for mystery books
- `MysteryProcessor` — calls Claude to extract structured JSON from raw text
- `MysteryDatabase` — JSON-file storage with index maintenance

**Pipeline flow:**
```
Search Gutenberg → Download Text → Claude Extraction (4 steps) → Save to JSON
```

### `mystery_generator.py`
Generates new mystery scenarios using RAG (Retrieval Augmented Generation).

**Key class:** `MysteryGenerator`

**RAG pipeline:**
```
User Prompt → Theme Extraction → DB Retrieval → Pattern Extraction → Claude Generation → Mystery
```

### `gameplay_validator.py`
Validates mysteries for playability before use in the game.

**Validation checks:**
1. Solvability — critical evidence count, motive coverage, red herring balance
2. Information sharing — confirms the 75% sharing mechanic creates strategic depth
3. Difficulty estimation — EASY / MEDIUM / HARD
4. Playtime estimation

### `demo_acquisition.py`
Fully self-contained demo. Uses `MockMysteryProcessor` instead of real Claude calls.
No `ANTHROPIC_API_KEY` or network access required. Use this to validate data structures.

---

## Environment Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Download spaCy model
python -m spacy download en_core_web_sm

# 3. Set required environment variable
export ANTHROPIC_API_KEY="your-key-here"

# 4. Optional overrides
export DATABASE_PATH="./mystery_database"   # default
export LOG_LEVEL="INFO"                     # default
```

**Running the pipeline:**
```bash
python demo_acquisition.py          # No API needed — verify data structures
python mystery_data_acquisition.py  # Acquires and processes real mysteries
python mystery_generator.py         # Generates a new mystery scenario
python gameplay_validator.py        # Validates gameplay quality
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `anthropic` | >=0.18.0 | Claude API — all AI processing |
| `requests` | >=2.31.0 | HTTP for web scraping |
| `beautifulsoup4` | >=4.12.0 | HTML parsing (Gutenberg) |
| `python-dotenv` | >=1.0.0 | Environment variable management |
| `spacy` | >=3.7.0 | NLP (optional, future use) |
| `psycopg2-binary` | >=2.9.9 | PostgreSQL (optional, production) |

**Future/optional (commented in requirements.txt):** `pgvector`, `sentence-transformers`, `aiohttp`, `pytest`, `black`, `flake8`

---

## Coding Conventions

Follow these patterns throughout the codebase:

**Type hints everywhere:**
```python
def search_mysteries(self, query: str = "detective mystery", limit: int = 10) -> List[Dict]:
```

**Dataclasses for data models:**
```python
@dataclass
class Character:
    name: str
    role: str
    description: str = ""
    archetype: Optional[str] = None
```

**Docstrings explain the "Why", not just the "What":**
```python
"""
Extract key themes from user prompt

Why extract themes first: Enables better database retrieval by narrowing
the search space before pattern matching.
"""
```

**Error handling with fallback JSON:**
```python
try:
    return json.loads(response_text)
except json.JSONDecodeError:
    return {'crime_type': 'unknown', ...}
```

**File section headers:**
```python
# ============================================================
# DATA MODELS
# ============================================================
```

**Naming:**
- `snake_case` — functions and variables
- `PascalCase` — classes
- `UPPER_CASE` — constants
- Descriptive names: `MysteryProcessor`, `GutenbergScraper`

**JSON storage:** Always use `indent=2` for readability.

---

## Architecture Patterns

1. **Pipeline Pattern** — sequential steps with error handling: Acquire → Process → Store
2. **RAG** — retrieval-augmented generation for mystery creation
3. **Dataclasses** — typed, immutable data models
4. **Strategy Pattern** — scrapers and processors are swappable
5. **Validator Pattern** — quality checks are isolated from generation logic

---

## Workflow Orchestration

### 1. Plan Mode Default

- Enter plan mode for **any non-trivial task** (3+ steps or architectural decisions)
- If something goes sideways, **STOP and re-plan immediately** — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy

Keep the main context window clean:
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One focused task per subagent

### 3. Self-Improvement Loop

- After **any correction from the user**: update `tasks/lessons.md` with the pattern
- Write rules that prevent the same mistake from recurring
- Ruthlessly iterate on these lessons until mistake rate drops
- Review `tasks/lessons.md` at session start for relevant context

### 4. Verification Before Done

- **Never mark a task complete without proving it works**
- Diff behavior between main and your changes when relevant
- Ask: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)

- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing

- When given a bug report: **just fix it** — no hand-holding needed
- Point at logs, errors, failing tests → then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

---

## Task Management

### Workflow

1. **Plan First** — Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan** — Check in before starting implementation for significant changes
3. **Track Progress** — Mark items complete as you go (one `in_progress` at a time)
4. **Explain Changes** — High-level summary at each step
5. **Document Results** — Add outcome summary to `tasks/todo.md`
6. **Capture Lessons** — Update `tasks/lessons.md` after any corrections

### `tasks/todo.md` format

```markdown
## Task: <name>

- [ ] Step 1
- [ ] Step 2
- [x] Step 3 (completed)

## Results
<summary of what was done and verified>
```

### `tasks/lessons.md` format

```markdown
## Lesson: <short title>
**Date:** YYYY-MM-DD
**Mistake:** What went wrong
**Correction:** What the user said
**Rule:** Going forward, always/never...
```

---

## Core Principles

- **Simplicity First** — Make every change as simple as possible. Impact minimal code.
- **No Laziness** — Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact** — Only touch what's necessary. Avoid introducing unintended side effects.

---

## Test Dataset

**Location:** https://github.com/Blutomania/mystery-crime-books

This is the canonical test dataset for the project. It is a HuggingFace-style dataset containing:

| File | Purpose |
|---|---|
| `dataset_infos.json` | Dataset metadata and schema description |
| `train-00000-of-00001.parquet` | Mystery/crime book data in columnar Parquet format |

**Usage guidance:**
- Use this dataset as the reference input when testing the data acquisition and processing pipeline
- Do not commit processed outputs back to this repo — it is read-only test data
- When validating changes to `mystery_data_acquisition.py` or `mystery_generator.py`, use records from this dataset as source material
- The `.parquet` file can be read with `pandas` or `pyarrow`: `pd.read_parquet("train-00000-of-00001.parquet")`

---

## Key Files Quick Reference

| File | Lines | Role |
|---|---|---|
| `mystery_data_acquisition.py` | 600 | Scraping + Claude extraction pipeline |
| `mystery_generator.py` | 432 | RAG-based mystery generation |
| `gameplay_validator.py` | 366 | Playability quality checks |
| `demo_acquisition.py` | 493 | Self-contained demo, no API needed |
| `requirements.txt` | — | Python dependencies |
| `tasks/todo.md` | — | Current task tracking |
| `tasks/lessons.md` | — | Self-improvement log |

---

## Cost Estimates (Claude API)

| Operation | Cost per unit | Notes |
|---|---|---|
| Process one mystery | ~$0.25 | 4-step Claude extraction |
| Generate one mystery | ~$0.15 | RAG + generation |
| 100 mysteries total | ~$40 | Full MVP dataset |

---

## Roadmap (from `mystery_database_plan.md`)

- **Phase 1** ✅ — POC: JSON storage, Gutenberg scraping, Claude extraction
- **Phase 2** — PostgreSQL + pgvector for semantic search at scale
- **Phase 3** — Async processing, batch API calls
- **Phase 4** — Full game backend integration

---

## Notes for AI Assistants

- Always run `demo_acquisition.py` first to validate data structures before touching the real pipeline
- The 75% sharing rule is **core to gameplay** — any change touching evidence/character sharing must preserve this mechanic
- Claude API calls in `MysteryProcessor` and `MysteryGenerator` follow a consistent pattern: send prompt → parse JSON → fallback on error
- JSON storage is intentional for POC — do not migrate to a database unless explicitly requested
- No CI/CD or test framework exists yet — manual verification via demo script is the current standard
