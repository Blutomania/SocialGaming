# Mystery Data Extraction Requirements

## Purpose

This document defines what structured data must be extracted from source mystery
content (novels, true crime, screenplays, etc.) to power the **Choose Your Mystery**
game engine.

The game is an AI-powered multiplayer party game where players investigate a crime
scene, interrogate AI-driven NPCs, assemble a crime board, strategically share
information (75% shared / 25% withheld), and compete to be the first to correctly
name the culprit.

**Important:** Locations and environments are chosen by the game-player at setup
time. Source material locations are NOT extracted. Instead, the extracted content
must be flexible enough to be re-appropriated into any player-chosen setting.

---

## 1. Core Crime/Incident

The foundational facts of the mystery. This is what the AI uses to generate the
crime scene the players walk into.

| Field                  | Description                                                                 | Required |
|------------------------|-----------------------------------------------------------------------------|----------|
| `crime_type`           | Primary classification: murder, theft, fraud, kidnapping, disappearance, sabotage | Yes |
| `victim_name`          | Name of the victim                                                          | Yes      |
| `victim_description`   | Who the victim is and why they matter (role, status, relationships)          | Yes      |
| `what_happened`        | Concise description of the crime itself (1-3 sentences)                     | Yes      |
| `how_it_happened`      | The actual method/mechanism of the crime (the ground truth)                  | Yes      |
| `discovery_scenario`   | How and when the crime was discovered; what players initially "walk into"    | Yes      |
| `surface_observations` | What is immediately obvious at the scene (visible to all players on arrival) | Yes      |
| `hidden_details`       | What only careful investigation or expertise would reveal                    | Yes      |

---

## 2. Main Characters (NPCs)

Each major character is an NPC that players can interrogate. The extraction must
capture enough depth for the AI to convincingly roleplay the character during
live questioning.

### Per-Character Fields

| Field                     | Description                                                              | Required |
|---------------------------|--------------------------------------------------------------------------|----------|
| `name`                    | Character's full name                                                    | Yes      |
| `role`                    | One of: victim, suspect, witness, bystander                              | Yes      |
| `is_culprit`              | Boolean. Exactly one suspect must be the actual culprit                   | Yes      |
| `description`             | Brief physical/social description                                        | Yes      |
| `personality_traits`      | 3-5 adjectives/phrases describing temperament and demeanor (e.g., "evasive under pressure", "charmingly deflective", "blunt and confrontational") | Yes |
| `speech_style`            | How they talk: formal, colloquial, nervous, curt, verbose, etc.          | Yes      |
| `motive`                  | Why this character could plausibly be the culprit. Even non-culprits need a believable motive to maintain suspense | Yes (for suspects) |
| `relationship_to_victim`  | Their connection to the victim: spouse, business partner, rival, employee, etc. | Yes |
| `relationship_to_others`  | Key connections to other characters in the cast                          | No       |
| `knowledge_about_crime`   | What this character knows about the crime: their alibi, what they saw/heard, their whereabouts | Yes |
| `knowledge_that_helps_solve` | Specific information this character possesses that helps the player solve the mystery. These are the "clue atoms" players extract during interrogation | Yes |
| `what_they_hide`          | What this character will deflect on, lie about, or refuse to discuss. Critical for making interrogations feel adversarial | Yes |
| `interrogation_behavior`  | How they behave under questioning: cooperative, hostile, tearful, lawyered-up, etc. | Yes |

### Constraints

- Minimum 4 characters, maximum 8
- Exactly 1 victim
- Exactly 1 culprit (flagged via `is_culprit`)
- At least 2 suspects with plausible motives (including the actual culprit)
- At least 1 witness

---

## 3. Mystery Type

A single primary classification that affects how the game plays, how NPCs behave,
and what kind of investigation the players conduct.

| Type           | Description                                                        |
|----------------|--------------------------------------------------------------------|
| `whodunit`     | Classic "who did it" - multiple suspects, one is guilty             |
| `locked_room`  | The "how" is as important as the "who" - impossible circumstances   |
| `cozy`         | Lighter tone, social relationships, no graphic violence             |
| `procedural`   | Evidence-driven, forensic, methodical investigation                 |
| `espionage`    | Deception layers, hidden allegiances, double agents                 |
| `heist`        | Reconstructing what happened, who planned it, how it was executed   |

Additionally, capture 2-5 **secondary tags** for flavor (e.g., "noir", "historical",
"high_society", "revenge", "inheritance").

---

## 4. Key Clues and Revelations

Clues are the atomic units of information that players discover, share (or withhold),
and assemble on their crime board. Every clue must be a **self-contained,
discrete piece of information** because individual clues are what players select
in the 75/25 sharing interface.

### 4a. Physical Clues

Found through scene investigation.

| Field              | Description                                                          |
|--------------------|----------------------------------------------------------------------|
| `description`      | What the clue is (e.g., "a broken watch stopped at 2:15 AM")        |
| `what_it_implies`  | What this clue suggests or proves                                    |
| `is_red_herring`   | Boolean                                                              |

### 4b. Testimonial Revelations

Extracted from NPCs during interrogation.

| Field              | Description                                                          |
|--------------------|----------------------------------------------------------------------|
| `description`      | The piece of information revealed                                    |
| `source_character` | Which NPC reveals this when questioned                               |
| `what_it_implies`  | What this revelation suggests or proves                              |
| `is_red_herring`   | Boolean                                                              |

### 4c. Red Herring Strategy

Each red herring (physical or testimonial) must also include:

| Field                  | Description                                                      |
|------------------------|------------------------------------------------------------------|
| `false_conclusion`     | What wrong answer this herring points toward                     |
| `why_misleading`       | Why it seems convincing but is actually wrong                    |
| `what_disproves_it`    | What other clue or revelation exposes it as a red herring        |

### 4d. Solution Chain

An **ordered sequence** of clues/revelations that, when assembled together, proves
who the culprit is and how the crime was committed. This is what the game engine
checks against when a player "names the culprit."

| Field              | Description                                                          |
|--------------------|----------------------------------------------------------------------|
| `step_number`      | Order in the logical chain (1, 2, 3...)                              |
| `clue_reference`   | Which physical clue or testimonial revelation this step uses         |
| `reasoning`        | How this step connects to the next, building the case                |

Minimum 3 steps, maximum 8.

---

## 5. Timeline

A chronological sequence of what actually happened (the ground truth), which the
player reconstructs over the course of the game. This is NOT shown to the player;
it is the source of truth that the AI game engine uses to validate player theories
and drive NPC responses.

| Field       | Description                                                              |
|-------------|--------------------------------------------------------------------------|
| `order`     | Sequence number                                                          |
| `time`      | When this event occurred (relative or absolute, e.g., "2 hours before discovery", "11:45 PM") |
| `event`     | What happened                                                            |
| `actors`    | Who was involved                                                         |
| `witnesses` | Who, if anyone, observed this event (and what they actually saw)         |

---

## 6. Source Metadata

Standard bibliographic fields for tracking provenance.

| Field              | Description                           |
|--------------------|---------------------------------------|
| `title`            | Original work title                   |
| `author`           | Author name                           |
| `publication_year` | Year of publication                   |
| `source_url`       | Where the text was obtained           |
| `source_type`      | novel, screenplay, true_crime, etc.   |
| `license_type`     | public_domain, fair_use, licensed     |
| `processed_date`   | When extraction was performed         |

---

## Design Notes

- **Locations are NOT extracted.** The game-player chooses the setting at game
  time. The extracted content (characters, motives, clues) must be abstract enough
  to be transplanted into any setting the player picks.
- **Every clue is a discrete unit.** This is critical for the 75/25 information
  sharing mechanic. Players see a checklist of individual clues and select which
  to share.
- **Characters must be deep enough to interrogate.** Personality, speech style,
  what they hide, and how they behave under pressure are all required fields
  because the AI must roleplay these NPCs in real-time conversation.
- **The solution chain must be logically sound.** A player should be able to
  follow the chain from clue to clue and arrive at the correct culprit through
  reasoning, not guessing.
