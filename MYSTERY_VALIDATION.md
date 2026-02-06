# Mystery Validation: Coherence & Uniqueness

The two hardest problems in procedural mystery generation.

---

## Problem 1: How Do We Ensure the Mystery "Makes Sense"?

A generated mystery fails if the culprit's motive doesn't fit their character, if the timeline has holes, or if the evidence chain has logical gaps. A priest who steals for no reason, a locked room with an unexplained exit, a witness who knows something they shouldn't — any of these breaks immersion and trust.

### The Constraint System

Every mystery is built on a set of **hard constraints** that must all pass before a mystery is playable. Think of it like a compiler — if the mystery doesn't compile, it doesn't ship to players.

#### Constraint 1: Character-Motive Alignment

The culprit's motive must be consistent with their archetype, backstory, and social position.

```
RULE: motive must be reachable from character profile

Example - Valid:
  Character: Temple Priest, devout, but secretly in gambling debt
  Motive: Stole the statue to pay off debts
  Why it works: The gambling debt creates a credible pressure
                that overrides the character's public persona.
                The contradiction IS the story.

Example - Invalid:
  Character: Temple Priest, devout, no financial pressure
  Motive: Stole the statue for profit
  Why it fails: Nothing in the character profile explains
                why this person would betray their role.
```

**How we enforce it:**

The Mystery Engine generates characters and motives together, not separately. The MKD provides **motive-archetype compatibility scores**:

```
archetype: "religious_authority"
compatible_motives:
  - cover_up (high)        # protecting the institution
  - blackmail (high)       # someone has leverage over them
  - passion (medium)       # forbidden relationship
  - financial (medium)     # BUT requires a "pressure" backstory element
  - ideology (medium)      # crisis of faith, competing belief
  - random_greed (reject)  # doesn't work without justification
```

After the LLM generates the mystery skeleton, a **validation pass** checks:

```python
def validate_character_motive(culprit, motive):
    # 1. Does the motive category match the archetype?
    compatibility = MKD.get_compatibility(culprit.archetype, motive.category)
    if compatibility == "reject":
        return FAIL("Motive incompatible with archetype")

    # 2. If compatibility is "medium", is there a justifying backstory element?
    if compatibility == "medium":
        if not culprit.backstory_contains(motive.required_justification):
            return FAIL("Motive requires backstory justification not present")

    # 3. Does the character have opportunity? (Were they present? Did they have access?)
    if not timeline_allows(culprit, crime.time, crime.location):
        return FAIL("Character couldn't have been at the crime scene")

    # 4. Is the motive discoverable? (Can players find evidence pointing to it?)
    if not evidence_chain_supports(motive, available_clues):
        return FAIL("No evidence path leads to this motive")

    return PASS
```

#### Constraint 2: Timeline Consistency

Every character needs an alibi or a gap. The real culprit's alibi must be breakable.

```
RULE: All character timelines must be internally consistent.
      The culprit's timeline must contain exactly one exploitable gap.

Timeline Validation:
  For each character:
    - Where were they at each hour before/during/after the crime?
    - Can at least one witness confirm or deny their location?
    - Does any physical evidence place them somewhere unexpected?

  For the culprit specifically:
    - Their stated alibi must have a flaw
    - That flaw must be discoverable through available actions
    - At least two pieces of evidence must contradict their alibi
```

#### Constraint 3: Evidence Chain Completeness

Players must be able to solve the mystery using ONLY the clues available in the game. No leaps of faith.

```
RULE: There must exist a logical path from starting knowledge
      to the correct accusation, using only discoverable evidence.

The Solution Path:
  Starting facts (given to all players)
       |
       v
  Clue A (discoverable at Location 1)
       |
       v
  Clue B (revealed by Witness 2 when shown Clue A)
       |
       v
  Clue C (found via Research when cross-referencing A + B)
       |
       v
  Conclusion: Culprit + Motive + Method

Validation checks:
  1. Can Clue A be found without prerequisites? (entry point exists)
  2. Does each clue logically lead to the next? (no dead ends)
  3. Are there enough clues for the total player count?
     (With 4 players and 75% sharing, the solution path can't
      require ALL clues — some will be withheld)
  4. Are there at least 2 independent paths to the solution?
     (Redundancy in case one path gets withheld)
```

#### Constraint 4: Red Herring Distinguishability

Red herrings must be ultimately distinguishable from real clues. A red herring that's indistinguishable from truth makes the mystery unsolvable.

```
RULE: Every red herring must be refutable by at least one
      discoverable piece of evidence.

Example:
  Red herring: "The merchant was seen near the temple that night"
  Refutation: "Harbor records show the merchant's ship arrived
               the NEXT morning — he wasn't in Athens yet"

  If the refutation doesn't exist, the red herring becomes
  an unsolvable false accusation trap. That's not fun.
```

### The Validation Pipeline

After the LLM generates a mystery, it goes through an automated gauntlet:

```
LLM generates mystery skeleton
         |
         v
+------ VALIDATION PIPELINE ------+
|                                  |
|  1. Character-Motive Alignment   |  <-- Does each character's
|     [PASS/FAIL]                  |      motive fit who they are?
|                                  |
|  2. Timeline Consistency         |  <-- Can the culprit have done it?
|     [PASS/FAIL]                  |      Do alibis hold or break correctly?
|                                  |
|  3. Evidence Chain Completeness  |  <-- Is the mystery solvable with
|     [PASS/FAIL]                  |      available clues?
|                                  |
|  4. Red Herring Distinguishability| <-- Can false leads be eliminated?
|     [PASS/FAIL]                  |
|                                  |
|  5. Difficulty Calibration       |  <-- Is it too easy or too hard
|     [PASS/WARN]                  |      for the player count?
|                                  |
|  6. Narrative Coherence (LLM)    |  <-- Second LLM pass: "Read this
|     [PASS/FAIL]                  |      mystery as a player. Does it
|                                  |      make sense? Any plot holes?"
|                                  |
+----------------------------------+
         |
    All PASS?
    /        \
  YES         NO
   |           |
   v           v
 Ship to    Regenerate failed
 players    components (up to
            3 retries, then
            fallback to curated
            mystery from MKD)
```

**Key insight:** Constraint checks 1-5 are **deterministic** (code logic, graph traversal, rule checks). Constraint 6 is a **second LLM call** acting as a "reader/editor" to catch narrative-level issues the rules can't. This two-layer approach catches both structural and narrative failures.

### The Fallback: Curated Mystery Library

If generation fails validation 3 times, the system falls back to a **pre-built, human-tested mystery** from the MKD that matches the player's prompt as closely as possible. This means:

- Players never get a broken mystery
- The curated library grows over time (human-written + validated AI mysteries that passed with high scores)
- The fallback is invisible to players — they don't know if they got a generated or curated mystery

---

## Problem 2: How Do We Ensure Uniqueness?

"Art Theft in Athens" should produce a different mystery every time. Not just cosmetically different — structurally different. Different culprit, different motive, different evidence chain, different NPCs.

### The Randomness Architecture

Uniqueness is enforced at multiple layers:

#### Layer 1: Combinatorial Explosion from the MKD

The MKD provides a massive pool of interchangeable components. Even for a single prompt, the combinations are enormous:

```
"Art Theft in Athens"

Crime sub-types:     inside job, heist, opportunistic, forgery swap, ransom
Culprit archetypes:  guard, merchant, priest, rival collector, foreign spy, artist
Motives:             debt, revenge, ideology, blackmail, passion, cover-up
Methods:             tunnel, bribery, distraction, forgery, inside access
Settings:            temple, agora, private villa, harbor warehouse, archive
Cast size:           5-8 NPCs drawn from ~50 compatible archetypes
Evidence types:      physical, testimonial, documentary, forensic

Conservative estimate of unique combinations:
  5 × 6 × 6 × 5 × 5 × C(50,6) × 4^10 ≈ billions
```

The engine doesn't pick the same combination twice. Each game session stores a **fingerprint** (culprit archetype + motive + method + plot structure) and the engine checks against recent sessions.

#### Layer 2: Prompt Decomposition & Recombination

The engine doesn't treat "Art Theft in Athens" as a monolithic prompt. It decomposes it:

```
Input: "Art Theft in Athens"

Decomposed:
  crime_type:  theft
  sub_domain:  art (sculpture? painting? manuscript? jewelry?)
  setting:     Athens (ancient? modern? mythological?)
  tone:        unspecified (engine chooses randomly)

Each sub-element is independently varied:
  Run 1: Stolen sculpture  + Ancient Athens + noir tone
  Run 2: Forged painting   + Modern Athens  + comedic tone
  Run 3: Missing manuscript + Mythological  + thriller tone
```

By varying the interpretation of the player's prompt, even identical inputs produce fundamentally different scenarios.

#### Layer 3: Structural Variation via Plot Templates

The MKD contains distinct **plot structure templates** that determine how the mystery unfolds, regardless of the specific crime:

```
Template A: "Classic Whodunit"
  - Crime happens, multiple suspects, one is guilty
  - Evidence narrows the field gradually
  - Solution comes from eliminating the innocent

Template B: "The Wrong Suspect"
  - Early evidence points strongly to one person
  - Investigation reveals they're being framed
  - Real culprit is the framer

Template C: "Hidden Identity"
  - The culprit is not who they claim to be
  - An NPC is using a false identity
  - Key evidence reveals the deception

Template D: "Conspiracy"
  - Multiple NPCs are involved
  - Players must figure out who is in on it vs. who is innocent
  - Testimony contradictions reveal the network

Template E: "The Unexpected Motive"
  - The crime wasn't what it appeared to be
  - A theft was actually a cover-up; a murder was actually an accident
  - The real crime is underneath the surface one

Template F: "The Accomplice Flip"
  - Two culprits, one willing to betray the other
  - The right interrogation approach turns one against the other
  - Players must figure out which accomplice to pressure
```

The engine rotates templates and ensures the same player group doesn't get the same template in consecutive sessions.

#### Layer 4: Session History & Deduplication

```
+-------------------+       +--------------------+
| New Mystery       |       | Session History DB  |
| Generation        +------>+                    |
|                   |       | Recent fingerprints:|
| Fingerprint:      |       | - theft/guard/debt  |
| theft/merchant/   |       | - murder/spouse/rage|
| blackmail/tunnel  |       | - fraud/lawyer/greed|
|                   |       |                    |
+-------------------+       +--------------------+
                                     |
                            Does new fingerprint
                            match any recent one?
                            /              \
                          NO               YES
                          |                 |
                        Ship it         Regenerate with
                                        forced variation
```

The fingerprint is a tuple of: `(crime_subtype, culprit_archetype, motive, method, plot_template)`

If any player in the session has seen that exact combination in their last N games, the engine forces at least one element to change.

#### Layer 5: NPC Personality Randomization

Even if two mysteries share the same structure, NPCs behave differently:

```
Same archetype "nervous witness" in two different games:

Game 1: Stammers, avoids eye contact, reveals info if shown physical evidence
Game 2: Over-explains, talks too much, reveals info if caught in contradiction

The MKD provides personality trait pools. The engine randomly
assigns traits from the pool, so the same archetype plays
differently every time.
```

#### Layer 6: The LLM's Own Creativity

On top of all the structured variation, the LLM introduces its own narrative creativity:
- Unique character names, backstories, and dialogue
- Atmospheric details specific to the setting
- Unexpected connections between characters
- Creative evidence types the MKD may not have catalogued

The LLM is seeded with a high temperature for creative elements (names, descriptions, dialogue) and low temperature for structural elements (evidence chains, timelines, logic).

```
Temperature strategy:
  Mystery skeleton (logic):     temperature = 0.3  (precise, consistent)
  Character names/backstories:  temperature = 0.9  (creative, varied)
  Scene descriptions:           temperature = 0.8  (atmospheric, unique)
  Evidence chain:               temperature = 0.2  (logical, airtight)
  NPC dialogue:                 temperature = 0.7  (natural, personality-driven)
```

### Uniqueness Guarantee Summary

```
Same prompt entered 10 times:

 Run  | Sub-domain  | Setting     | Template         | Culprit       | Motive
 -----|-------------|-------------|------------------|---------------|--------
  1   | Sculpture   | Ancient     | Classic Whodunit | Guard         | Debt
  2   | Painting    | Modern      | Wrong Suspect    | Collector     | Revenge
  3   | Manuscript  | Mythological| Hidden Identity  | Foreign spy   | Ideology
  4   | Jewelry     | Ancient     | Conspiracy       | Priest+Guard  | Blackmail
  5   | Sculpture   | Ottoman-era | Unexpected Motive| Artist        | Cover-up
  6   | Fresco      | Modern      | Accomplice Flip  | Curator+Thief | Passion
  7   | Pottery     | Classical   | Classic Whodunit | Merchant      | Greed
  8   | Painting    | WWII-era    | Wrong Suspect    | Soldier       | Orders
  9   | Mosaic      | Byzantine   | Hidden Identity  | Monk          | Faith
  10  | Tapestry    | Ancient     | Conspiracy       | Senate faction| Power
```

No two are alike in structure, even though the prompt was identical.

---

## How These Two Systems Work Together

Coherence and uniqueness are in tension. The more random you make something, the harder it is to keep consistent. The architecture resolves this with a clear separation:

```
UNIQUENESS happens at SELECTION time:
  - Which components to combine
  - Which template to use
  - Which interpretation of the prompt

COHERENCE happens at VALIDATION time:
  - After components are assembled
  - Rule-based + LLM-based checks
  - Reject and retry if broken

The MKD is the bridge:
  - It provides pre-vetted compatible combinations
  - Character archetypes come with compatible motives already mapped
  - Plot templates come with required evidence structures built in
  - This means most random selections WILL pass validation
  - Only edge cases need regeneration
```

This is why the MKD is the most important long-term investment. The richer the database, the more variety is possible WITHOUT sacrificing coherence. A thin MKD means either repetitive mysteries or incoherent ones. A deep MKD delivers both novelty and logic.
