# SESSION STATE — Choose Your Mystery

> **Purpose:** This file is the authoritative project memory. It is updated at
> the end of every session. Any new Claude session should READ THIS FIRST before
> asking clarifying questions or starting work. If something contradicts the
> README, this file wins for current state.

---

## Project Overview

A multiplayer social deduction game where users are given a generated mystery
and take turns questioning witnesses, chasing leads, and investigating crime
scenes until they solve it.

**User-facing flow:**
1. Player enters a prompt (e.g. "murder on a Victorian submarine")
2. App samples compatible parts from the part registry and assembles a full mystery
3. Players interrogate, investigate, and finally accuse — game validates correctness

**Tech stack (planned):**
- Python backend — `cli.py` (extraction pipeline), `part_registry.py` (part sampling), `app.py` (Gradio UI)
- Hosted on HuggingFace Spaces
- Corpus: `mystery-crime-books/` parquet file (~14MB, grows over time) — **NOT in git** (too large, growing)
- LLM: Anthropic Claude API for extraction and generation

---

## Repository Layout (current)

```
SocialGaming/
├── SESSION_STATE.md          ← YOU ARE HERE — read first every session
├── test_mysteries.py         ← 6 hand-crafted test mysteries as Python constants
├── mystery_generator.py      ← early-stage generator (pre-part-registry)
├── mystery_data_acquisition.py
├── demo_acquisition.py
├── gameplay_validator.py
├── mystery_database_plan.md
├── requirements.txt
├── README.md
├── GETTING_STARTED.md
└── Choose Your Mystery*.pdf  ← concept documents

NOT YET IN REPO (to be created):
├── cli.py                    ← extraction pipeline CLI  [LOST IN SESSION 3]
├── part_registry.py          ← part sampling / lookup table [LOST IN SESSION 3]
├── app.py                    ← Gradio UI [LOST IN SESSION 3]
└── mystery_database/
    └── extractions/          ← one JSON per book (283 books extracted so far)
                                [LOST IN SESSION 3 — check local machine]
```

---

## The Six Test Mysteries

Defined in `test_mysteries.py` as Python dataclasses. Titles:

1. Murder on Mars
2. Art Theft in Amazonia
3. The Alchemical Forgery of the Abbasid Court
4. The Ghost-Signal of the Victorian Deep
5. A Steampunk Sabotage
6. The Genetic Identity Heist of New Tokyo

These are **hand-written metadata only** — not full prose. As a result, P2
narrative fields (resolution, investigator, culprit, reveal_mechanic) are
intentionally sparse. This is expected and correct. See Extraction Table below.

---

## The Corpus

- **File:** `mystery-crime-books/train-00000-of-00001.parquet`
- **Size:** ~14MB (and growing — do NOT commit to git)
- **Contents:** 359 mystery/crime books
- **Location:** User's local machine only
- **Status:** Not yet pushed to any remote storage

### Recommended handling
Use **git-lfs** or keep the parquet out of git entirely and document the
download/acquisition steps. Never commit large growing binary files to the
main git repo.

---

## P1 / P2 Extraction Protocol

### P1 fields (structural — found in any mystery)
| Field              | Description                                         |
|--------------------|-----------------------------------------------------|
| `crime`            | What happened                                       |
| `victim`           | Who was harmed                                      |
| `closed_world`     | Why suspects cannot leave                           |
| `culprit_and_motive` | Who did it and why                                |
| `resolution`       | How it was solved                                   |
| `investigator`     | Who is doing the detecting                          |
| `alibi`            | The key false/misleading alibi                      |
| `reveal_mechanic`  | How the truth comes out                             |

### P2 fields (narrative depth — from full text)
`red_herring`, `suspects[]`, `evidence[]`, `timeline`, `setting_detail`

### Extraction quality comparison

| Field              | Test mysteries (metadata only) | Corpus books (full novel text) |
|--------------------|-------------------------------|-------------------------------|
| crime              | High                          | High                          |
| victim             | High                          | High                          |
| closed_world       | High                          | Medium                        |
| culprit_and_motive | Low                           | High                          |
| resolution         | Low                           | High                          |
| investigator       | Low                           | High                          |
| alibi              | High                          | Low                           |
| reveal_mechanic    | Medium                        | High                          |

**Interpretation:** Test extractions are strong where metadata was explicit
(crime, setting, alibi). Corpus extractions are strong where those P1 elements
are embedded in actual prose (resolution, investigator, culprit). The pipeline
is working correctly — this contrast is expected and desirable.

---

## The Part Registry

A **flattened sampling pool** for procedural mystery generation.

- One row per *part*, not per book
- A single book contributes ~8 rows (one crime, one investigator, etc.)
- Each row: `type | content | setting_tags | source_id`
- The app samples compatible parts by matching `setting_tags` to the player's prompt

### Current state
| Source              | Rows  |
|---------------------|-------|
| 6 test mysteries    | 48    |
| 283 corpus books    | 0 (unprocessed) |
| **Total**           | **48** |

### Target state (after corpus ingestion)
| Source              | Rows    |
|---------------------|---------|
| 6 test mysteries    | 48      |
| 359 corpus books    | ~2,000+ |
| **Total**           | **~2,000+** |

The `as_part_registry_rows()` function in `test_mysteries.py` can bootstrap
the registry during development before the corpus is ingested.

---

## Session History

### Session 1 & 2 — Planning & corpus acquisition
- Defined P1/P2 protocol
- Acquired the mystery-crime-books parquet corpus (359 books)
- Wrote early `mystery_generator.py` and data acquisition scripts

### Session 3 — Extraction pipeline (WORK LOST — NOT PUSHED)
- Wrote `cli.py`, `part_registry.py`, `app.py`
- Ran extraction on the corpus (283 books extracted, output to `mystery_database/extractions/`)
- Attempted `--end 10` validation run
- **NONE OF THIS WAS PUSHED.** Check local machine for these files.

### Session 4 (this session) — Recovery & scaffolding
- Confirmed Session 3 files are missing from repo
- Created `test_mysteries.py` (6 test mysteries as permanent constants)
- Created `SESSION_STATE.md` (this file)
- Created `end_of_session.sh` (automated sync script)
- Next priority: recover Session 3 files from local machine OR rebuild

---

## Immediate To-Do List

### Blocker — recovery
- [ ] Check local machine for `cli.py`, `part_registry.py`, `app.py`, `mystery_database/`
  - Run: `find ~/SocialGaming -name "*.py" | sort` and `ls -la ~/SocialGaming/`
  - If found: stage, commit, push immediately using `end_of_session.sh`
  - If lost: rebuild (see below)

### Blocker — corpus
- [ ] Decide on corpus storage strategy (git-lfs vs. external link vs. .gitignore + docs)
- [ ] Make corpus available for extraction run

### Extraction
- [ ] Run `python cli.py extract --protocol P1P2 --end 10` — validate quality
- [ ] Full corpus run: `python cli.py extract --protocol P1P2` (359 books → ~2,000+ parts)

### Product
- [ ] Wire `app.py` to `part_registry.py` (replace freeform LLM with part registry sampling)
- [ ] Deploy `app.py` to HuggingFace Spaces

### Quality / feedback loops
- [ ] Add coherence validator — checks P1 chain before outputting a mystery
- [ ] Add quality signal capture — per-session "did this mystery work?" flag
- [ ] Weight part registry by signal — high-rated parts sampled more

---

## Rebuild Guide (if Session 3 files are unrecoverable)

If `cli.py`, `part_registry.py`, `app.py` cannot be found locally:

**`cli.py`** — extraction CLI. Entry point: `python cli.py extract --protocol P1P2 [--end N]`
- Reads parquet from `mystery-crime-books/`
- For each book, calls Claude API with P1/P2 extraction prompt
- Writes one JSON per book to `mystery_database/extractions/<id>.json`

**`part_registry.py`** — the sampling pool
- Reads all JSONs from `mystery_database/extractions/`
- Flattens into rows: `{type, content, setting_tags, source_id}`
- `sample_parts(prompt, n_per_type)` — returns compatible parts for a given prompt

**`app.py`** — Gradio UI
- Text input: player describes the mystery setting/prompt
- Calls `part_registry.sample_parts(prompt)`
- Assembles parts into a playable mystery card
- Displays mystery to player group
