# Getting Started — Choose Your Mystery

The actual system. Not the old demo.

---

## Prerequisites

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or set in HuggingFace Secrets
```

---

## Run the app

```bash
streamlit run app.py
```

1. Type a setting prompt: `"1920s Harlem jazz club, Prohibition era"`
2. Optionally check **Generate cinematic brief** for a video-gen prompt
3. Click **Generate Mystery** — takes ~30 seconds (2 API calls)
4. Read the case, interrogate suspects, make your accusation

---

## Generate mysteries from the terminal

```bash
# Basic
python cli.py generate --setting "Ancient Rome, 44 BC, Senate chamber"

# With options
python cli.py generate \
  --setting "Deep-sea oil platform, North Sea, winter storm" \
  --num-players 6 \
  --cinematic          # adds video-gen brief
  --yes                # skip confirmation prompt
```

Generated mysteries are saved to `mystery_database/generated/`.

## Browse saved mysteries

```bash
python -c "
import json, glob
for f in sorted(glob.glob('mystery_database/generated/*.json')):
    d = json.load(open(f))
    sol = d.get('solution', {})
    coh = d.get('_coherence', {})
    status = 'PASS' if coh.get('passed', True) else 'FAIL'
    print(f\"{d.get('title','?'):50} [{status}]  culprit={sol.get('culprit','?')}\")
"
```

---

## Validate a mystery

```bash
python cli.py check mystery_database/generated/<filename>.json
```

---

## Build the part corpus (one-time, costs API credits)

```bash
# Test run first — free, uses 6 pre-extracted test mysteries
python cli.py extract --protocol P1 --dry-run

# Real extraction (P1 only, cheapest)
python cli.py extract --protocol P1

# Full corpus (P1+P2, ~359 books)
python cli.py extract --protocol P1P2
```

---

## How generation works

```
Your prompt
  → part_registry.py samples ~12 compatible parts from 1,469-part corpus
  → Claude assembles them into a structured JSON mystery        (call 1)
  → localization.py renames characters to fit the era           (call 2, or skip if modern)
  → coherence_validator.py checks logical consistency           (free)
  → [opt-in] generate_cinematic_brief()                         (call 3)
  → saved to mystery_database/generated/
```

Full architecture: `docs/WIRING.md`

---

## Cost per mystery

| Step | Tokens | Notes |
|---|---|---|
| Generation | ~8,000 | always |
| Localization (cache miss) | ~1,200 | first time for an era |
| Localization (cache hit) | ~900 | subsequent same-era mysteries |
| Localization (modern) | 0 | skipped entirely |
| Cinematic brief | ~2,000 | opt-in only |
| Coherence check | 0 | free |

Era localization rules are cached in `mystery_database/localization_cache/` — the
system gets cheaper as you explore more settings.

---

## Key files

| File | What it does |
|---|---|
| `app.py` | Streamlit UI |
| `cli.py` | Terminal interface (generate, extract, check, browse, solve) |
| `part_registry.py` | 1,469-part corpus; sampling logic |
| `coherence_validator.py` | P1 causal-chain + witness + evidence checks |
| `localization.py` | Era-appropriate name/occupation localization with disk cache |
| `extraction_protocols.py` | P1–P4 taxonomy |
| `docs/WIRING.md` | Full technical wiring (read before touching generation) |
| `CLAUDE.md` | Instructions for AI coding assistants |
| `SESSIONS.md` | Session-by-session history and next steps |
