## Lesson: Evaluation Should Be Game-Centric
**Date:** 2026-02-20
**Mistake:** Initial evaluation metrics were data-centric (completeness, transposability, novelty) — abstract and subjective.
**Correction:** User clarified the score must reflect actual game playability: can it be solved in ≤4 rounds through Q&A and player sharing?
**Rule:** Going forward, always anchor evaluation metrics to the game's concrete rules (round count, sharing mechanic, solvability) — not to data quality abstractions.

## Lesson: Clue Discovery Is Player-Driven, Not Passive
**Date:** 2026-02-20
**Mistake:** Assumed clues might be revealed passively (dealt out, auto-discovered).
**Correction:** Clues are discovered only through player action — interrogating witnesses/suspects or examining locations.
**Rule:** Any system that "gives" clues to players (dealing, broadcasting, auto-revealing) is wrong. Players must take an action to surface each clue.

## Lesson: Round Length Is 4 Minutes, Not Less
**Date:** 2026-02-20
**Rationale:** Players interrogate NPCs within each round. With 2 actions per player at ~60 seconds each, plus time for the sharing decision, 4 minutes is the minimum viable round length.
**Rule:** Round length is 4 minutes. Do not shorten it without explicit approval — interrogation time is the primary gameplay activity.

## Lesson: GenAI Cost Is Bounded — Only Video + Avatars
**Date:** 2026-02-20
**Decision:** Generative AI in the production game is limited to exactly two touchpoints: (1) the crime event intro video (generated once per mystery), and (2) player avatars (generated once per session per player). All other gameplay — including NPC interrogation responses — uses scripted data generated at mystery-creation time by the pull scripts.
**Rule:** Do not add Claude API calls inside the gameplay loop. NPC responses come from `discovery_hints` in the PlayableMystery data. Real-time AI during gameplay is out of scope unless explicitly approved.

## Lesson: Architecture Must Support Text → Graphic Expansion Without Rewriting Core Logic
**Date:** 2026-02-20
**Decision:** The prototype is text-only (console). Production adds a graphic web UI and generative media. These are separate layers (Presentation, Generation) that sit above the Core game logic. The core never changes.
**Rule:** Always implement game logic in platform-agnostic classes. Use abstract base classes for anything visual or media-generating so text stubs can be swapped for real implementations. See `docs/game_design.md` for the layer diagram.
