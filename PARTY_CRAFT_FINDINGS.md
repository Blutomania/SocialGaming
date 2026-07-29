# Choose Your Mystery — Party & Social Deduction Craft Findings

## Overview

Third companion document alongside `RESEARCH_FINDINGS.md` (novelist craft) and
`SCREEN_CRAFT_FINDINGS.md` (screen/TV craft). Those two ground narrative construction —
how a mystery's plot is built. This one grounds the thing neither novels nor screen media
actually do: **live, multiplayer, asymmetric-information play** — real murder mystery
parties and social deduction games (*Blood on the Clocktower*, Jackbox), which are the
closest real-world analogue to the 75% clue-sharing mechanic, the interrogation phase, and
a competitive first-to-solve accusation endgame.

## Two parts

- **Part 1 — Design & Mechanics Authority.** Designers/producers explaining what makes the
  live, asymmetric-info format actually work as a *game*, not just a story.
- **Part 2 — Player Experience.** Testimonials, host retrospectives, and psychology-of-
  enjoyment writing about what people say they love in practice. Treated as evidence of
  *reception*, not design authority — kept in a visibly different citation register than
  Part 1 (marketing-adjacent sourcing, not designer reasoning).

## Mapping convention (different from the other two documents)

This material doesn't map onto the P1–P4 literary taxonomy the way novelist/screen craft
does — it's about mechanics and player experience, not plot construction. Entries here map
instead to **game systems already in this project** (see `docs/WIRING.md`):

- **75% Sharing Mechanic** — the core asymmetric-info mechanic
- **Interrogation Phase** — player ↔ AI NPC dialogue
- **Investigation/Scene Phase** — evidence discovery
- **Accusation/Reveal Phase** — competitive, first-to-solve endgame
- **Replayability/Generation** — variety across sessions
- **Host/GM Function** — currently played by the backend (generation + `coherence_validator.py`)
- **Social Dynamics** — player-to-player interaction, not currently modeled by any file
- **Win Condition Design** — competitive-solve vs. cooperative-fun, a real design tension

## Status & sourcing caveat

Same caveat as `SCREEN_CRAFT_FINDINGS.md`: direct `WebFetch` to most article/interview hosts
is blocked by this session's egress policy (403 on CONNECT — confirmed via
`$HTTPS_PROXY/__agentproxy/status`, a policy denial not a site issue). Findings below are
built from `WebSearch`-returned attributed excerpts unless otherwise noted. Verify against
full source text before this feeds any generation prompt.

---

## Part 1 — Design & Mechanics Authority

### Jackbox Games

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Winning is secondary to the shared experience | "When you play a Jackbox game, winning is secondary; the true objective is to get the group to laugh." Their design formula (the "Jack Principles") strips games down to minimize friction and lower the barrier to entry. | **Win Condition Design** — direct tension worth naming: Choose Your Mystery is explicitly competitive (first to solve), whereas Jackbox deliberately deprioritizes winning in favor of collective enjoyment. Not a reason to change the win condition, but worth deciding consciously rather than by default. | [Built In Chicago](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack) |
| Improv's "yes-and" as a design principle | Jackbox regularly hires Second City improv veterans; that training shows up as a house design philosophy — take a player's idea and build on it rather than shutting it down. | **Interrogation Phase** — a concrete prompt-design principle for NPC dialogue: an NPC's response to a player's theory/accusation should build on what the player offered (even to deflect it) rather than issue a flat non-sequitur | [Built In Chicago](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack) |
| Social deduction requires constant rebalancing | "Social deduction games require a lot of balance, and just when you think you've got it figured out, somebody plays in a way you didn't think of and makes you rethink the rules." Identity/hidden-role games are popular with both the team and their audience. | **75% Sharing Mechanic** — a caution: emergent player strategies around a fixed information-sharing rule are likely, and the rule may need retuning after real playtesting rather than being treated as solved by initial design | [Built In Chicago](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack) |

### Murder Mystery Co — "Why Murder Mysteries Are So Fun"

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Ownership through participation | "Every participant has a role to play, even guests without a scripted character still influence the outcome through questions, observations, and deductions" — being part of the story creates ownership, rather than passively consuming a plot. | **Investigation/Scene Phase**, **Social Dynamics** — reinforces that even non-central "witness"-type characters need enough material to meaningfully influence the group's deduction, not just flavor text | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |
| Mysteries spark social connection without forced icebreakers | The format naturally sparks "conversation, laughter, and collaboration" — players "debate theories, share discoveries, and form alliances" organically. | **Social Dynamics**, **75% Sharing Mechanic** — the sharing mechanic's whole point (forcing collaboration) is validated as something players already do voluntarily in the real-world format when the structure invites it | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |
| Clues framed as story, not raw data | "Humans are wired to enjoy problem-solving, especially when the clues come in the form of stories, relationships, and secrets" — the puzzle is more engaging when clues are relational/narrative rather than abstract facts. | **Investigation/Scene Phase** — supports `coherence_validator.py`'s existing bias toward evidence with "thin description" warnings; this is independent validation that narrative-framed clues aren't just nice-to-have polish | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |
| Flexible participation styles, both valid | Some players love staying in character and delivering dramatic accusations; others prefer quietly observing and piecing together the puzzle — both are "equally valid," and no one is pressured to perform. | **Social Dynamics**, **Accusation/Reveal Phase** — a UX principle: the game shouldn't force performative interrogation on players who'd rather work the evidence quietly; both modes need a viable path to winning | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |
| Shared failure is part of the fun | "Groups bond over shared failure too, as getting the wrong answer creates stories people retell for years, with mistakes becoming inside jokes." | **Accusation/Reveal Phase** — a wrong accusation shouldn't just be a fail-state; consider whether the reveal/resolution text can make a wrong guess entertaining in its own right, not just a loss | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |

### Steven Medway — Designer, *Blood on the Clocktower* ("Behind the Curtain" design blog + interviews)

**Sourcing note specific to this section:** Rows below are split into two tiers. Rows marked
**[Medway, primary]** draw on Medway's own "Behind the Curtain" design-blog series
(bloodontheclocktower.com) or his own quoted design statements as surfaced by `WebSearch`
excerpts. Rows marked **[third-party analysis]** are reviewer/journalist commentary
*about* his design choices, not his own words — included because they're accurate,
sourced, and useful, but they should not be treated as verbatim Medway quotes if this
material is ever used in a generation prompt.

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Design moves away from body-language reading, toward information/power interaction **[Medway, primary]** | Medway designed *Blood on the Clocktower* to de-emphasize reading physical tells (the classic Mafia/Werewolf skill), instead building the game around information and character-power interactions — including a private, structured channel (talking to the Storyteller one-on-one) that pure player-to-player games like Werewolf don't have. | **Interrogation Phase**, **Social Dynamics** — direct validation for an AI-mystery format that has no physical tells to read in the first place: information asymmetry and character-power interaction (what an NPC knows, what a player's role/clue lets them do) is exactly the lever this project already pulls, not bluffing "tells." | [Behind the Curtain #4: Werewolf & Clocktower](https://bloodontheclocktower.com/blogs/news/behind-the-curtain-4-werewolf-clocktower-how-they-are-different-how-they-are-the-same) |
| Balance is qualitative, not quantitative **[Medway, primary]** | "Clocktower's abilities cannot be compared mathematically" — unlike games where one character gets "X" and another gets "2X," character power differences are situational and qualitative. Misinformation opportunities given to the "evil team" are treated as necessary and deliberate, to level the playing field against info-advantaged good players. | **Host/GM Function**, **75% Sharing Mechanic** — reframes what "balanced" should mean for a game built on hidden asymmetric info: don't try to make every clue or NPC ability numerically equal in value, make advantage context-dependent and offset it with controlled means for some information to be wrong or misleading. | [Behind the Curtain #7: Balance](https://bloodontheclocktower.com/blogs/news/behind-the-curtain-7-balance) |
| The Storyteller's chaos is the point, not a bug **[Medway, primary]** | Behind the Curtain #1 directly poses the objection "If the Storyteller can lie to players about their info, isn't it all just guesswork? Why is this fun?" Medway's answer: the Storyteller's joy is crafting the right level of challenge; the evil player's joy is crafting the perfect lie; the good player's joy is "to cut through the chaos, to find the necessary truth amidst a sea of possibilities, to separate fact from fiction, and to work together to build a team that agrees with you." | **Accusation/Reveal Phase**, **75% Sharing Mechanic** — direct validation of the 75%-sharing design intent: the payoff isn't players ending up with perfect information, it's the social process of triangulating partial/contradictory info into a trusted team consensus. Confirms that imperfect propagation is a feature, not something to "fix" toward full transparency. | [Behind the Curtain #1: Total Chaos? Sort Of...](https://bloodontheclocktower.com/news/behind-the-curtain-1-total-chaos-sort-of) |
| Outsiders: a role built to be a fun *handicap*, not a helpful ability **[Medway, primary]** | The "Outsider" character class is on the good team but, instead of a useful ability, has a built-in detriment/challenge to overcome. Purpose: let larger games add good-team players without overpowering the good side, while the handicap itself stays "ridiculously fun" to play rather than purely punishing. Townsfolk start neutral and can gain advantage; Outsiders start at a disadvantage and can climb back to neutral by meeting the challenge. | **Replayability/Generation**, **Investigation/Scene Phase** — an argument for generation variety: some generated NPCs/leads could be deliberately handicapping or misleading for the player who draws them (not just informative), as long as overcoming that handicap is itself satisfying, not just a debuff. | [Behind the Curtain #2: Outsiders. Why?](https://bloodontheclocktower.com/blogs/news/behind-the-curtain-2-outsiders-why) |
| Storyteller has live discretion to steer pacing/balance mid-session **[third-party analysis + Medway-adjacent]** | Community Storyteller guidance describes the Storyteller "subtly nudging the game towards an exciting conclusion, not too much that wins feel undeserved, but just enough to keep the game exciting and balanced" — with a concrete example of a Storyteller quietly reassigning a red-herring result mid-setup when the good team looked too strong. This is a live/adaptive extension of the qualitative-balance philosophy Medway describes in Behind the Curtain #7. | **Host/GM Function** — flagged explicitly below: this is a *dynamic, mid-session* tuning capability. The current backend does generation-time coherence checking (`coherence_validator.py`) but has no analogue to a GM quietly rebalancing difficulty once play is already underway. | [Storyteller Advice — Blood on the Clocktower Wiki](https://wiki.bloodontheclocktower.com/Storyteller_Advice) |
| Dead players are never fully cut out of the game **[Medway, primary origin + third-party framing]** | Medway built this specifically in reaction to other social deduction games: he "kept noticing player exclusion after their elimination" and reworked the standard mechanics so every player stays important. The concrete mechanism: dead players keep one "ghost vote" for the rest of the game — they can still talk, still argue, still influence outcomes, and can still affect who wins. A reviewer calls this "the single smartest fix to the biggest problem in the genre" (most Mafia/Werewolf-style games ask eliminated players to sit out and watch). | **New concept flagged below** (Social Dynamics / Win Condition Design touch it but neither owns it) — a structural answer to a problem this project doesn't fully have yet (there's no mid-game elimination), but the *underlying* problem — what happens to players' engagement once the game resolves for someone else — is directly relevant to a competitive first-to-solve Accusation/Reveal Phase. | [How did Steven Medway design Blood on the Clocktower?](https://bloodontheclocktower.com/blogs/news/how-did-steven-medway-design-blood-on-the-clocktower); "single smartest fix" framing: [Blood on the Clocktower Guide — draughtslondon.com](https://draughtslondon.com/mastering-blood-on-the-clocktower/) |
| Voting/execution pacing pressure is what makes the phase satisfying **[third-party analysis, not a Medway quote]** | Analysis of the nomination → second → vote → single execution structure: "the quick turnaround between deliberations, nominations, voting, and then execution forces people to say whatever they can to be the most convincing." Only one execution happens per day-phase, which concentrates stakes onto a single decision rather than diffusing them. | **Accusation/Reveal Phase** — a structural lesson independent of Medway's exact wording: what makes an accusation phase dramatically charged is scarcity (one shot, real time pressure), not just narrative stakes. Worth weighing whether Choose Your Mystery's accusation phase should impose a similar single-shot/time-boxed structure rather than unlimited leisurely deliberation. | [Critical Play – Blood on the Clocktower — Mechanics of Magic](https://mechanicsofmagic.com/2024/04/07/critical-player-blood-on-the-clocktower/) |
| Deep replayability comes from recombinable character abilities, not new plots **[third-party analysis]** | A reviewer describes the game's replay depth as coming from a skilled Storyteller mixing and matching character abilities across scripts to build custom setups — "almost like the marriage of social deduction with a CCG." Official content ships as multiple interchangeable "scripts" (character sets) rather than one fixed rule set, plus a large fan-made script ecosystem. | **Replayability/Generation** — a concrete parallel to `part_registry.py`'s `SOURCE(INDEX)` sampling model: replay variety here comes from recombining a fixed pool of atomic, self-contained components (character powers / mystery parts) in new configurations, not from writing new content each time. | [Blood on the Clocktower Game Review — Meeple Mountain](https://www.meeplemountain.com/reviews/blood-on-the-clocktower-02/) |

### New concepts flagged (Medway / *Blood on the Clocktower*)

1. **Dynamic, mid-session GM rebalancing** — Medway's Storyteller role isn't just a
   generation-time authority (design the setup once, check coherence, done); it's a live actor
   who can subtly retune difficulty *while play is underway* based on how the table is actually
   doing. Nothing in this project's current architecture (`coherence_validator.py` runs
   pre/post generation, not mid-session) has an analogue. Worth deciding explicitly whether
   "Host/GM Function" should be redefined to include live session-time adjustment, or whether
   that's a distinct future capability.
2. **Post-resolution / post-elimination engagement** — the "ghost vote" mechanic solves a
   problem this project doesn't have in the same form (no mid-game player elimination), but the
   underlying design question transfers directly: in a competitive first-to-solve Accusation/
   Reveal Phase, what keeps the players who *didn't* solve it first engaged for the rest of the
   session, rather than reduced to spectators? Recommend either a new category
   ("Post-Resolution Engagement") or folding it explicitly into Win Condition Design's scope.
3. **Regional/cultural variance in play dynamics** — a Room Escape Artist podcast episode
   description states Medway discusses "how the game experience changes depending on which
   country you're playing in," but search excerpts didn't surface his actual reasoning, only the
   episode teaser. Flagged as an open thread, not a sourced insight — would need the actual
   audio/transcript (blocked host) to say anything concrete.

### Murder Mystery Co — Hitchcock-Themed Party Templates

**Sourcing note:** full article text provided directly by the user (`[full text verified]`),
not a `WebSearch` snippet. Still marketing copy for the same company already cited above —
each row extracts a genuinely reusable structural template rather than the surrounding sales
copy, same treatment already applied to the "Why Murder Mysteries Are So Fun" entries.

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Obstructed/partial observation as the core mechanic (*Rear Window* template) | Frames the party version around "nosy neighbors, suspicious couples, and — yes — a potential killer who's always just out of sight," mirroring the original film's voyeuristic, binoculars-only vantage point. | **Investigation/Scene Phase**, **75% Sharing Mechanic** — a specific technique: give some evidence only as a partial or obstructed view (rather than full, clean access) so players must infer past what they can't directly confirm, not just read a clue card | [Murder Mystery Co — Hitchcock Murder Mysteries Party Ideas](https://www.murdermysteryco.com/hitchcock-murder-mysteries-party-ideas/) |
| Identity/persona layer as its own mechanic (*Vertigo* template) | Party version built around guests who "explore hidden motivations and fake personas" — not just secrets, but characters actively performing as someone else. | **Social Dynamics**, **Investigation/Scene Phase** — distinct from a simple hidden secret: a character actively presenting as a different identity is a heavier, more deliberate deception mechanic than an ordinary NPC secret | [Murder Mystery Co](https://www.murdermysteryco.com/hitchcock-murder-mysteries-party-ideas/) |
| Deliberate two-player alliance pairing (*Strangers on a Train* template) | "Pairing guests into unexpected alliances creates the perfect tension, especially when the characters start realizing who they're really dealing with." | **Social Dynamics** — a concrete mechanic distinct from whole-group interrogation: deliberately binding two specific players into a private sub-plot/alliance that only later reveals its cost, rather than every player relating to the group uniformly | [Murder Mystery Co](https://www.murdermysteryco.com/hitchcock-murder-mysteries-party-ideas/) |
| Tightly-wound alibis as the centerpiece (*Dial M for Murder* template) | Party version emphasizes "tightly wound alibis, clever clues, and dramatic confrontations" as the draw, over atmosphere or character voice. | **Accusation/Reveal Phase**, **Investigation/Scene Phase** — a reminder that for some player groups, the alibi-logic puzzle itself (not theme or performance) is the headline attraction and should be built airtight enough to reward careful reasoning | [Murder Mystery Co](https://www.murdermysteryco.com/hitchcock-murder-mysteries-party-ideas/) |
| Even suspicion distribution across the whole cast (*Psycho* template) | The goal stated directly: "giving your guests the feeling that anyone — yes, anyone — could be the killer." | Extends **M1 Suspect Architecture**-adjacent thinking into **Social Dynamics** — reinforces spreading plausible suspicion evenly across the full suspect roster rather than letting 2-3 "obvious" characters absorb most of it, so every player-to-player exchange carries some real doubt | [Murder Mystery Co](https://www.murdermysteryco.com/hitchcock-murder-mysteries-party-ideas/) |

### New concepts flagged (Part 1)

1. **Win Condition Design as a live tension** — Jackbox's "winning is secondary" ethos vs.
   this game's competitive first-to-solve structure isn't a bug to fix, but a design choice
   worth being explicit about — e.g., does the game want *any* mechanism that rewards non-
   winners for a good session (memorable wrong guesses, social credit for good bluffing),
   the way real party mysteries seem to get that "for free"?
2. **Emergent-strategy retuning** — Jackbox's point that hidden-role game balance keeps
   breaking as players find new strategies suggests the 75% sharing rate itself may need
   playtesting-driven retuning post-launch, not just correctness-checking against
   `coherence_validator.py`.

---

## Part 2 — Player Experience

*The material below is not design authority — it's reception evidence. It comes from customer
testimonials, a host's personal retrospective, and journalism about the psychology of social
deduction games, not from designers or producers explaining their reasoning. Treat these rows
as data about what real players and hosts say they enjoyed in practice, worth checking design
choices against, not as prescriptions the way Part 1's entries are. Quotes are attributed to the
page that aggregates them (often anonymous or first-name-only customers, as is standard for this
kind of source) rather than to named individuals unless a byline was actually found.*

### Customer testimonials — My Mystery Party

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Repeat hosting as the loyalty signal | Multiple testimonials describe hosting again, not just enjoying one session: "This was such a big hit, my friends have asked if we could do murder mystery parties more often" and "We've done three mystery parties now from My Mystery Party and they're a hit every time!" | **Replayability/Generation** — real-world evidence that the strongest satisfaction signal isn't a single great session, it's guests actively requesting a repeat; worth treating "would this group want to do this again" as a design target, not just "was this session solved cleanly" | [My Mystery Party — Testimonials](https://www.mymysteryparty.com/testimonials-1/) |
| Banter, not just puzzle-solving, gets named as the fun | "We all had so much fun and enjoyed the banter" — the social byplay between guests is called out specifically, distinct from solving the case itself | **Social Dynamics** — reinforces that the interrogation/investigation phases need to leave room for player-to-player joking and asides, not just efficient clue extraction from NPCs | [My Mystery Party — Testimonials](https://www.mymysteryparty.com/testimonials-1/) |
| First-time hosts report feeling confident, not overwhelmed | Customers describe an easy download/setup process and "sound advice" from support that let first-time hosts run a party confidently despite no prior experience | **Host/GM Function** — the backend (generation + `coherence_validator.py`) is standing in for this kind of hand-holding; a first-time player group with no GM present needs the equivalent confidence, e.g. clear phase prompts, not just a coherent mystery underneath | [My Mystery Party — Testimonials](https://www.mymysteryparty.com/testimonials-1/) |

### Customer testimonials — Murder Mystery Co. / Murder Mystery U.S.A.

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Actors credited for pulling everyone in, not just performing | "The actors were hilarious and they got all the guests involved" (50th birthday party review) | **Interrogation Phase** — the NPC's job as reported by real customers isn't just delivering good lines, it's actively drawing quieter guests into the exchange; an AI NPC that only responds to whoever's already talking is missing half the job | [The Murder Mystery Co. — Reviews](https://www.murdermysteryco.com/reviews/) |
| Twists sustaining suspense through the whole event | A corporate-event review (Red Bull team-building, ~30 people): "The storyline was super intriguing, the characters were so much fun, and the plot twists kept us guessing." | **Investigation/Scene Phase**, **Accusation/Reveal Phase** — validates that mid-mystery reversals, not just the final reveal, are what's remembered as "kept us guessing"; a mystery that reveals its shape too early loses this even if the ending itself lands | [Murder Mystery U.S.A. — Live Testimonials](https://www.murdermystery.com/live-testimonials) |
| "Best party ever" language recurs across companies | Both a DIY-kit customer ("best party ever") and a live-actor company customer ("best Christmas party ever!!!") independently use the same superlative | **Win Condition Design** — a candidate signal: whether *anyone* used "best party ever"-type language may be a better satisfaction proxy for this game than who won the accusation | [The Murder Mystery Co. — Reviews](https://www.murdermysteryco.com/reviews/); [Murder Mystery U.S.A. — Live Testimonials](https://www.murdermystery.com/live-testimonials) |

### Host retrospective — Chrystina Noel, "10 Tips to Host a Murder Mystery Party"

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Small, cramped spaces work better than open ones | Chrystina reports her small house split across four floors "was actually perfect" for the party — the small space with nooks and crannies forces people to hang out together and talk, and the nooks double as spots for private conversations | **Investigation/Scene Phase**, **Social Dynamics** — a physical-space finding without a direct digital equivalent, but worth reading as: investigation "areas" that force small clusters of players together (rather than one big shared space) may produce better interrogation dynamics than a wide-open one | [Chrystina Noel — 10 Tips to Host a Murder Mystery Party](https://chrystinanoel.com/blog/murder-mystery-party) |
| First-time hosts should facilitate, not play a character | She originally planned to play along but found she needed full access to answer guest questions, and now recommends first-time hosts just facilitate rather than take a character role | **Host/GM Function** — supports keeping the backend's role strictly as arbiter/facilitator (generation, coherence checking, NPC responses) rather than ever acting as a biased "player" in the mystery | [Chrystina Noel — 10 Tips to Host a Murder Mystery Party](https://chrystinanoel.com/blog/murder-mystery-party) |
| Décor and atmosphere matter less than expected | She notes some daytime decor (balloons, candles) "seemed unnecessary" for a 2pm party and it was "totally fine without them" | **New concept flagged** — a minor finding that atmosphere-heavy production values may matter less to guest enjoyment than the interaction design itself; doesn't map cleanly to an existing category, listed below | [Chrystina Noel — 10 Tips to Host a Murder Mystery Party](https://chrystinanoel.com/blog/murder-mystery-party) |

### Psychology of enjoyment — social deduction games (Werewolf/Mafia)

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| The story is what's remembered, not the outcome | In One Night Ultimate Werewolf, "each player takes a role in a story that lasts just minutes, but might be talked about for days" — the game session itself becomes an anecdote independent of who won | **Accusation/Reveal Phase**, **Win Condition Design** — reinforces the Part 1 Murder Mystery Co. finding ("shared failure is part of the fun") from a different, non-marketing source: the memorable unit is the session's story, not the win/loss record | [Boing Boing — "What deduction games like Werewolf tell us about ourselves," Matt M. Casey, 2014](https://boingboing.net/2014/11/11/what-social-deduction-games-li.html) |
| Lying carries asymmetric risk depending on your role | Werewolves lie to protect themselves and manufacture "unproductive suspicion"; villagers may lie too, to bait information out of others, but doing so risks damaging their own credibility if caught | **Interrogation Phase** — a concrete asymmetry worth reflecting in NPC/player behavior: a guilty party's deception and an innocent party's deception should carry different social costs when caught, not be treated as symmetrical "lying" | [Boing Boing — "What deduction games like Werewolf tell us about ourselves," Matt M. Casey, 2014](https://boingboing.net/2014/11/11/what-social-deduction-games-li.html) |
| Every game centers on scrutinizing each other, not the environment | The article distinguishes social deduction games from other genres precisely because play "focuses almost entirely on how players scrutinize each other," tracing the lineage back to Dmitry Davidoff's 1986 game Mafia (villagers vs. a smaller informed minority) | **Social Dynamics** — a structural reminder that in this genre, player-to-player suspicion *is* the core gameplay loop, not a side effect of it; the 75% sharing mechanic's value is largely in fueling that scrutiny between players, not just moving information | [Boing Boing — "What deduction games like Werewolf tell us about ourselves," Matt M. Casey, 2014](https://boingboing.net/2014/11/11/what-social-deduction-games-li.html) |
| Knowledge asymmetry itself is the addictive core | "Knowing something that no one else knows and using it to your advantage is right at the core of what makes Mafia and Werewolf such delicious and addictive games to play... the intoxicating appeal of power, and specifically knowledge as power." | **75% Sharing Mechanic** — direct validation of the core design bet: deliberately keeping some players informationally ahead of others (rather than pooling everything instantly) is not a compromise, it's identified as the primary source of engagement in this genre | [No Rolls Barred — "What Are Social Deduction Games?"](https://norollsbarred.com/articles/what-are-social-deduction-games/) |
| An informed minority outmaneuvering an uninformed majority is the genre's founding idea | Werewolf/Mafia was designed by psychology student Dmitry Davidoff specifically to demonstrate that a small informed group can out-maneuver a large uninformed one | **75% Sharing Mechanic**, **Accusation/Reveal Phase** — frames the "race to accuse" not as a speed contest but as a contest of who assembled the more complete information picture fastest; worth keeping the accusation phase rewarding synthesis over raw speed | [No Rolls Barred — "What Are Social Deduction Games?"](https://norollsbarred.com/articles/what-are-social-deduction-games/) |

### First-person player accounts

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| The draw is ownership of the story, not consumption of it | Player-facing writeups converge on the same idea in first-person framing: murder mystery games are enjoyed because "every participant has a role to play... instead of consuming a plot, participants help shape it" | **Investigation/Scene Phase**, **Social Dynamics** — corroborates the Part 1 Murder Mystery Co. finding independently from a player-experience angle rather than a company's own marketing page | [10 reasons why I enjoy interactive murder mystery games so much](https://www.great-murder-mystery-games.com/10-interactive-murder-mystery-games.html) |
| Quiet players get pulled in without being forced to perform | The structure itself "makes it easier for quieter guests to engage, since the structure gives everyone a reason to speak" | **Social Dynamics**, **Interrogation Phase** — same point Part 1 makes about flexible participation styles, but from the angle of *why* it happens: it's the built-in "reason to speak" (a role, a clue, an objective) doing the work, not player confidence alone. Suggests interrogation UI should always give a shy player a concrete question/objective prompt rather than an open mic | [10 reasons why I enjoy interactive murder mystery games so much](https://www.great-murder-mystery-games.com/10-interactive-murder-mystery-games.html) |
| Multiple personal goals beyond "solve the murder" sustain engagement | Beyond identifying the killer, players report enjoying secondary objectives layered into their character (e.g., paying off a debt, hiding an affair, retrieving an object) — the murder is the headline goal but not the only one | **Win Condition Design**, **Replayability/Generation** — a candidate structural idea: secondary per-player objectives (independent of who "wins" the accusation) give players something to succeed at even when they don't solve the case first, softening the all-or-nothing competitive win condition flagged as a tension in Part 1 | [10 reasons why I enjoy interactive murder mystery games so much](https://www.great-murder-mystery-games.com/10-interactive-murder-mystery-games.html) |
| A murder mystery is deliberately not solved the same way twice | A replayability-focused designer note (adjacent genre, not a player testimonial, but directly on point): free-form structure means "two people could play the same character and have wildly different results" across playthroughs | **Replayability/Generation** — direct support for treating replay variance (not just content variety across generations) as a design goal: even the *same* generated mystery, replayed with a different group, should be able to unfold differently based on how players choose to interrogate and share | [Foulplay Games — "Can you Replay a Murder Mystery Game?"](https://www.foulplayco.com/blog/replaying-a-murder-mystery-game) |

### New concepts flagged (Part 2)

1. **Atmosphere/production value may be over-weighted relative to interaction design** —
   Chrystina Noel's finding that skipped decor "was totally fine" suggests spending polish
   budget on interrogation/investigation interaction quality may matter more to player
   enjoyment than visual set dressing. Doesn't map cleanly to any existing game-system
   category; closest is Investigation/Scene Phase but it's really a resourcing-priority
   observation, not a mechanic.
2. **Secondary per-character objectives as a softer win condition** — several sources
   (player-experience listicle, Murder Mystery Co.'s "flexible participation styles")
   independently point at giving each player a personal sub-goal beyond "identify the
   culprit first." This directly extends the Part 1 flagged tension (Win Condition Design)
   with a concrete mechanism: a player who doesn't win the accusation race could still have
   "won" their personal objective, which may be an easier lever to pull than changing the
   core accusation race itself.
3. **Repeat-hosting / "would play again" as a satisfaction metric** — the testimonial pattern
   of guests requesting another session is a distinct, easily-instrumented signal (could be
   captured as a post-game prompt) that's different from both the viability rating already
   in the design (`CLAUDE.md` → Design Principles → Creator signal) and from time-to-solve or
   accusation accuracy (Player signal). Worth considering as a third feedback-loop signal.

---

## Sources

- Jackbox Games — [Built In Chicago](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack)
- Murder Mystery Co — [Why Murder Mysteries Are So Fun](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/), [Reviews](https://www.murdermysteryco.com/reviews/), [Hitchcock Murder Mysteries Party Ideas](https://www.murdermysteryco.com/hitchcock-murder-mysteries-party-ideas/) (full text provided by user)
- Steven Medway / Blood on the Clocktower — [Behind the Curtain #1](https://bloodontheclocktower.com/news/behind-the-curtain-1-total-chaos-sort-of), [#2](https://bloodontheclocktower.com/blogs/news/behind-the-curtain-2-outsiders-why), [#4](https://bloodontheclocktower.com/blogs/news/behind-the-curtain-4-werewolf-clocktower-how-they-are-different-how-they-are-the-same), [#7](https://bloodontheclocktower.com/blogs/news/behind-the-curtain-7-balance), [How did Steven Medway design Blood on the Clocktower?](https://bloodontheclocktower.com/blogs/news/how-did-steven-medway-design-blood-on-the-clocktower); [Storyteller Advice Wiki](https://wiki.bloodontheclocktower.com/Storyteller_Advice); [Draughts London guide](https://draughtslondon.com/mastering-blood-on-the-clocktower/); [Mechanics of Magic](https://mechanicsofmagic.com/2024/04/07/critical-player-blood-on-the-clocktower/); [Meeple Mountain review](https://www.meeplemountain.com/reviews/blood-on-the-clocktower-02/); [Room Escape Artist](https://roomescapeartist.com/2025/05/20/s9e6-steven-medway-blood-clocktower/) (topic pointer only)
- My Mystery Party — [Testimonials](https://www.mymysteryparty.com/testimonials-1/)
- Murder Mystery U.S.A. — [Live Testimonials](https://www.murdermystery.com/live-testimonials)
- Chrystina Noel — [10 Tips to Host a Murder Mystery Party](https://chrystinanoel.com/blog/murder-mystery-party)
- Boing Boing — [What deduction games like Werewolf tell us about ourselves](https://boingboing.net/2014/11/11/what-social-deduction-games-li.html)
- No Rolls Barred — [What Are Social Deduction Games?](https://norollsbarred.com/articles/what-are-social-deduction-games/)
- [10 reasons why I enjoy interactive murder mystery games so much](https://www.great-murder-mystery-games.com/10-interactive-murder-mystery-games.html)
- Foulplay Games — [Can you Replay a Murder Mystery Game?](https://www.foulplayco.com/blog/replaying-a-murder-mystery-game)
