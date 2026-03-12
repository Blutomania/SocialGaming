---
title: Choose Your Mystery
emoji: 🔍
colorFrom: indigo
colorTo: purple
sdk: streamlit
app_file: app.py
pinned: false
license: mit
---

# Choose Your Mystery

AI-powered social mystery party game. Players investigate crimes, interrogate AI characters,
and compete to solve the case first.

**Core innovation:** the 75% information-sharing mechanic — each player must share 75% of
what they learn, forcing collaboration while preserving individual advantage.

**Current phase:** text-driven (prompt in → mystery text out). Next phase: AI-generated
opening video sequence replacing the text brief.

---

## Quick start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# Run the Streamlit app
streamlit run app.py

# Or use the CLI
python cli.py --help
```

See `docs/WIRING.md` for the full technical architecture.

---

## Key files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — prompt → mystery → interrogation → accusation |
| `cli.py` | Terminal entry point (5 subcommands: `generate`, `extract`, `check`, `browse`, `solve`) |
| `part_registry.py` | Mystery atomization and part sampling (the 1,469-part corpus) |
| `coherence_validator.py` | P1 causal-chain validator — checks crime → victim → closed_world → culprit → resolution |
| `extraction_protocols.py` | P1–P4 taxonomy definitions (Skeleton, Architecture, Craft, Texture) |
| `CLAUDE.md` | Instructions for AI coding assistants working on this repo |
| `SESSIONS.md` | Master session log and consolidated to-do list |
| `RESEARCH_FINDINGS.md` | Writer-grounded mystery taxonomy (C1–C6, M1–M8, F1–F12) |
| `docs/WIRING.md` | Technical architecture: schemas, data flow, cinematic brief wiring |

---

## Where generated mysteries live

```
mystery_database/generated/   ← all generated mysteries as JSON
mystery_database/extracted/   ← parts extracted from source texts
mystery_database/sources/     ← raw source texts
```

Browse all generated mysteries and their culprits:

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

Pretty-print a single mystery:

```bash
python -m json.tool mystery_database/generated/<filename>.json | less
```

---

## CLI reference

```bash
# Generate a mystery
python cli.py generate --setting "1920s Harlem jazz club, Prohibition era" --num-players 4

# Generate with cinematic brief (video-gen prompt)
python cli.py generate --setting "..." --cinematic

# Validate a saved mystery
python cli.py check mystery_database/generated/<file>.json

# Extract parts from a source text (P1 skeleton)
python cli.py extract --protocol P1 --source <text_file>

# Full corpus extraction (P1+P2, all sources)
python cli.py extract --protocol P1P2
```

---

## Phases

| Phase | Status | Delivery |
|---|---|---|
| Text-driven | **Current** | Prompt → mystery narrative → interrogation via text |
| Video-driven | **Planned** | Cinematic brief → AI video → opening sequence replaces text |

The `cinematic_brief` field on each mystery dict (opt-in in the UI, `--cinematic` in CLI)
is the bridge between phases. It is already structured for direct use with Sora / Runway /
Pika. See `docs/WIRING.md → Cinematic Brief`.

---

## License

Codebase: MIT. Mystery source texts: public domain (Project Gutenberg, pre-1928).
Generated mysteries: verify AI provider terms before commercial use.
