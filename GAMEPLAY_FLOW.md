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

Each player's turn is a private investigation session. Other players cannot see what the active player is doing. On their turn, a player can perform a set number of actions (e.g., 3-5 actions per turn):

#### Available Actions:

**A. Investigate a Location**
- Choose from available locations (museum, marketplace, docks, etc.)
- Search for clues — interactive UI reveals evidence items
- Each location may yield 1-3 clues per visit
- Some locations unlock after certain evidence is found

**B. Interrogate an NPC**
- Select a witness, suspect, or bystander from the cast list
- Real-time AI-powered conversation (text chat with the NPC)
- NPCs have personalities, secrets, and breaking points
- The right questions + the right evidence = deeper reveals
- NPCs may lie, deflect, or reveal information depending on approach

**C. Research / Forensics**
- Analyze collected evidence for deeper insight
- Cross-reference alibis and timelines
- Request forensic analysis (takes 1 action, results come back next turn or immediately depending on type)

**D. Review Case Board**
- View all personal evidence (private + shared from others)
- Organize notes, tag suspects, build theories
- No action cost — can be done freely during turn

#### Example Turn (User 1):

```
Action 1: Search the Museum entrance     --> Finds: torn crimson fabric
Action 2: Interrogate the night guard     --> Learns: guard heard two voices
Action 3: Analyze the crimson fabric      --> Result: expensive dye, merchant class
```

User 1's turn ends. Before passing, they hit the **Information Sharing** step.

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
**If wrong:** Player is eliminated from winning (can still play and share info, but cannot make another accusation). Game continues for remaining players.

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
| Step 6-7: Each Player Turn | 3-5 minutes |
| Full Round (4 players) | 12-20 minutes |
| Full Game (3 rounds) | 40-65 minutes |
| **Total Session** | **~45-75 minutes** |
