---
title: Choose Your Mystery
emoji: 🔍
colorFrom: indigo
colorTo: purple
sdk: streamlit
app_file: app.py
pinned: false
license: mit
short_description: AI murder mystery party game — generate, interrogate, and solve unique cases
tags:
  - text-generation
  - game
  - llm
  - mystery
  - claude
  - social-deduction
  - interactive-fiction
  - party-game
  - streamlit
---

# Choose Your Mystery

**An AI-powered murder mystery party game.** Set the scene, interrogate the suspects, and solve the case.

You describe a setting — a 1920s jazz club, a Scottish castle, a corporate retreat — and the game generates a complete, coherent murder mystery: victim, suspects, motives, alibis, physical evidence, and a hidden culprit. Then you interrogate each character and accuse the killer.

Built on a 1,469-part corpus of classic mystery literature. Every mystery is unique.

**Core mechanic (multiplayer, coming soon):** each player must share 75% of what they learn — forcing collaboration while preserving individual advantage.

---

## How it works

1. **Describe a setting** — any era, any location (Victorian manor, space station, 1970s disco)
2. **Get a full mystery** — victim, 3–4 suspects with motives and alibis, physical evidence, hidden culprit
3. **Interrogate characters** — ask each suspect anything; the AI responds in character
4. **Make your accusation** — name the killer, the method, and the motive

Every mystery passes an automated coherence check: the causal chain from crime → victim → suspects → resolution must hold before the game begins.

---

## Run locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

Requires an [Anthropic API key](https://console.anthropic.com).

---

## For developers

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI |
| `cli.py` | Terminal entry point (`generate`, `extract`, `check`, `browse`, `solve`) |
| `part_registry.py` | 1,469-part corpus; sampling logic |
| `coherence_validator.py` | P1 causal-chain validator (zero API calls) |
| `docs/WIRING.md` | Full technical architecture |
| `CLAUDE.md` | Instructions for AI coding assistants |

---

## License

Codebase: MIT. Mystery source texts: public domain (Project Gutenberg, pre-1928).
Generated mysteries: verify AI provider terms before commercial use.
