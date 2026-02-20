# Choose Your Mystery — Game Design Document

**Last updated:** 2026-02-20

---

## 1. Core Mechanic: The 75% Sharing Rule

Players must share **at least 75%** of the clues they discover each round. They may withhold up to 25%. This is the primary strategic tension — hoarding is punished (you need other players' clues to solve the mystery), but selective withholding creates meaningful advantage.

---

## 2. Round Structure

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Round length | 4 minutes | Enough time for 2 focused interrogations at ~60s each, plus the sharing decision |
| Actions per player per round | 2 | Limits information gain, forces strategic target selection |
| Action types | Interrogate NPC, Examine location | Covers testimony and physical evidence |
| Rounds per game | 4–6 | Tuned by RSE metric in PlayabilityCalculator |

Clues are discovered by **player action** — asking questions of witnesses/suspects, or examining locations. Nothing is handed to players passively.

At round end, each player sees what they discovered and submits their sharing decision before the next round opens. The 75% floor is enforced by the system.

---

## 3. Interrogation Model: Hybrid Topic Anchoring

### The Problem

Open-ended Q&A preserves player agency but wastes time on off-topic questions. Multiple-choice menus prevent that but make the experience feel like a quiz rather than an investigation.

### The Solution: Topic Anchoring + Free-Form Question

When a player opens an interrogation, they see a menu of **what this NPC can speak to** before typing anything:

```
Interrogating: DR. STERLING
You can ask about:
  • His whereabouts between 9–11pm
  • His relationship with Lord Ashworth
  • His knowledge of forensic techniques
  • The medication he prescribed recently

Your question: ___________________________
```

The player writes their own question, but the visible topic list means:
- Players know what is worth asking without spoiling the answers
- Off-topic questions become self-policing (players can see they're wasting a turn)
- Claude (in the production version) responds in character with natural dialogue, not a canned menu entry

When a question misses the visible topics, the NPC responds in character: *"I'm not sure what that has to do with anything."* The NPC's confusion is the feedback — not a system error message.

### How Topics Are Generated

Topics come from the `PlayableMystery` data produced by the pull scripts. Claude generates them **at mystery-creation time**, not at gameplay time. Each clue in the causal chain is tagged with:

- `discoverable_from` — which character or location reveals it
- `topic_tag` — the topic anchor label shown to the player
- `discovery_hints` — 2–3 example questions that unlock it (used to pre-generate scripted responses)

This means **no AI calls happen during gameplay** for interrogation. See Section 5.

---

## 4. Schema Additions (PlayableMystery)

Two additions are required to support topic-anchored interrogation:

### `PlayableCharacter`
```python
interrogation_topics: List[str]
# e.g. ["alibi_9_to_11pm", "relationship_with_victim", "forensic_knowledge", "recent_prescription"]
# Populated by CausalChainExtractor at mystery-creation time.
```

### `PlayableClue`
```python
discoverable_from: str          # character_id or location_id that reveals this clue
topic_tag: str                  # maps to one entry in the character's interrogation_topics
discovery_hints: List[str]      # example questions Claude used to pre-generate scripted responses
```

---

## 5. Generative AI Cost Boundaries

GenAI is **expensive when used per-interaction**. This design deliberately limits it to two one-time costs per game session:

| Touchpoint | When Generated | Estimated Cost | Technology |
|------------|---------------|----------------|------------|
| Crime event video | Once per mystery (not per session) | ~$0.50–$2.00 | Sora / Runway / Pika |
| Player avatars | Once per player per session | ~$0.04–$0.20 each | DALL-E 3 / Stable Diffusion |

**Everything else is scripted or rule-based:**
- NPC dialogue during interrogation → pre-generated at mystery-creation time
- Round management, sharing logic, clue graph traversal → pure Python
- Playability scoring → deterministic algorithms (BFS, Monte Carlo simulation)

The pull scripts (e.g. `pull_script_03_causal_chain.py`) use Claude **once per mystery** to extract the causal clue graph and generate scripted NPC responses. After that, gameplay costs are predictable and near-zero.

---

## 6. Prototype-to-Production Architecture

The codebase is built in three layers. The prototype implements only the **Core** layer with text stubs for everything above it. Production swaps in real implementations without touching the game logic.

```
┌─────────────────────────────────────────────────────┐
│  GENERATION LAYER  (optional, swappable)             │
│  CrimeEventBase    → TextCrimeEvent                  │
│                    → GeneratedCrimeVideo (future)    │
│  AvatarBase        → TextAvatar                      │
│                    → GeneratedAvatar (future)        │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRESENTATION LAYER  (swappable)                     │
│  GameRunnerBase    → ConsoleGameRunner (prototype)   │
│                    → WebGameRunner (future)          │
│  NPCResponderBase  → ScriptedNPCResponder (always)   │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  CORE GAME LOGIC  (platform-agnostic, never changes) │
│  PlayableMystery — clue graph (already built)        │
│  ActionSystem    — interrogate, examine              │
│  RoundManager    — timer, action budget, turn order  │
│  SharingEngine   — 75% rule enforcement              │
│  PlayabilityCalculator — MCD, RSE, UST (already built│
└─────────────────────────────────────────────────────┘
```

### Layer Contracts (Abstract Base Classes)

```python
class CrimeEventBase:
    def present(self, mystery: PlayableMystery) -> None:
        """Display/play the crime event intro."""
        raise NotImplementedError

class AvatarBase:
    def assign(self, player_name: str) -> str:
        """Return avatar description or asset URL for the player."""
        raise NotImplementedError

class NPCResponderBase:
    def respond(self, character_id: str, topic_tag: str, question: str,
                mystery: PlayableMystery) -> str:
        """Return the NPC's in-character response and surface the relevant clue."""
        raise NotImplementedError

class GameRunnerBase:
    def run(self, mystery: PlayableMystery, players: List[str]) -> None:
        """Execute the full game loop."""
        raise NotImplementedError
```

### Prototype Implementations (Text-Only)

| Interface | Prototype Implementation | Behaviour |
|-----------|--------------------------|-----------|
| `CrimeEventBase` | `TextCrimeEvent` | Prints `mystery.scenario_description` to console |
| `AvatarBase` | `TextAvatar` | Returns `"{player_name} the {random_role}"` |
| `NPCResponderBase` | `ScriptedNPCResponder` | Looks up pre-written response in `discovery_hints`; returns it verbatim |
| `GameRunnerBase` | `ConsoleGameRunner` | Console I/O loop with `input()` prompts, simulated timer |

### Production Expansions

| Interface | Production Implementation | Notes |
|-----------|--------------------------|-------|
| `CrimeEventBase` | `GeneratedCrimeVideo` | Call video gen API; return URL. Generated once, cached. |
| `AvatarBase` | `GeneratedAvatar` | Call image gen API (DALL-E 3 / SD). Cached per session. |
| `GameRunnerBase` | `WebGameRunner` | WebSocket-based; same core logic, real-time sync |
| `NPCResponderBase` | `ScriptedNPCResponder` | **Does not change.** Scripted responses remain for cost reasons. |

---

## 7. Prototype Scope

The text-only prototype validates:
- [ ] Round loop (timer, action budget, turn rotation)
- [ ] Topic-anchored interrogation (topic display → free-form input → scripted response)
- [ ] 75% sharing enforcement at round end
- [ ] Clue graph traversal (can players reach the solution?)
- [ ] Win condition (player submits correct culprit identification)

The prototype does **not** implement:
- Video or image generation
- Multiplayer networking
- Persistent player accounts
- Web UI

---

## 8. File Locations

| Artefact | Location |
|----------|----------|
| Core schema + playability metrics | `pull_script_03_causal_chain.py` |
| Example PlayableMystery | `causal_chain_output/causal_the_locked_room_mystery.json` |
| Prototype game engine (to be built) | `game_engine/` |
| This document | `docs/game_design.md` |
