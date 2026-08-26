# F5 checklist — walking the Godot client by hand

The procedure for running the desktop client in the engine and checking the single-player path.
Zero cost through step 15; only the last two spend API credits.

**Why this exists.** Godot reports a bad node path only at runtime, and reports a control that was
never connected not at all — it just does nothing when clicked. `scripts/check_godot_wiring.py`
catches what it can by reading the scene and script files, but reading a scene is not the same as
loading it, and Session 36 proved the gap twice. This checklist is the part no script can do.

**Status (Session 36, August 26 2026).** Steps 1–9 have been walked by the owner and pass. The
interrogation screen failed at step 16, was fixed, and has **not been re-run**. Steps 10–17 are
unverified. See `SESSIONS.md` Session 36.

---

## What you need

| | |
|---|---|
| Engine | Godot 4.x. `godot/project.godot` declares 4.6; 4.7.2 opens it fine (see *Expected noise*) |
| Backend | The FastAPI server on port 8000, in its own terminal |
| API key | **Not needed** for steps 1–15. `get_client()` in `server/main.py` builds the Anthropic client lazily, so the server boots and serves the whole saved-mystery route with no key set |
| Time | ~15 minutes for the free route |

---

## Setup

### 1. Sync the repo

```
git pull
git log --oneline -3 -- godot/
```

Run this from the **repo root**, not from `server/` — several git subcommands resolve paths
relative to your working directory.

### 2. Start the backend

Its own terminal window, left alone for the whole session. It runs in the foreground and dies with
its terminal.

```
cd server
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --port 8000
```

Confirm from a second terminal:

```
curl -s http://localhost:8000/health
```

Expect a JSON body reporting ok true.

If pip refuses with *externally-managed-environment* (Homebrew Python), use a venv — and remember
to re-activate it in any new terminal:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If the port is held by an orphaned server: `lsof -ti:8000 | xargs kill`

---

## Opening the project

### 3. Click **Edit**, not **Run**

In the Godot project manager, select Choose Your Mystery and click **Edit**.

A fresh clone has no `godot/.godot/` directory — that is the generated import cache and is never
committed. **Run** from the project manager fails on it with *"Can't run project: Assets need to be
imported first."* Let the initial import finish.

Then check **Project → Project Settings → Autoload**: three entries, `GameState`, `ApiClient`,
`NetworkManager`.

### 4. Press F5

F5 is an editor shortcut, so the editor window must have focus. The play button in the top-right
toolbar does the same thing, and is the way round a laptop F-key bound to brightness. Either
launches `res://scenes/ui/MainMenu.tscn` in a **new window**, separate from the editor. F8 or the
stop button ends it.

**Expect:** the title Choose Your Mystery, four buttons — New Game (Solo), Multiplayer, Browse
Saved Mysteries, Quit — and the status line turning green with "Backend connected."

Red *"Backend unreachable"* means step 2's server died, not that the client is broken.

---

## The free route — no API spend

### 5. Browse Saved Mysteries

**Expect:** a centred window listing **17** rows, each formatted title, difficulty, star rating.

*Not a bug:* "The Murder at Tokyo" and "The Great Cookie Caper of Sesame Street" each appear
twice. Two files on disk resolve to the same slug. Cosmetic and pre-existing.

### 6. Dismiss the popup two ways

Click Close. Reopen. Then dismiss with the window's own close gesture. Both must work — a Godot
`Window` does not hide itself on `close_requested`, the handler has to, and that handler was
unconnected until Session 34.

### 7. Select "Whiteout at Shackleton Base"

The richest case on disk: 8 characters, 4 suspects, 5 investigation areas, coherence passed.

**Expect:** the popup closes and `CaseDisplay.tscn` loads.

If clicking a row does *nothing*, the `item_selected` signal is unconnected again and
`_on_browse_item_selected` is dead code.

### 8. Read the case screen

**Expect:** title, setting, crime, characters and evidence all populated — no empty panels, no raw
null. Two buttons: Interrogate Suspects and Make Accusation. A rating row.

### 9. Open Make Accusation

**Expect** exactly four names, and no orange warning line:

| Suspect | Culprit? |
|---|---|
| Dr. Marcus Hale | **yes** |
| Dr. Yuki Tanaka | no |
| Bjorn Larssen | no |
| Dr. Felix Caron | no |

The dropdown is built from `characters` filtered to the suspect role, so victims and witnesses must
not appear — 8 characters in, 4 names out.

### 10. Accuse the wrong person — Dr. Yuki Tanaka

Submit, then confirm at the dialog.

**Expect** the result screen: a red verdict naming who you accused and who the culprit was, a full
solution breakdown (culprit, method, motive, key evidence, how to deduce), a rating row, and the
buttons Play Again and Review Case.

A blank screen, or an error naming a node path under `ScrollContainer`, means the Session 34 fix to
`result_screen.gd` regressed. That commit was the entire end-of-game screen.

### 11. Rate the mystery

Click a rating button. This posts to the rate endpoint — a disk write, no Claude call. Expect no
error, and the request visible in the server terminal.

### 12. Both exits from the result screen

Review Case returns to `CaseDisplay`; Play Again returns to `MainMenu`. Two different
destinations, neither throwing.

### 13. The culprit-matching regression — "The Stolen Star of Smurf Village"

Browse to it and accuse **Smurfwick the Craftsmurf**.

This mystery's culprit field is a prose sentence naming two culprits, so exact matching marked
*every* accusation wrong, including both right ones.

**Expect:** correct. Repeat with **Smurfadel, Master of Adornment** — also correct.
**Smurfodex, Keeper of the Great Smurf Tome** — wrong.

*Cosmetic, expected:* the verdict prints the raw culprit field, so you will see the whole prose
string. Ugly, not a failure. The underlying cause is CLAUDE.md item 18, still open.

### 14. Interrogation screen — reachable without spending

From a loaded case, click Interrogate Suspects. **Do not ask a question yet** — the screen itself
is free, each question is not.

**Expect:** the header reading Phase 1, budget text reading "Ask as many questions as you like."
(not *0 questions remaining*), and a populated suspect dropdown.

This screen failed in Session 36 with *"Cannot call method 'add_item' on a null value"* because
`Interrogation.tscn` used `#` comment lines, which drop the node declared after them. That is
fixed; this step confirms it.

### 15. Stop and take stock

If 1–14 pass, the free route is clear. Everything below spends money and can wait.

---

## The paid route — costs API credits

### 16. One interrogation · ~1 call

Ask a single question. Expect an in-character reply in the history.

### 17. One generation · 1 large call

New Game (Solo) → a scenario → Generate Mystery. Real generations on record have taken 112 to
1,992 seconds, so give it room.

**Expect:** the prompt box, the moderation disclaimer visible beneath it, the cinematic-brief
checkbox, and on success a brand-new case on `CaseDisplay`.

Watch for JSON parse errors. An old batch summary shows 13 of 14 generations failing that way; it
is from March and 16 have generated cleanly since, but this run is the confirmation nobody has done.

---

## Expected noise — none of these are failures

- **A missing icon warning.** `godot/project.godot` points its icon at a path under an `assets`
  directory that does not exist in the repo. Cosmetic window icon, nothing else.
- **Godot 4.7 modifying files.** Opening a 4.6 project in 4.7 re-saves `godot/project.godot` and
  `godot/scenes/ui/MainMenu.tscn`, which then show as modified in `git status`.
- **Untracked `.uid` files.** Godot generates these sidecars for scripts that lack them.

---

## What this checklist does not test

- **Two defensive branches on the accusation screen.** All 17 saved mysteries have suspects, and
  every culprit resolves to at least one of them — so neither the no-suspects message nor the
  unsolvable warning can fire from saved data. They have no test case on disk.
- **Multiplayer entirely** — lobby, room codes, the share mechanic, the WebSocket path, and
  `server/static/mobile.html`. Stage 3.
- **APF** — CLAUDE.md item 23, not built.
- **Anything visual.** Whether the screens read well is a judgement only a human at the screen can
  make. Note it as you go.

---

## If something breaks

Capture three things:

1. The **step number**.
2. The **Output panel** text, verbatim.
3. The **Debugger** tab's stack trace if it froze rather than misbehaved.

Two diagnostic habits that paid off in Session 36:

- **The error line is often the symptom, not the cause.** A null-method error names the first line
  that touched a null, not the reason it was null. The running scene's **remote inspector** shows
  which node references resolved and which are empty, which is what actually located the bug.
- **A parse error appears only when its scene first loads.** Godot parses a script when the scene
  needs it, so a broken screen stays silent until you click through to it.
