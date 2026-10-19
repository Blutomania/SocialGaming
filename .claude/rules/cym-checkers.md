---
# Loads only when a session touches CYM's scripts/. Root-anchored ("/"), so
# MYF's mind-your-friends/scripts/ never pulls it in — see cym.md's header.
paths:
  - "/scripts/**"
  - "/.claude/rules/cym-checkers.md"
---
# CYM — checkers and tools

Split out of `.claude/rules/cym.md` in Session 51, so that only a session working in `scripts/`
loads the full table. `.claude/rules/cym.md` keeps the short list to run before handing anyone a build.

All zero API cost, no Godot binary needed, and each has already caught a real bug. The two
checks that run **inside** the engine are in `.claude/rules/cym-godot.md`.

## Checkers

| Script | Catches |
|---|---|
| `scripts/check_godot_wiring.py` | Broken `$NodePath`s, `@onready` type mismatches, unreferenced interactive controls, autoload calls with the wrong arity, `#` lines in a `.tscn`, an undeclared `theme_type_variation`, Python-style docstrings, implicit string concatenation. All scenes, autoloads and scripts. **Necessary, not sufficient** — it reads scene files rather than loading them |
| `scripts/check_narrative.py` | A person the solution reasons about who is not in the cast; a declared link that does not resolve; a chain step nothing supports; elimination that does not leave exactly the culprit. `scripts/test_narrative_checks.py` proves those fire |
| `scripts/check_solvability.py` | Not a gate — a report on the link between evidence and solution across every generated mystery |
| `scripts/check_mystery_playable.py` | A `solution.culprit` naming no listed suspect, an empty suspect list, a blocking coherence failure served anyway |
| `scripts/check_rule_coverage.py` | A hard assertion in the generation prompt that no rule enforces (untriaged), an inventory entry naming a dead rule id, an inventoried assertion deleted. Its standing UNENFORCED list is its real output; `scripts/test_rule_coverage.py` proves it can fail |
| `scripts/check_decisions.py` | Both games' decision records: an item labelled open that another says is finished, a missing or duplicate number, a cited item that resolves to nothing — in the instructions files, `docs/`, and source comments |
| `scripts/check_doc_claims.py` | Docs drifted from code — a referenced file that does not exist, a *path:line* past its file, a backticked quoted string absent from every code file |
| `scripts/build_palette.py --check` | The palette drifted between `palette.py`, `Palette.gd`, `mobile.html` and the ground clear colour |
| `scripts/test_palette.py` | Every ink/background pair against its WCAG floor |
| `scripts/build_icons.py --check` | Generated icon copies drifted from `icons/`; refuses a raster in an SVG wrapper. `--report` describes the sources |
| `scripts/build_brand.py --check` | `godot/assets/brand/` drifted from `brand/NEWnegative_CYM.svg` / `NEWorganic_cym.svg`. Byte-exact, no recolouring — a brand mark is a fixed identity |
| `scripts/check_brand_contrast.py` | How much of a mark's ink sits at or below 2.5:1 against the ground. Run on any artwork before wiring it in (item 17) |

## Tests

| Script | Proves |
|---|---|
| `scripts/test_apf.py` | The rhythm: round 1 asks nothing, sharing is cumulative and monotone, the difficulty ladder separates, the board never greys a face on a narrowing, disclosure names whoever sat on it, a client is sent only its own half |
| `scripts/test_casefiles.py` | The three assignment constraints, each refusing a mystery that violates it |
| `scripts/test_share_rule.py` | The share minimum is defined once — server and client used to disagree in 6 of 18 cases |
| `scripts/test_gate_and_ledger.py` | The gate's refusals and the ledger's arithmetic; a legacy mystery is `unjudged`, not rejected; CPAM divides by accepted, not attempts |
| `scripts/test_arrangement.py` | The wiring pass refuses both false positives it actually made, wires a genuine carrier, withholds a wiring that makes the mystery worse |
| `scripts/test_ws_push.py` | Starts its own server, listens as the host's socket, and fails if a player's join, round or share never reaches it, or anyone is announced twice. The only check that listens rather than polls — Session 49's round-2 stall was exactly this |
| `scripts/test_icons.py` | The icon flatten, genuinely random assignment, the suspect tag fallback chain (species → non-human → gender-matched human → full pool), and refusal of a drifted `icons/suspect/tags.json` |
| `scripts/test_localization_preserves_traits.py` | `pronouns`/`presentation` survive `localize_mystery()` untouched |
| `scripts/test_registry_staleness.py` | A moved-on corpus rebuilds the registry and an unchanged one does not |
| `scripts/test_crime_scene_map.py` | Overlapping or off-canvas rooms, a misplaced witness, a non-deterministic layout |
| `scripts/test_background_field.py` | The BACKGROUND layout |
| `scripts/test_extraction_fatal_errors.py` | A batch stops on an account-level API failure and continues past a per-source one |

## Needs a running server

`scripts/walk_apf_game.py` plays a whole four-round APF game over real HTTP — create, join,
assignment, rounds, disclosure, accusation, result — on the mystery already on disk, with **no API
key**. Start the server first. Session 42 found two defects with it that every unit test passed.

`scripts/seat_players.py <ROOM>` fills three seats for a solo F5 walk; see `.claude/rules/cym-godot.md`.

## Not checkers, run locally

`scripts/cpam.py` (cost per accepted mystery, pass rate, rejections by rule, from
`mystery_database/ledger.jsonl`); `scripts/backfill_ledger.py` (idempotent, `--go` to write);
`scripts/wire_pointers.py` (exonerations nothing reveals; `--coverage` for suspects with no
witness); `scripts/preview_background_field.py` (the BACKGROUND field as SVG over real screen
text, `--sheet` for title extremes); `scripts/compare_extraction_models.py`;
`scripts/extract_from_pdfs.py` (one new source; always `--dry-run` an anthology first);
`scripts/upgrade_p1_to_p1p2.py` (item 19; prints the plan, `--go` spends).
