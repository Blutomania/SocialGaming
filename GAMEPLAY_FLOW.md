# Choose Your Mystery - Gameplay Flow

## Example Scenario: 4 Players, Remote Play

---

### Step 1: Create Game
**Actor:** User 1 (Host)

User 1 opens the app and enters a scenario prompt:

```
Prompt: "Art Theft in Athens"
```

The Mystery Engine processes the prompt and generates:
- Full backstory (what was stolen, from where, when)
- Cast of NPCs (witnesses, suspects, guards, informants, red herrings)
- Evidence chain (the solvable path to the truth)
- Searchable locations (museum, marketplace, docks, suspect residences)
- Red herrings and misdirection layers

Generation takes ~10-15 seconds. Host sees a loading screen with thematic visuals.

---

### Step 2: Invite Friends
**Actor:** User 1 (Host)

User 1 shares access to the game via:
- **Link** - Shareable URL (e.g., `chooseyourmystery.com/game/XK7F`)
- **Code** - 4-6 character alphanumeric code entered on the join screen
- **Key** - Direct invite via contacts/friends list (logged-in users)

Host can see a lobby showing who has joined and who is pending.

```
Game Lobby: "Art Theft in Athens"
  [x] User 1 (Host)   - Joined
  [ ] User 2           - Invited, pending...
  [ ] User 3           - Invited, pending...
  [ ] User 4           - Invited, pending...
```

---

### Step 3: Friends Join
**Actors:** Users 2, 3 & 4

Invited players open the link/enter the code/accept the invite and land in the game lobby. No account required for basic play (alias entry only). Optional login for persistent stats and avatar history.

```
Game Lobby: "Art Theft in Athens"
  [x] User 1 (Host)   - Ready
  [x] User 2           - Joined
  [x] User 3           - Joined
  [x] User 4           - Joined

  [ START GAME ] <-- visible to Host when all players joined
```

---

### Step 4: Avatar Creation
**Actors:** All Users (simultaneous)

Each player creates their detective avatar using the generative AI engine:

- **Input options:**
  - Text prompt ("A grizzled Athenian philosopher-detective")
  - Style selection (realistic, cartoon, noir, etc.)
  - Upload a selfie for AI-styled transformation
- **Output:** A unique character portrait + name + brief persona

All players create avatars simultaneously to minimize wait time. Players can see each other's avatars as they're generated.

```
User 1: "Inspector Nikos"    - weathered face, olive cloak
User 2: "Lyra the Scribe"   - young, sharp-eyed, ink-stained hands
User 3: "Captain Demos"     - broad-shouldered, ex-military
User 4: "Oracle Thessa"     - mysterious, draped in white
```

---

### Step 5: The Incident (Cinematic Intro)
**Actors:** All Users (watch together)

A short AI-generated video plays for all players simultaneously, setting the scene:

> *The camera pans across the moonlit Parthenon. Inside the Temple of Athena,
> a guard slumps unconscious beside an empty pedestal. The golden statue of
> Athena Promachos is gone. Torchlight flickers across scattered pottery and
> a torn piece of crimson fabric caught on a column...*

**Video specs:**
- Duration: 30-60 seconds
- Generated via AI video model (e.g., Runway, Sora, Kling)
- Establishes: the crime, the setting, the mood, and 1-2 visible clues
- All players see the same video — this is the shared starting point

After the video, all players receive:
- A brief text summary of the incident
- The initial known facts (what, where, when)
- Access to the case file (updates as evidence is found)

---

### Step 6: Investigation Phase (Turn-Based)
**Actor:** One user at a time, starting with User 1

Each player's turn consists of **one prime action**. The active player's turn is semi-private — other players receive a broadcast of *what* the active player is doing, but not the details of what they learn.

#### Prime Actions (choose one per turn):

| Action | What it does | What others see |
|--------|-------------|-----------------|
| **Chase a Lead** | Follow up on a clue or tip to a new location or person | *"Inspector Nikos is chasing a lead at the docks"* |
| **Talk to a Witness** | Interrogate an NPC — AI-powered conversation | *"Inspector Nikos is talking to Athena, a witness"* |
| **Look for Clues** | Search a location for physical evidence | *"Inspector Nikos has found a clue!"* |
| **Do Research** | Analyze evidence, cross-reference alibis, forensics | *"Inspector Nikos is doing research at the archive"* |
| **Solve the Crime** | Make an accusation (see Step 8) | *"Inspector Nikos thinks he's solved it..."* |

#### What Other Players See (The Broadcast)

While waiting, other players see a real-time activity feed:

```
+---------------------------------------------------+
|  LIVE FEED                                        |
|                                                    |
|  Inspector Nikos is talking to Athena,            |
|  a witness at the Temple...                       |
|                                                    |
|  [Animated avatar of Nikos shown in conversation] |
|                                                    |
|  Meanwhile, review your case board:               |
|  [ VIEW CASE BOARD ]  [ REVIEW SHARED EVIDENCE ]  |
+---------------------------------------------------+
```

Players know the *type* of action and the *target* (which NPC, which location) but NOT:
- What the witness said
- What specific clue was found
- What the research revealed

This keeps spectators engaged and gives them meta-information (who is Nikos suspicious of?) without revealing the substance.

#### Example Turn (User 1):

```
Prime Action: Talk to a Witness — the night guard

  Others see: "Inspector Nikos is talking to the Night Guard"

  Nikos learns (privately):
  - Guard heard two voices before the theft
  - Guard was drugged, not knocked out
  - Guard noticed crimson fabric on the floor
```

User 1's turn ends. Before passing, they hit the **Information Sharing** step.

#### Free Actions (no turn cost):
- Review your case board at any time (during your turn or while waiting)
- Read shared evidence from other players
- Add personal notes and annotations

---

### Step 7: Information Sharing / Retention
**Actor:** Active player (before passing turn)

This is the core strategic mechanic. After completing their investigation actions, the player reviews everything they learned this turn:

```
+---------------------------------------------------+
|  YOUR FINDINGS THIS TURN                          |
|                                                    |
|  [x] Torn crimson fabric at museum entrance       |
|  [x] Guard heard two voices before the theft      |
|  [ ] Fabric traced to merchant-class dye           |
|  [x] Guard was drugged, not knocked out           |
|                                                    |
|  You must share 3 of 4 items (75%)                |
|  ----------------------------------------         |
|  Sharing: 3  |  Keeping private: 1                |
|                                                    |
|  [ CONFIRM & PASS TURN ]                          |
+---------------------------------------------------+
```

**Rules:**
- Player must share **75%** of findings (rounded up)
- Player keeps **25%** private for competitive advantage
- Shared information goes to ALL other players' case boards
- Private information is visible only to the player who found it
- Players can add annotations/theories to shared items

**Strategy:** What you withhold matters. Keeping the fabric analysis private means you're the only one who knows the thief is merchant class — giving you a lead on narrowing suspects.

**Turn then passes to the next player:**

```
Round 1:  User 1 --> User 2 --> User 3 --> User 4
Round 2:  User 1 --> User 2 --> User 3 --> User 4
Round 3:  User 1 --> User 2 --> User 3 --> User 4
```

Each player repeats Step 6 (investigate) and Step 7 (share/retain) on their turn.

---

### Step 8: Resolution
**Trigger:** After 3 full rounds OR when any player calls for an accusation

#### Option A: Accusation (Early End)
At any point during their turn, a player can declare: **"I know who did it."**

They must provide:
- **WHO** — The culprit (select from NPC cast)
- **WHY** — The motive
- **HOW** — The method / key evidence supporting the accusation

```
+---------------------------------------------------+
|  MAKE YOUR ACCUSATION                             |
|                                                    |
|  Culprit:  [ Merchant Stavros           v]        |
|  Motive:   [ Debt to foreign collectors  v]       |
|  Key Evidence: [ Select up to 3 items    v]       |
|                                                    |
|  WARNING: A wrong accusation eliminates you       |
|  from winning. You remain in the game as a        |
|  participant but cannot win.                       |
|                                                    |
|  [ SUBMIT ACCUSATION ]    [ BACK TO INVESTIGATING]|
+---------------------------------------------------+
```

**If correct:** Game ends. That player wins.
**If wrong:** Player **loses their next turn** as a penalty. They remain in the game and can still win, but skip one turn of investigation. They can attempt another accusation on a future turn (at the same risk).

#### Option B: End of Round 3 (Forced Resolution)
If no one has made a correct accusation after 3 rounds, ALL remaining players must simultaneously submit their accusations:

- All accusations are locked in secretly
- Reveal happens simultaneously
- **Correct answer wins.** If multiple players are correct, the one who assembled the most complete evidence chain wins (tiebreaker)
- If nobody gets it right, the AI reveals the solution in a cinematic recap

---

## Round Structure Summary

```
 ROUND 1              ROUND 2              ROUND 3
+---------+          +---------+          +---------+
| U1 Turn |          | U1 Turn |          | U1 Turn |
| Investigate        | Investigate        | Investigate
| Share 75%|         | Share 75%|         | Share 75%|
+---------+          +---------+          +---------+
| U2 Turn |          | U2 Turn |          | U2 Turn |
| Investigate        | Investigate        | Investigate
| Share 75%|         | Share 75%|         | Share 75%|
+---------+          +---------+          +---------+
| U3 Turn |          | U3 Turn |          | U3 Turn |
| Investigate        | Investigate        | Investigate
| Share 75%|         | Share 75%|         | Share 75%|
+---------+          +---------+          +---------+
| U4 Turn |          | U4 Turn |          | U4 Turn |
| Investigate        | Investigate        | Investigate
| Share 75%|         | Share 75%|         | Share 75%|
+---------+          +---------+          +---------+
                                           |
                      Any player may       ALL players
                      accuse early ------> must accuse
                      (risk: elimination)  (forced end)
```

---

## Key Timing Estimates

| Phase | Estimated Duration |
|-------|-------------------|
| Step 1: Create Game (AI generation) | 15-30 seconds |
| Step 2-3: Invite & Join | 1-3 minutes |
| Step 4: Avatar Creation | 2-3 minutes (simultaneous) |
| Step 5: Incident Video | 30-60 seconds |
| Step 6-7: Each Player Turn (1 prime action + sharing) | 2-4 minutes |
| Full Round (4 players) | 8-16 minutes |
| Full Game (3 rounds) | 30-50 minutes |
| **Total Session** | **~35-60 minutes** |
