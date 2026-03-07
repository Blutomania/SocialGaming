# Choose Your Mystery — Claude Code Instructions

## Project Overview
AI-powered social mystery party game. Players investigate crimes, interrogate AI characters,
and compete to solve the case first. Core innovation: the 75% information-sharing mechanic.

Key files:
- `app.py` — Streamlit UI (Claude-powered, P1-P4 taxonomy)
- `part_registry.py` — Mystery atomization and part sampling
- `cli.py` — Terminal entry point (5 subcommands)
- `extraction_protocols.py` — P1–P4 taxonomy definitions
- `SESSIONS.md` — Master session log and consolidated to-do list
- `RESEARCH_FINDINGS.md` — Writer-grounded mystery taxonomy (C1–C6, M1–M8, F1–F12)

Active branches:
- `claude/document-research-findings-LdlIV` — UI, research, session log (this session)
- `claude/mystery-versioning-system-TPblK` — Part registry, CLI, corpus pipeline

## Session Summary Protocol — MANDATORY

### When to trigger
You MUST run `python scripts/session_summary.py` and commit the result in ANY of these situations:
1. The conversation is approaching context limits (long thread, many tool calls)
2. A major feature or phase is complete
3. The user signals they are done for the session
4. You are about to be replaced by a new session
5. Any natural stopping point after significant work

### What the summary must include
Run the script, which will auto-populate most fields. Then ensure SESSIONS.md contains:
- Branch name and latest commit hash
- Every file created or modified (with one-line description)
- Every decision made (architecture, naming, approach)
- What is incomplete and the exact next step to resume
- Any blockers or open questions

### How to run it
```bash
python scripts/session_summary.py
```
The script will prompt for session notes, generate the summary, append it to SESSIONS.md,
and commit automatically.

For a fully automated summary with no prompts:
```bash
python scripts/session_summary.py --auto
```

### NEVER end a session without updating SESSIONS.md
If you cannot run the script (e.g. missing dependencies), write the summary directly into
SESSIONS.md manually and commit it before stopping.

## Coding Conventions
- Python 3.8+
- Claude model: `claude-sonnet-4-6`
- Mystery parts use `SOURCE(INDEX)` notation: `C(4)`, `F(2)`, `A(6)`
- Extraction protocols: P1 Skeleton (C1-C6), P2 Architecture (M1-M8), P3 Craft (F1-F8), P4 Texture (F9-F12)
- All generated mysteries must include a `provenance_recipe` field
- UI is Streamlit; backend scripts are CLI via `cli.py`

## Current To-Do (as of March 7, 2026)
See `SESSIONS.md` for the full prioritized list. Top items:
1. Step 6: `python cli.py extract --protocol P1P2 --end 10` (validate before full corpus run)
2. Step 7: Full corpus run (`python cli.py extract --protocol P1P2`)
3. Wire `app.py` to `part_registry.py`
4. Deploy `app.py` to HuggingFace Spaces
