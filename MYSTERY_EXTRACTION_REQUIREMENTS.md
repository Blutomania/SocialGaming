# Mystery Extraction Requirements
## Specification for Choose Your Mystery Data Pipeline

This document defines the canonical schema for extracted and generated mystery
scenarios. Every field exists to serve a specific game mechanic or generation
quality need. Nothing is extracted speculatively.

---

## Design Principles

1. **Schema serves gameplay, not data completeness.**
   Every field either (a) drives a gameplay interaction, (b) enables RAG
   retrieval quality, or (c) makes validation possible. No decorative fields.

2. **The world is player-chosen, not extracted.**
   Location and setting are supplied by the user prompt ("Murder on Mars").
   The pipeline captures *world context* (era, tech level, cultural norms)
   to ensure appropriate content is generated — not to extract a setting.

3. **Evidence is split by how it is discovered.**
   - `PhysicalClue`: found by examining locations
   - `TestimonialRevelation`: extracted by interrogating NPCs
   This maps directly to the two investigation actions in the game, and makes
   each clue a discrete, shareable unit for the 75/25 mechanic.

4. **Exactly one culprit.**
   One character has `is_culprit = True`. The game engine uses this to
   evaluate player accusations. No ambiguity.

5. **Red herrings are fully specified.**
   A red herring carries its `false_conclusion`, `why_misleading`, and
   `what_disproves_it`. This allows the validator to confirm the mystery is
   fair — misdirection must always be disprovable.

6. **The solution is an ordered logical chain.**
   `SolutionStep` entries are ordered and each references specific clue IDs.
   This gives the game engine a way to score partial solutions and give
   calibrated hints.

---

## Data Categories

### Category 1: World Context

Captures what kind of world this is, for two purposes:
- RAG retrieval: matching similar mysteries when generating from prompts
- Content validation: ensuring evidence types and character roles are appropriate

```python
world_era: str
    # ancient | medieval | early_modern | victorian | modern |
    # near_future | far_future | alternate_history

world_specific_period: str
    # Free text. E.g. "Victorian England 1890s", "Abbasid Caliphate 910 CE",
    # "Mars Colony 2157", "Steampunk alternate 1880s"

world_tech_level: str
    # pre_industrial | industrial | contemporary | advanced | sci_fi
    # Determines which evidence categories are valid (see Category 3)

world_cultural_context: str
    # Key norms, hierarchy, customs that affect the investigation.
    # E.g. "Victorian class hierarchy limits who inspectors can pressure"
    # E.g. "Corporate privacy laws block access to genetic records"

world_physics_constraints: List[str]
    # What is impossible in this world.
    # E.g. "No DNA analysis — fiber and chemical evidence only"
    # E.g. "Cannot leave the habitat — all suspects are on site"

world_flavor_tags: List[str]
    # Genre descriptors: locked_room | cozy | noir | gothic | sci-fi |
    # cyberpunk | steampunk | historical | heist | political | procedural
```

**Valid evidence categories by tech level:**

| Tech Level     | Valid Categories                                                    |
|----------------|---------------------------------------------------------------------|
| pre_industrial | physical, chemical, documentary, testimonial, environmental         |
| industrial     | physical, chemical, documentary, testimonial, environmental         |
| contemporary   | physical, chemical, documentary, testimonial, environmental, digital|
| advanced       | all 7                                                               |
| sci_fi         | all 7                                                               |

The 7 categories: `physical | biological | digital | chemical | documentary | testimonial | environmental`

---

### Category 2: Core Crime / Incident

What happened, and how. Split into what's immediately visible vs. what
requires investigation — maps directly to the opening scene presentation
and the first investigation turn.

```python
crime_type: str
    # murder | theft | forgery | sabotage | identity_theft |
    # kidnapping | espionage | fraud | disappearance

mystery_type: str
    # PRIMARY classification (one only):
    # whodunit | locked_room | cozy | procedural | espionage | heist

secondary_tags: List[str]
    # Additional flavor: ["historical", "political", "closed_environment"]

victim_identity: str
    # Who was victimized and their significance

what_happened: str
    # Complete description of the crime (for the game engine, not players)

how_it_happened: str
    # Method used (for solution validation)

discovery_scenario: str
    # How and when the crime was discovered; what players are told at game start

surface_observations: List[str]
    # What is visible immediately on arrival — no investigation needed.
    # These are presented to all players at game start.
    # E.g. "The study door is locked from inside"
    # E.g. "A body is found on the floor beside an overturned chair"

hidden_details: List[str]
    # What requires active investigation to uncover.
    # Not presented at game start — earned through play.
    # E.g. "Chemical traces of sedative in the victim's tea"
    # E.g. "The lock mechanism shows signs of external manipulation"

stakes: str
    # personal | political | corporate | existential
```

---

### Category 3: Physical Clues

Evidence discovered by examining locations. Each is a discrete, shareable unit.

```python
id: str
    # Unique identifier: clue_001, clue_002, etc.

name: str
    # Short name: "Jacket fibers in keyhole"

description: str
    # What it looks like / what it is

category: str
    # physical | biological | digital | chemical | documentary | environmental
    # (Not testimonial — that's TestimonialRevelation)
    # Must be valid for the world's tech_level

location: str
    # Where it is found in the scene

what_it_proves: str
    # What a player correctly concludes from this clue

relevance: str
    # critical | supporting | red_herring

analysis_required: bool
    # Whether it requires a tool or skill to interpret

analysis_method: Optional[str]
    # What tool/skill is needed. E.g. "Toxicology lab", "Gene sequencer"
    # Null if the clue is self-evident

# Red herring fields (populated ONLY when relevance == 'red_herring')
false_conclusion: Optional[str]
    # What it SEEMS to prove (the misdirection)

why_misleading: Optional[str]
    # Why this clue points the wrong direction

what_disproves_it: Optional[str]
    # Which other clue ID(s) or logical step undoes this red herring
    # Every red herring must be disprovable
```

---

### Category 4: Testimonial Revelations

Information extracted from NPC interrogation. Each is a discrete, shareable unit.

The `trigger_condition` is critical: it tells the game engine (or game master)
what question or action causes a character to reveal this information.
Characters should not volunteer all information immediately.

```python
id: str
    # Unique identifier: testimony_001, testimony_002, etc.

providing_character: str
    # Name of the character who gives this testimony

statement: str
    # Exact or paraphrased statement the character makes

what_it_reveals: str
    # What a player correctly concludes from this testimony

relevance: str
    # critical | supporting | red_herring

trigger_condition: str
    # What question or action causes this revelation.
    # E.g. "Ask about their whereabouts after midnight"
    # E.g. "Confront them with the fiber evidence"
    # E.g. "Ask a second time after other suspects have been interviewed"

# Red herring fields (populated ONLY when relevance == 'red_herring')
false_conclusion: Optional[str]
why_misleading: Optional[str]
what_disproves_it: Optional[str]
```

---

### Category 5: Characters

Designed for interrogation gameplay. The key split:
- `knowledge_about_crime`: what they say about their own whereabouts
- `knowledge_that_helps_solve`: what they know about others (clue atoms)

```python
name: str

role: str
    # victim | suspect | investigator | witness | bystander

is_culprit: bool
    # Exactly ONE character per mystery has this True.
    # The game engine uses this for accusation evaluation.

occupation: str
    # Setting-appropriate title

personality_traits: List[str]
    # E.g. ["paranoid", "methodical", "charming"]
    # Used to generate consistent NPC dialogue

speech_style: str
    # How they talk. E.g. "Precise and clinical; deflects with jargon"
    # Used for NPC dialogue generation

interrogation_behavior: str
    # How they respond under questioning.
    # E.g. "Cooperative but evasive about Tuesday evening"
    # E.g. "Hostile; attempts to redirect suspicion toward others"
    # E.g. "Nervous; reveals more than intended when flustered"

what_they_hide: str
    # What they are actively concealing, regardless of guilt.
    # Every character hides something — this drives interrogation depth.

relationship_to_victim: Optional[str]
    # How they relate to the victim

motive: Optional[str]
    # Why they might be guilty. Required for suspects.

alibi: Optional[str]
    # Their stated alibi. May be true or false.

knowledge_about_crime: str
    # Their account of their own actions during the crime window.
    # This is what they SAY — may contradict the ground truth.

knowledge_that_helps_solve: List[str]
    # Clue atoms players can extract through interrogation.
    # These are the seeds for TestimonialRevelation entries.
    # E.g. "Saw the suspect in the corridor at 1 AM"
    # E.g. "Heard an argument the night before the theft"

# Optional enrichment fields
faction: Optional[str]
cultural_position: Optional[str]
age: Optional[int]
archetype: Optional[str]
    # butler | spouse | rival | scientist | official | merchant | etc.
```

---

### Category 6: Solution

#### Timeline

Ground-truth chronology of what actually happened.

```python
sequence: int        # Ordering (1 = first)
time: str            # E.g. "10:30 PM", "Day 2, 0800"
event: str           # What happened
participant: str     # Who was involved
visible_to_players: bool
    # True = this was observable (corroborated by clues)
    # False = hidden truth only revealed in the solution
```

#### Solution Steps

Ordered logical chain from clues to culprit. Used by the game engine to
score partial solutions and generate calibrated hints.

```python
step_number: int     # Ordering (1 = first deduction)
clue_ids: List[str]  # Which clue_XXX or testimony_XXX IDs support this step
logical_inference: str  # What the player must reason from the clues
conclusion: str      # What this step proves
```

#### Top-level solution fields

```python
culprit_name: str          # Must match exactly one character's name
method: str                # How the crime was committed
motive: str                # Why
how_to_deduce: str         # Prose walkthrough of the full logical chain
```

---

## Validation Rules

The `gameplay_validator.py` enforces these rules on every generated mystery:

### Solvability
- At least 2 critical physical clues
- At least 1 critical testimonial revelation
- All suspects have `motive` populated
- Red herring ratio: 20-50% of total clues
- Solution's `culprit_name` matches exactly one character with `is_culprit=True`
- All `clue_ids` in SolutionSteps reference real clue/testimony IDs

### Setting Coherence
- All physical clue `category` values must be valid for `world_tech_level`
- `analysis_method` must be setting-appropriate (no "gene sequencer" in Victorian)

### Red Herring Fairness
- Every red herring must have `what_disproves_it` populated
- The disproving clue/testimony must exist in the mystery

### Information Sharing (75/25 Rule)
- Total clues (physical + testimonial) should be ≥ 8 for MEDIUM strategic depth
- At least one critical clue should require active investigation (`analysis_required=True`
  or trigger condition on a testimony) — this is the "smoking gun" worth withholding

### Faction Logic (political/corporate/existential stakes only)
- At least 2 factions defined
- At least one faction tension pair defined
- Suspects distributed across factions

---

## The Six Test Queries

These six scenarios are the canonical test set for the generator. Any schema
change must be validated against all six before being considered stable.

| # | Query | Era | Tech Level | Crime Type | Mystery Type | Key Challenge |
|---|-------|-----|------------|------------|--------------|---------------|
| 1 | Murder on Mars | near_future | sci_fi | murder | locked_room | Digital/biological evidence; isolated colony; faction: corporate vs. workers |
| 2 | Art Theft in Amazonia | modern | contemporary | theft | heist | Remote location; cultural property stakes; jungle as constraint |
| 3 | Alchemical Forgery of the Abbasid Court | medieval | pre_industrial | forgery | procedural | Non-Western historical; no modern forensics; court hierarchy limits investigation |
| 4 | Ghost-Signal of the Victorian Deep | victorian | industrial | disappearance | locked_room | Submarine environment; Victorian class norms; ambiguous crime type |
| 5 | A Steampunk Sabotage | alternate_history | industrial | sabotage | whodunit | Alternate history; steampunk tech as evidence; guild faction dynamics |
| 6 | Genetic Identity Heist of New Tokyo | near_future | sci_fi | identity_theft | heist | Genetic/digital evidence primary; corporate privacy shields; near-future Tokyo culture |

---

## File Locations

| File | Purpose |
|------|---------|
| `mystery_data_acquisition.py` | Source pipeline + schema dataclasses |
| `mystery_generator.py` | RAG-based generator from user prompts |
| `gameplay_validator.py` | Automated quality checks |
| `demo_acquisition.py` | No-API demo with pre-structured Victorian locked room mystery |
| `test_queries/` | JSON files for the six test queries |
| `MYSTERY_EXTRACTION_REQUIREMENTS.md` | This document — canonical schema spec |
| `mystery_database_plan.md` | Strategic roadmap and production architecture |
| `CLAUDE.md` | Session context protocol for future Claude sessions |

---

*Last updated: 2026-03-05*
*Session: claude/confirm-parquet-parsing-Rqios*
