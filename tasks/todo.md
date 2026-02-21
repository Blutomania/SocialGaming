## Task: Pull Script 03 — Causal Chain Extraction

Goal: Build the target PlayableMystery JSON schema and Script 3 (Causal Chain),
which extracts a cause→effect clue graph from mystery source text and evaluates
game playability via MCD, RSE, and UST metrics.

- [x] Read existing codebase (mystery_data_acquisition.py, demo_acquisition.py)
- [x] Define evaluation criteria: solvable in ≤4 rounds, Q&A driven, multi-player sharing
- [x] Design PlayableMystery target JSON schema (dataclasses)
- [x] Implement CausalChainExtractor (Claude API)
- [x] Implement MockCausalChainExtractor (demo, no API)
- [x] Implement PlayabilityCalculator (MCD, RSE, UST, composite score)
- [x] Write demo __main__ block and verify output
- [x] Commit and push

## Metrics Defined

| Metric | Target | Description |
|--------|--------|-------------|
| MCD (Minimum Clue Depth) | 4–8 | Fewest clues to uniquely solve |
| RSE (Round-to-Solution Estimate) | ≤4 rounds | Rounds needed with N players + 75% sharing |
| UST (Unique Solution Test) | Pass | Exactly one valid culprit |
| Playability Score | 0.0–1.0 | Composite of above |

## Results
Verified via `python pull_script_03_causal_chain.py` (demo mode, no API needed):
- 6 characters, 9 clues (7 real + 2 red herrings)
- UST: PASS | MCD: 3 | RHR: 22% | RSE: 3 rounds (3/4/5 players)
- Playability score: 0.950 — EXCELLENT
- Output saved to: causal_chain_output/causal_the_locked_room_mystery.json

---

## Task: PlayableMystery Schema — Interrogation Fields

Goal: Add `interrogation_topics` to `PlayableCharacter` and `discoverable_from`,
`topic_tag`, `discovery_hints` to `PlayableClue`. Update `CausalChainExtractor`
and `MockCausalChainExtractor` to populate them.

See `docs/game_design.md` Section 4 for field definitions.

- [x] Add fields to `PlayableClue` dataclass
- [x] Add `interrogation_topics` to `PlayableCharacter` dataclass
- [x] Update `MockCausalChainExtractor` to populate new fields with demo data
- [x] Update `CausalChainExtractor` prompt to extract and return new fields
- [x] Verify via demo run — topics display correctly per character
- [x] Commit and push

## Results
Verified via `python pull_script_03_causal_chain.py` (demo mode):
- All 6 characters have interrogation_topics populated (victim correctly has [])
- All 9 clues have discoverable_from, topic_tag, and discovery_hints
- topic_tags align with their source character's interrogation_topics list
- Playability metrics unchanged: UST PASS, MCD 3, RHR 22%, Score 0.950

---

## Task: PlayableCharacter — Setting-Agnostic Archetypes

Goal: Replace `archetype: str` (setting-specific job title) with a two-field design:
`archetype_class` (canonical, from a fixed 9-class vocabulary) and
`archetype_label` (free text, setting-specific, shown to players).

- [x] Add `ARCHETYPE_CLASSES` constant dict (9 classes, default_topics per class)
- [x] Update `PlayableCharacter` dataclass: replace `archetype` with `archetype_class` + `archetype_label`
- [x] Update `MockCausalChainExtractor` — all 6 characters use new fields
- [x] Update `CausalChainExtractor._extract_characters()` prompt + constructor call
- [x] Update CLAUDE.md — new "Character Archetypes" section, Key Classes entry
- [x] Update tasks/todo.md and tasks/lessons.md

## Results
Implemented two-field archetype split. MockCausalChainExtractor locked-room demo:
- char_victim: authority / "Nobleman"
- char_culprit: professional / "Physician"
- char_spouse: intimate_partner / "Spouse"
- char_relative: family / "Niece"
- char_witness: worker / "Butler"
- char_investigator: investigator / "Inspector"
archetype_class survives setting transplants; archetype_label changes with setting.

---

## Task: Text-Only Prototype — ConsoleGameRunner

Goal: Build `game_engine/` with the layered architecture from `docs/game_design.md`.
Implements core game loop (round timer, action budget, topic-anchored interrogation,
75% sharing enforcement, win condition) using text-only stubs.

- [ ] Create `game_engine/` package with `__init__.py`
- [ ] Define abstract base classes: `CrimeEventBase`, `AvatarBase`, `NPCResponderBase`, `GameRunnerBase`
- [ ] Implement `TextCrimeEvent` — prints scenario description
- [ ] Implement `TextAvatar` — assigns text role to player name
- [ ] Implement `ScriptedNPCResponder` — looks up `discovery_hints` from PlayableMystery
- [ ] Implement `RoundManager` — tracks round count, action budget (2 per player), timer
- [ ] Implement `SharingEngine` — enforces 75% share at round end
- [ ] Implement `ConsoleGameRunner` — orchestrates full loop with `input()` prompts
- [ ] Write `demo_game.py` to run a full game against the Locked Room Mystery (demo mode)
- [ ] Verify: game is solvable, sharing enforced, win condition reached
- [ ] Commit and push
