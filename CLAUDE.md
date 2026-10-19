# SocialGaming — two games, one repo

This file loads into **every** session, so it holds only what both games share. Each game's own
instructions live in their own file and load only when a session touches that game's files.

| Game | Its instructions | Its code |
|---|---|---|
| **Choose Your Mystery** (CYM) — AI murder-mystery party game | `.claude/rules/cym.md` (plus `.claude/rules/cym-godot.md` and `.claude/rules/cym-checkers.md`, loaded only for `godot/` and `scripts/`) | the repo root: `server/`, `godot/`, `scripts/`, `docs/`, the top-level `*.py` |
| **Mind Your Friends** (MYF) — social trivia with sabotage cards | `mind-your-friends/CLAUDE.md` | `mind-your-friends/` |

**Before doing anything else, open the file for the game the task is about** — `.claude/rules/cym.md`
or `mind-your-friends/CLAUDE.md`. Both also load on their own once you touch that game's files,
but a session that starts by reading `SESSIONS.md` or answering a question has touched neither.
If the task names no game, ask which.

Until Session 50 the root `CLAUDE.md` *was* CYM's file. Code comments and older docs that say
"CLAUDE.md" or "root CLAUDE.md" about CYM mean `.claude/rules/cym.md`.

## Shared by both games

- **Session protocol.** Start: `git fetch origin && git checkout main && git pull origin main`,
  branch off `main`, read the most recent block for your game in `SESSIONS.md`, and state branch,
  commit and plan. End: append a block to `SESSIONS.md` (never end a session without it), update
  the game's own file and its `docs/DECISIONS.md`, commit, push the feature branch, and tell the
  owner to sync locally.
- **`git push origin main` is rejected (403).** Open a PR and merge it once clean — letting them
  pile up caused the July 2026 branch reconciliation (CYM items 5, 6, 9). After a merge, restart
  the feature branch from the new `main`; a merged PR never takes new work.
- **A branch the harness hands you may be stale.** Compare it against `main` before trusting it.
  `dev/mind-your-friends` and the `archive/*` tags are history, not live lines of work.
- **`SESSIONS.md`** is one log for both games, append-only, newest at the top. Title each block
  with the game (`(CYM: …)` / `(MYF: …)`).
- **Item numbers are per game.** CYM's live in `docs/DECISIONS.md`, MYF's in
  `mind-your-friends/docs/DECISIONS.md`, and both have an "item 27". Say which game when citing
  one outside that game's own files. Never renumber an item.
- **The coherence engine is shared:** `coherence/` at the root. CYM's `coherence_validator.py` and
  MYF's `server_py/coherence_rules.py` both subclass its `RuleSet`; a change there affects both.
- **Words differ.** CYM is an investigation game and bans card-game vocabulary (cards, decks,
  hands, deal, played). MYF really is a card game and uses it.
- **All Claude calls are server-side.** Invoke Python as `python3`.
- **Run the doc checkers after editing any instructions file:** `python3 scripts/check_doc_claims.py`
  and `python3 scripts/check_decisions.py` (which checks both games' item lists). They read this
  file, `.claude/rules/*.md` and `docs/`; the second also reads MYF's docs and both games' source comments.
