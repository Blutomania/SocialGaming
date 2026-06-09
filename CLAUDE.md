# Choose Your Mystery — Claude Code Instructions

## Project Overview
Multiplayer social deduction mystery game. AI generates coherent murder mystery scenarios from a 1,469-part corpus. Players join via shareable code; the 75%-information-sharing mechanic forces collaboration while preserving individual advantage.

## Tech Stack
- Python 3.8+, Streamlit (`app.py`), CLI (`cli.py`)
- Claude API (`claude-sonnet-4-6`)
- JSON file store: `mystery_database/generated/`, `mystery_database/extractions/`

**Auth** — Use env var `ANTHROPIC_API_KEY` or the session token file; see pattern in `app.py`.

## Architecture
```
app.py              # Streamlit UI
cli.py              # Terminal entry (generate, extract, check, browse, solve)
part_registry.py    # 1,469-part corpus + sampling
coherence_validator.py  # Free P1 causal-chain check (no API call)
gameplay_validator.py   # 75% sharing mechanic validation
mystery_database/   # generated/, extractions/, localization_cache/
docs/WIRING.md      # Canonical generation architecture — read before touching
```

## Conventions
- **Branch**: develop on `dev/choose-your-mystery` — never commit directly to `main`
- Mystery parts use `SOURCE(INDEX)` notation (`C(4)`, `F(2)`)
- All generated mysteries include `_provenance` and `_coherence` fields
- Model: `claude-sonnet-4-6`
- No comments unless the WHY is non-obvious

## Game Design Context
P1 causal chain must be unbroken: crime → victim → closed world → culprit/motive → resolution. Run `coherence_validator.check_parts()` before Claude call, `check_mystery()` after.

**75% sharing mechanic**: Players must share 75% of evidence, keeping 25% private. `gameplay_validator.validate_information_sharing()` checks this. Needs at least 5 evidence items to create meaningful decisions.

**Multiplayer invite model**: Host generates mystery, gets a shareable code (e.g. `game/XK7F2`), shares via any channel (Jackbox/Skribbl.io model). No email/SMS infrastructure needed. First-come-first-served joining.

## Common Tasks
**Run Streamlit app**
```bash
pip install -r requirements.txt
streamlit run app.py
```

**Run CLI**
```bash
python cli.py generate --setting "1920s Paris" --genre noir
python cli.py check <mystery-id>
python cli.py browse
```

## What NOT to Do
- Never push directly to `main` (403). Always use a `claude/` branch.
- Never re-run the corpus extraction pipeline — source texts that failed were too brief; re-running produces the same results.
- Don't re-extract mysteries that already have JSON in `mystery_database/extractions/`.
- Never promise "guaranteed coherence" in output or docs — say "designed to maximize coherence."
