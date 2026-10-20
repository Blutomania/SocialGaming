---
# Loads only when a session touches CYM's Godot client. Root-anchored ("/"), so
# MYF's own mind-your-friends/godot/ never pulls it in — see cym.md's header.
paths:
  - "/godot/**"
  - "/.claude/rules/cym-godot.md"
---
# CYM — Godot client notes

Split out of `.claude/rules/cym.md` in Session 51 so that a CYM session working on generation
or the server never pays for it. Applies to `godot/` only; Mind Your Friends' Godot client has
its own notes in `mind-your-friends/CLAUDE.md`.

## The client

- **Godot 4.x, GDScript 2.0** — typed, `class_name` declarations. `project.godot` declares 4.6;
  the owner runs 4.7.
- **Five autoloads**, in order: `GameState`, `ApiClient`, `NetworkManager`, `Style`, `Chrome`.
  `Style` is second-to-last because it reads `Palette.gd`; `Chrome` is last because it adds the
  brand mark on top of whatever theme Style already set. Adding one: register it in
  `project.godot` **and** confirm it appears in Project → Project Settings → **Globals** (called
  *Autoload* on 4.6 and earlier).
- **Backend URL** is `ApiClient.SERVER_URL`, default `http://localhost:8000`.
- **No Godot binary is reachable from a session** — outbound is allowlist-only and the engine's
  hosts are not on it (tested, Session 38). Rendering is verified only on the owner's machine,
  so every report on a Godot change says whether it has been seen.
- **A fresh clone is opened with Edit, not Run** — `.godot/` is a generated import cache and is
  not committed. `.uid` files *are* committed; Godot 4.4+ expects them.
- **`project.godot` cannot hold documentation.** Opening it in 4.7 rewrites the file, deleting
  every `;` comment, bumping `config/features` to `"4.7"` and dropping `[rendering]`. Discard that
  diff rather than committing it (`docs/F5_CHECKLIST.md`).
- **State the type.** `:=` on `Dictionary.get()` infers `Variant`, which the engine treats as a
  parse error — Session 36 lost a whole screen to it (item 22).

| File | Purpose |
|---|---|
| `godot/scripts/autoloads/GameState.gd` | Current mystery, phase, history |
| `godot/scripts/autoloads/ApiClient.gd` | HTTP + WebSocket wrapper for the backend |
| `godot/scripts/autoloads/NetworkManager.gd` | ENet singleton — registered, called by nothing (see `.claude/rules/cym.md` → Architecture) |
| `godot/scripts/autoloads/Style.gd` | Builds the global Theme from `Palette.gd` and puts it on the scene-tree root, so every screen restyles with no `.tscn` edited. Hand-written |
| `godot/scripts/autoloads/Chrome.gd` | The brand mark, upper-left, on every screen — added to `get_tree().root` for the same reason. Loads the **generated** `godot/assets/brand/negative_mark.svg`; source `brand/NEWnegative_CYM.svg`, mirrored by `scripts/build_brand.py` |
| `godot/scripts/theme/Palette.gd` | **Generated** from `palette.py` — never hand-edit |
| `godot/scripts/theme/Icons.gd` | Which icon a thing gets; its header explains why that must carry no information (suspect portraits are the one, deliberate exception — item 35) |
| `godot/scripts/data/MysteryData.gd` | Typed wrapper for mystery JSON |
| `godot/scripts/ui/apf_round.gd` | The APF play screen — the suspect board, and *What You Know* (your casefile plus everything shared with you, one column since Session 51) with the share decision, on one screen, because the board is what makes withholding legible |
| `godot/scripts/tools/` | `EditorScript`s, run inside the engine (below) |

The screens are in `.claude/rules/cym.md` → Key files; their look is `docs/STYLE_GUIDE.md` and item 36.

## Three failure modes Godot will not report

Each has cost a screen in this project. They are why the checkers exist.

| Failure | What it looks like |
|---|---|
| A GDScript parse error | The scene's static nodes render and nothing responds. No runtime error. |
| A `#` comment line in a `.tscn` | The node declared after it is silently dropped at load. |
| A theme item name the engine does not have | A silent no-op — the control keeps its engine default. |

`scripts/check_godot_wiring.py` catches what can be caught by reading files (table in
`.claude/rules/cym-checkers.md`). It reads scenes rather than loading them, so it is
**necessary, not sufficient**; the two below are the only checks that use Godot's own loader.

## Checks that run inside the engine

`EditorScript`s — File → Run, free, owner's machine only.

| Script | Catches | Last run |
|---|---|---|
| `godot/scripts/tools/VerifyScenes.gd` | A node a `.tscn` declares that does not survive loading, a node whose runtime class differs from the scene's, a scene root that lost its script. Reads `scenes/ui/` itself | Session 49: ten of ten `ok` |
| `godot/scripts/tools/ApplyTheme.gd` | A theme item name the engine does not have; also writes the editor's theme preview (`cym_theme.tres`, generated, never a source) and reports whether the fonts resolved | Session 49: clean. Re-run after any `Style.gd` change; expect `MISSES none` |

## Running it

Start the server from the repo root with `python3 -m uvicorn server.main:app --port 8000`, then
F5. **`python3 -m uvicorn`, not bare `uvicorn`** — the launcher is missing from `PATH` on
Homebrew Python, on `pip install --user` and outside an active venv, and *command not found*
there reads like a missing dependency when the package is installed.

**A solo walk needs the other seats filled:** APF needs at least two players, so run
`python3 scripts/seat_players.py <ROOM>` while the host is still in the lobby — before *Begin* —
because `open_session()` snapshots who is in the room. It joins three players and pays each share
checkpoint with the bare minimum; it never accuses or closes the case. The walk itself is
`docs/F5_CHECKLIST.md`.
