# Choose Your Mystery — Screen & TV Craft Findings

## Overview

Companion to `RESEARCH_FINDINGS.md`. That document grounds the extraction taxonomy
(`extraction_protocols.py` P1–P4) in the words of prose mystery novelists. This document
extends the same grounding to **filmmakers, screenwriters, and showrunners** of successful
mystery films and television — feeding the RAG generation-grounding layer scoped in
`SESSIONS.md` Session 18 / `CLAUDE.md` Current To-Do item 10.

Purpose: give the mystery generator craft authority beyond structural completeness
(what `coherence_validator.py` already checks for free) — e.g. *how* a fair-play clue
should actually be planted, not just that a clue exists.

## Status & sourcing caveat

**Capture in progress.** Direct `WebFetch` of the source articles is blocked by this
session's egress policy (403 on CONNECT to hosts like theringer.com, scriptmag.com,
nofilmschool.com, aframe.oscars.org, cbr.com, freshfiction.tv — confirmed via
`$HTTPS_PROXY/__agentproxy/status`, not a site-side block). `WebSearch` is unaffected and
returns attributed excerpts/quotes from these same articles, so all entries below are
built from search-engine-returned snippets of the cited pages, not full-text fetches.

**Before this feeds any generation prompt**, verify quotes against full source text
(e.g. via a browser, archive.org, or a session without this egress restriction) — treat
everything below as accurately-attributed-per-search-snippet, not manually verified
verbatim.

---

## Rian Johnson — *Knives Out*, *Glass Onion*, *Poker Face*

| Concept | Insight | Maps to taxonomy | Source |
|---|---|---|---|
| Whodunit's structural weakness | Started from Hitchcock's critique that whodunits rely on one surprise at the end — a narrative weakness. His answer: a film that "begins as a traditional whodunnit and orients the audience very clearly, and then turns into a Hitchcock thriller where there's a character you care about." | Extends **C5 Resolution** / **M6 Reveal Mechanic** — the reveal isn't just a solved puzzle, it's earned emotional payoff | [ScriptMag](https://scriptmag.com/interviews-features/rian-johnson-talks-screenwriting-and-what-classic-movies-can-teach-us) |
| Visual fair play | "Feels like fair game to use the strength of cinema to do things visually that you cannot in books." Plays fair by hiding clues in **sound** — a technique with no prose equivalent. | Extends **M3 Clue Fairness** with a screen-specific corollary: fairness can be medium-native (visual/aural), not just textual | [No Film School](https://nofilmschool.com/rian-johnson-knives-out-screenplay) |
| Clues hidden in plain sight | Buries slighter clues inside jokes; prefers a visual clue the camera "zooms in on" that "was there the whole time because you could have seen it" — audience should be able to notice clues on first viewing even without knowing their relevance yet. | **M3 Clue Fairness**, **M2 Red Herring** (misdirection via comedic beat, not just plot) | [No Film School](https://nofilmschool.com/rian-johnson-knives-out-screenplay) |
| Reveal must feel earned, not just correct | Big dénouement is "only satisfying if it feels like audiences are connecting dots that they recognize" — not merely told the answer. | **C5 Resolution**, **M6 Reveal Mechanic** | [No Film School](https://nofilmschool.com/rian-johnson-knives-out-screenplay) |
| Mystery is underneath, not on top | Prioritizes the mystery being "visually engaged with great actor material and dialogue, with the mystery placed underneath all that stuff" — structure should feel invisible to a first-time viewer. | New concept, not in current taxonomy — candidate for a screen-specific "load-bearing but invisible structure" note | [PBS On Story](https://www.pbs.org/video/reinventing-the-classic-whodunnit-a-conversation-with-rian-johnson-7vtzs4/) |
| Character-first ensemble | Considers piecing together a fully-realized ensemble "one of the most rewarding aspects of the genre" — wants every actor to get material worthy of their talent, not just a suspect slot. | **M1 Suspect Architecture** — extends it: suspects need actorly material, not just means/motive/opportunity coverage | [PBS On Story](https://www.pbs.org/video/reinventing-the-classic-whodunnit-a-conversation-with-rian-johnson-7vtzs4/) |
| Theme drives structure | Starts from theme and uses the mystery's structure itself to engage deeper thematic material, rather than bolting theme onto a finished plot skeleton. | New concept — no direct P1–P4 analogue; candidate addition | [PBS On Story](https://www.pbs.org/video/reinventing-the-classic-whodunnit-a-conversation-with-rian-johnson-7vtzs4/) |
| Howcatchem vs. whodunit | On *Poker Face*: "as opposed to a whodunnit like *Knives Out* or *Glass Onion*, where you have an ensemble of eight or nine suspects and you have to juggle all of them," the benefit of the howcatchem format — audience sees who did it and how the detective catches them — "is that there's only one suspect." Term "howcatchem" (inverted detective story) coined by Philip MacDonald. | **New structural mode**, not covered by P1–P4 at all — the whole taxonomy currently assumes whodunit (culprit hidden from player until resolution). A howcatchem mode would need its own protocol variant if the game ever supports it. | [The Ringer](https://www.theringer.com/2023/01/25/tv/rian-johnson-interview-poker-face-peacock-natasha-lyonne) |
| Villain as full character | Cites *Columbo* as inspiration: the inverted format "allowed them to give screen time to the villain and to have them be built into a substantial character and play out the dynamic between them and Columbo." | **C4 Culprit + Motive** — extends it: even in a standard whodunit, the culprit benefits from being written with this much interiority, not just a motive line | [The Ringer](https://www.theringer.com/2023/01/25/tv/rian-johnson-interview-poker-face-peacock-natasha-lyonne) |

### New concepts flagged for taxonomy consideration

None of these exist in `extraction_protocols.py` P1–P4 yet — surfacing them here rather
than silently editing the taxonomy:

1. **Medium-native clue fairness** — fairness delivered through visual/aural information
   the player can *notice* (not just be told), distinct from prose's M3 definition.
2. **Invisible structure** — the mystery skeleton should not be visible as a skeleton to
   the player on first pass; craft is in the concealment as much as the construction.
3. **Howcatchem as a second structural mode** — currently out of scope (the game is
   whodunit-only), but worth a one-line note in `docs/WIRING.md` if genre variants are
   ever discussed.

---

## Steven Moffat — *Sherlock*

| Concept | Insight | Maps to taxonomy | Source |
|---|---|---|---|
| Clue-planting as magic trick | On whether there are real clues to how Sherlock survives the Reichenbach fall: "Planting clues isn't very hard because you know what you're doing. Just like a magic trick isn't difficult if you know how to do it." Frames fair-play clueing as a performer's-secret asymmetry — trivial for the writer who already knows the solution, genuinely hard (and fun) for the audience who doesn't. | **M3 Clue Fairness** — a screen-specific framing: fairness is a magician's discipline (plant openly, let confidence/misdirection do the concealing), not a puzzle-design one | [Benjamin Grafton interview, June 17 2012](https://benjamingrafton.com/interviews/2012/06/17/interview-with-stephen-moffat) |
| "There's one clue everyone's missed" | On the Reichenbach Fall's central mystery: "There's one clue that everybody's missed. It's something that Sherlock does that was very out of character, but which nobody has picked up on." Fan theories (fake pulse ball, blood packet, mystery cyclist) proliferated without landing on it — Moffat maintained a genuine solvable clue existed even though the show never confirmed it on-screen. | **M3 Clue Fairness** — the clue is planted in *character behavior* (an out-of-character beat), not physical evidence; a subtler clue-type than object/testimony | [BBC News, Jan 2012](https://feeds.bbci.co.uk/news/entertainment-arts-16266601) |
| Magic trick as reveal-mechanic shield | Sherlock tells Watson pre-jump "It's just a magic trick," and Moffat/Gatiss used that line as their own real-world defense for never giving a definitive on-screen explanation of the fall — invoking the magician's rule that "the one thing a magician should never do" is explain the trick, since a revealed trick loses its power. | **M6 Reveal Mechanic** — extends it: a reveal mechanic can deliberately stay partially unresolved/ambiguous as a craft choice, trading total closure for lingering mystique | [Den of Geek analysis](https://www.denofgeek.com/tv/sherlocks-fall-the-empty-hearse-and-magic-tricks/) |
| Misdirection through audience sympathy | On Mary Watson's series-3 spy-past twist, hidden "in plain sight in the first two episodes": "she can recognise a skip code, she likes Sherlock Holmes, it's all there, right in front of you." The misdirection worked not by hiding the clues but by making the audience *emotionally relieved* Mary was supportive of Sherlock and John's friendship — so relief overrode suspicion, and viewers (like Sherlock himself) missed it because they liked her. | **M2 Red Herring** — a distinct mechanism from a false suspect: concealment via the audience's own affection for a character, not via a decoy. Also extends **M3 Clue Fairness**: the clues (skip-code recognition, dialogue like "he'd need a confidant") are literal and visible, just emotionally camouflaged | [Empire, "20 Sherlock Series 3 Secrets"](https://www.empireonline.com/movies/features/sherlock-series-3-secrets/) |
| Controlled release of information as the core craft problem | On storytelling generally (applied throughout his mystery writing): "The controlled release of information — which is more or less what storytelling is — is really, really hard." Treats pacing-out-the-reveal, not plot mechanics per se, as the central skill of mystery construction. | **M6 Reveal Mechanic** — a structural principle underlying it: the reveal mechanic is really a sequencing-of-disclosure problem across the whole runtime, not just a final scene | [Purdie Writing, "Steven Moffat on Writing," Nov 2013](http://purdiewriting.blogspot.com/2013/11/steven-moffat-on-writing.html) |
| Secrecy discipline extends to cast, not just audience | On keeping the Reichenbach Fall solution hidden even from the show's own actors during production: "We've practically reduced our cast to tears telling them the plan." Suggests a production-side technique for protecting a reveal — compartmentalizing knowledge of the solution even among people performing the scenes — distinct from anything happening on the page. | **New concept**, not in current taxonomy — a *production/process* discipline (need-to-know script distribution) rather than a textual craft element; flagged below | [PBS Masterpiece, Moffat & Cumberbatch on The Reichenbach Fall](https://www.pbs.org/video/masterpiece-sherlock-moffat-and-cumberbatch-on-the-reichenbach-fall/) |
| Non-linear structure as a storytelling default, not a gimmick | Pushing back on being characterized as a non-linear-structure specialist: "People are always going on at me about out of sequence narrative, but what is the right order to tell a story?" — treats chronological order as just one arbitrary option among several, with reveal-protection often favoring a different one. Elsewhere: "I like non-linear storytelling and time-travel and the occasional twist, I suppose." | **New concept** — closest existing analogue is **M6 Reveal Mechanic**, but this is about *narrative sequencing of scenes/episodes* (what order the audience receives story-time events), not the mechanism of the reveal itself; flagged below as a candidate addition | [Glasgow Guardian, "Dr Who is Sherlock Holmes in Space"](https://glasgowguardian.co.uk/2023/09/08/dr-who-is-sherlock-holmes-in-space-in-conversation-with-steven-moffat/) |

### New concepts flagged for taxonomy consideration

1. **Need-to-know production secrecy** — protecting a mystery's solution isn't purely a
   writing-craft matter; Moffat describes deliberately withholding the solution from cast
   members during shooting. No P1–P4 code covers *process* discipline around who on the
   creative team knows the ending and when — this is a production-practice concept, not a
   textual one, so it may sit outside the taxonomy's scope entirely rather than needing a
   new code.
2. **Narrative sequencing as reveal-protection** — writing/revealing story events out of
   chronological order (non-linear structure) as a deliberate technique to protect a twist,
   distinct from **M6 Reveal Mechanic** (which covers *how* a reveal is delivered, not *what
   order* preceding scenes are shown in). Worth a note in `docs/WIRING.md` if the interrogation/
   investigation phase ever wants to withhold or reorder information delivery to players for a
   forthcoming reveal, analogous to a game master pacing disclosure.
3. **Reveal ambiguity as a deliberate craft choice** — Moffat/Gatiss's "magic trick" defense for
   never fully explaining the Reichenbach fall on-screen suggests some reveals can gain power by
   staying partially unresolved. This cuts against the game's requirement that **C5 Resolution**
   land conclusively for players to "win" — noted here as a tension rather than proposing a
   change, since Choose Your Mystery's competitive accusation format likely can't tolerate an
   ambiguous canonical solution the way a TV episode can.

## John Hoffman — *Only Murders in the Building*

| Concept | Insight | Maps to taxonomy | Source |
|---|---|---|---|
| Reverse-plotting from the solution | "We knew the end moments of episode ten and then we worked our way backwards," explaining that "mystery writing is very tricky." Elsewhere, more explicitly: "you have to jump to the end first, and then twist your way backwards so you're hiding what you're going to reveal, but you're layering in and you have to really thread-by-thread [track] clues and red herrings and other paths that might connect a bit but don't lead to the ultimate central mystery." | **C5 Resolution** driving construction order — the culprit/motive (**C4**) and resolution are fixed first, then **M2 Red Herring** and **M5 Alibi** threads are built backward from that fixed point, not forward from a premise | [Gold Derby](https://www.goldderby.com/feature/john-hoffman-only-murders-in-the-building-showrunner-video-interview-2-1205830514/) |
| Red herrings as threaded, dead-ending paths | Describes the writers' room having "to work backwards and know where we're aiming and who killed and how and, and then track backwards and twist it so that we were hiding that but not realizing the truth of what happened" — red herrings are explicitly "other paths that might connect a bit but don't lead to the ultimate central mystery," i.e., partially plausible, not arbitrary noise. | **M2 Red Herring** — sharpens the existing code: a strong red herring should genuinely connect to real evidence/threads rather than being a dead, disconnected lie | [WGA East, OnWriting Ep. 65](https://www.wgaeast.org/onwriting/episode-65-john-hoffman-only-murders-in-the-building/); corroborating quote also surfaced via [Gold Derby](https://www.goldderby.com/feature/john-hoffman-only-murders-in-the-building-showrunner-video-interview-2-1205830514/) |
| Mystery as a collaboration with audience guesswork | "When you're doing a mystery, you want to feel what they're thinking a little bit and maybe undercut that, swerve away from it or lean right into it." Treats audience theorizing as an input to be actively managed each episode, not just eventually resolved. | **M2 Red Herring** / **M6 Reveal Mechanic** — extends both: misdirection is reactive to anticipated audience theories, not fixed at outline stage alone | [Moviefone](https://www.moviefone.com/news/only-murders-in-the-building-interview-john-hoffman/) |
| Serialized mystery is a different craft problem than a film mystery | "A 10-episode mystery is a very different thing from a two-hour movie of a mystery" — requires keeping twists alive, deepening character investment, and holding "all 10 episodes in your head when you're actually shooting episode one through 10, so that you're mindful of what's coming." | New concept — no direct P1–P4 analogue for *serialized, multi-episode* clue pacing (see flagged concepts below) | [Gold Derby](https://www.goldderby.com/feature/john-hoffman-only-murders-in-the-building-showrunner-video-interview-2-1205830514/) |
| Mystery construction is deliberately effortful, not improvised | The season's "mystery side and the twists and everything else that comes along is a painstaking process" — keeping the signature twists consistent across a season is treated as its own disciplined workstream, separate from character/comedy writing. | **M3 Clue Fairness** — process-level corollary: fairness/consistency checking is an explicit, separate pass, not something that falls out of writing scenes | [Gold Derby](https://www.goldderby.com/feature/john-hoffman-only-murders-in-the-building-showrunner-video-interview-2-1205830514/) |
| Balancing comedy and mystery is a distinct, compounding difficulty | "A mystery has particular things that are difficult. A mystery comedy is another thing that makes it a little bit challenging. And then trying to find the balance is the real challenge." Names comedy-plus-mystery as harder than either alone, not just an additive genre mashup. | New concept — closest existing code is **F8 Moral Ambiguity** (tonal complexity) but doesn't cover comedy/mystery tonal balancing specifically; flagged below | [Awards Radar](https://awardsradar.com/2022/06/22/john-hoffman-omitb/) |
| Comedy earns its place through grounded tragedy, not despite it | On tone: without "belying the truths about what awful tragedy can do," but using that truth to power comedy — "the best laughs you have are when you're at a funeral, or places you're not supposed to." Comedy is licensed by, not opposed to, taking the crime's human cost seriously. | **F8 Moral Ambiguity** extends toward comedic tone specifically — humor sourced from grief/tragedy rather than undercutting the victim's stakes | [ScriptMag](https://scriptmag.com/interviews-features/creating-the-murder-mystery-comedy-with-only-murders-in-the-building-co-creator-and-showrunner-john-hoffman) |
| Culprit identity kept genuinely open late into breaking a season | The writers "always talk about alternatives at the very beginning" of breaking a season, and "pick up a couple of different versions and wonder what's the best way to go, what's the one that seems interesting, what feels right for the story we want to tell" — i.e., multiple candidate culprits are actively developed in parallel before one is locked in. | **C4 Culprit + Motive** — process corollary: culprit selection is treated as a comparative choice among several worked-out options, not a single fixed premise decided up front | [TheWrap](https://www.thewrap.com/only-murders-in-the-building-season-5-episode-10-john-hoffman-interview/) |

### New concepts flagged for taxonomy consideration

None of these exist in `extraction_protocols.py` P1–P4 yet:

1. **Serialized/multi-episode clue pacing** — Hoffman's repeated point that a 10-episode
   mystery is "a very different thing from a two-hour movie of a mystery" is a structural
   concern the current taxonomy (built from prose novelists and, so far, film-length screen
   sources) doesn't address: how clue density, red-herring lifespan, and twist cadence should
   be paced *across episodes/season*, not just across a single narrative arc. Relevant if the
   game's investigation phase is ever split into multiple timed rounds/episodes rather than one
   continuous session.
2. **Comedy/mystery tonal balancing as its own craft problem** — Hoffman names "mystery
   comedy" as harder than mystery or comedy alone, distinct from general tonal register
   (**F13 Atmospheric Register**) or moral ambiguity (**F8**). Given the game's own social,
   often-comedic player interactions, this may be worth a dedicated code if future sources
   (e.g. a *Knives Out*-adjacent or sitcom-mystery creator) corroborate it as a recurring,
   nameable craft concern rather than an idiosyncrasy of one show.
3. **Explicit multi-candidate-culprit breaking process** — treating culprit choice as a
   comparative shortlist worked out in parallel (not just "who fits the motive best" after
   the fact) is a writers'-room process note rather than a structural taxonomy code; flagged
   here rather than folded into **C4** since it describes *how* the culprit is chosen, not
   what the choice must contain.

## Chris Chibnall — *Broadchurch*, *Gracepoint*, *Death at the White Hart*

| Concept | Insight | Maps to taxonomy | Source |
|---|---|---|---|
| Long-form pacing over episodic case-of-the-week | "It was almost unheard of to set a series over eight episodes. Six was the norm, but Broadchurch was unusual because it was long form writing, which meant we could spend much more time with each character." Called stretching a single murder investigation over eight weekly episodes "a terrifying high-wire act" at a time when story-of-the-week procedurals were the industry default. | Extends **M1 Suspect Architecture** / **M4 Social World** — long-form structure is what buys room to develop the *whole* social world, not just the detective plot, as a screen-specific corollary to prose pacing | [Royal Television Society](https://rts.org.uk/article/chris-chibnall-man-who-reinvented-cliffhanger); [Den of Geek](https://www.denofgeek.com/tv/chris-chibnall-interview-broadchurch-doctor-who-more/) |
| Writing stayed adaptive to cast performance | Only the first few scripts were written before shooting began; Chibnall waited until casting was locked and he'd seen actors perform the roles before writing later episodes, letting performance feed the writing. | New process note, adjacent to **F2 Suspect's Wound** / **C6 Investigator** — suggests craft benefit of writing character interiority *after* seeing it embodied, which has no direct prose analogue | [Den of Geek](https://www.denofgeek.com/tv/chris-chibnall-interview-broadchurch-doctor-who-more/) |
| Emotion overrides plot mechanics when they conflict | "The emotion has to trump the fans' little nerdy obsessions" — when plot logic and emotional truth pulled in different directions, he prioritized the latter. | Extends **C4 Culprit + Motive** / **F8 Moral Ambiguity** — motive and reveal should serve emotional truth over pure mechanical cleverness | [Den of Geek](https://www.denofgeek.com/tv/chris-chibnall-interview-broadchurch-doctor-who-more/) |
| Culprit locked early, cast to match | Chibnall says he knew Joe Miller (Ellie Miller's husband) was the killer from day one of writing, and cast actor Matthew Gravelle "carefully with that in mind" — the actor's suitability to eventually play a killer's reveal shaped casting. | **C4 Culprit + Motive** / **M1 Suspect Architecture** — the culprit's suspect-pool "cover" is partly a casting decision, not just a writing one | [david-tennant.co.uk fan-site interview digest](http://www.david-tennant.co.uk/2013/03/broadchurch-actors-had-no-clue-to.html) (via search snippet; original interview outlet not independently confirmed) |
| Culprit choice changed during drafting | Separately, Chibnall has said that early on he "knew vaguely the identity of who I thought the killer was, although that changed" — a few days into a rough first draft he had a realization: "it's not that person; it's going to be this ending." | **C4 Culprit + Motive** — shows the culprit identity was a live variable during outlining/drafting, not fixed from the first beat sheet; distinct from the production-security practice below (this is an authorial drafting decision, not an anti-leak tactic) | [Fast Company](https://www.fastcompany.com/1683515/the-art-of-the-cliffhanger-broadchurch-creator-breaks-down-britains-most-tweeted-thriller) (per search snippet) |
| Suspect pool built through ambiguous direction of the ensemble, not just plot mechanics | Chibnall wanted every performer to "slightly suspect their character" and think about and suspect each other — direction aimed at making the *cast itself* uncertain who was guilty, so no actor could unconsciously signal innocence or guilt through performance. | Extends **M1 Suspect Architecture** / **M2 Red Herring** with a screen-specific technique: misdirection can be built at the *performance* level (directing actors to play ambiguity), not only at the script/plot level — flagged below as partly new | [search-attributed interview summary, exact outlet not confirmed in snippet — likely Den of Geek or Cultbox] |
| Same premise, deliberately different solution across productions | Chibnall wrote both *Broadchurch* (UK) and its US remake *Gracepoint* from the same premise but gave them different killers: Joe Miller in *Broadchurch* vs. Tom Miller (the Millers' son, in a lesser, accidental-death framing) in *Gracepoint*. Producers "wouldn't definitively confirm" the culprit differed and said they "didn't want viewers to rule anybody out." | **C4 Culprit + Motive** — concrete evidence Chibnall treats "who did it" as swappable even atop an otherwise-identical suspect/setting architecture; useful precedent if the game ever wants same-scenario/different-culprit replay variants | [Variety](https://variety.com/2014/tv/news/gracepoint-broadchurch-foxs-adaptation-differs-british-original-1201265784/) (per search snippet) |
| Production-level secrecy: watermarked scripts, NDAs, tiny inner circle | For series 2, all scripts were individually watermarked/named so any leak could be traced back to its source, and cast signed NDAs. Chibnall says only five people (including himself) knew the full story at any time; scripts were kept in a safe on set. Most cast learned the killer's identity only right before or at the point of filming the reveal — e.g., Matthew Gravelle (Joe Miller) was told by phone the night before receiving the episode 8 script; Jodie Whittaker (Beth Latimer) was told early only because she asked, needing to know if her grief was "real" tears; Olivia Colman was told just before the reveal was filmed. | **Not covered by the current taxonomy at all.** This is a production-process/security practice (script control, NDAs, staggered cast disclosure), not a story-structure element — flagged explicitly as a candidate new concept rather than force-mapped | [IMDb postmortem](https://m.imdb.com/news/ni56224817/?ref_=nm_nwr_2); [david-tennant.co.uk digest](http://www.david-tennant.co.uk/2013/03/broadchurch-actors-had-no-clue-to.html) (both per search snippet) |
| Ended the show to avoid becoming an episodic procedural | Chibnall says he chose to end *Broadchurch* after three series because he "didn't want it to become like *Midsomer Murders*" — i.e., didn't want a single-location mystery format to calcify into an endless case-of-the-week formula once the original closed-world premise was exhausted. | New concept, adjacent to **C3 Closed World** — a closed-world setting has a natural narrative shelf life; reusing it case-after-case erodes the "closed world" premise's credibility | [AOL/Chris Chibnall interview](https://www.aol.com/chris-chibnall-says-ended-broadchurch-170218365.html) (per search snippet) |
| Suspect-building process on the page (novel) | On his prose debut *Death at the White Hart* (village pub landlord killed, large ensemble suspect pool of pub patrons that night), Chibnall described having "a sense of who his money was on" going in but staying open: "you have a plan for where you're going, your ears are open and you're always thinking about what the characters are telling you." | **M1 Suspect Architecture** / **M3 Clue Fairness** — outline-with-flexibility approach: a provisional culprit guides suspect construction, but the writer stays responsive to what a scene reveals about a character rather than forcing the outline | [NPR](https://www.npr.org/2025/06/13/nx-s1-5276298/death-at-the-white-hart-when-the-publican-is-found-dead-everyones-a-suspect) |
| Closed-world suspect pool from a real, lived-in community | Chibnall has lived in Dorset for 20 years, about a mile from the beach where *Broadchurch* was filmed — the placement in and long-term observation of a real small community is, per his own account, of "profound and fundamental interest" to him and feeds directly into how the shows' closed-world casts of suspects are populated. | **C3 Closed World** / **M4 Social World** | [Great British Life](https://www.greatbritishlife.co.uk/magazines/dorset/26269470.broadchurch-writer-chris-chibnall-launching-book-bridport/) (per search snippet) |

### New concepts flagged for taxonomy consideration

None of these exist in `extraction_protocols.py` P1–P4 yet:

1. **Production-security-as-craft-practice** — watermarked/traceable scripts, cast NDAs,
   and a deliberately tiny circle of people who know the solution, with staggered
   disclosure to cast timed to filming order. This is explicitly a *production-process*
   discipline, not a story-structure element, and doesn't belong anywhere in P1–P4 as
   currently scoped. Worth a short standalone note in `docs/WIRING.md` only if the project
   ever needs a "how do we keep AI-generated mystery solutions from leaking to players
   mid-session" analogue (e.g. server-side solution storage, no early client exposure) —
   otherwise out of scope for the generation taxonomy itself.
2. **Performance-level misdirection** — directing an ensemble cast to play mutual,
   ambiguous suspicion of one another (so no actor's performance telegraphs guilt or
   innocence) is a screen-native extension of **M2 Red Herring** with no prose or
   AI-NPC-dialogue equivalent yet defined. Could matter for `interrogate` endpoint design:
   NPC dialogue generation may need an equivalent "don't let tone leak guilt" constraint
   for every suspect, not just the true culprit.
3. **Culprit-as-late-variable during outlining** — Chibnall's own account of changing his
   mind about the killer partway into a first draft, plus the confirmed Broadchurch/
   Gracepoint case of one premise supporting two different solutions, both suggest
   treating "who did it" as swappable later in the design process than C4 currently
   implies. Not necessarily a new taxonomy code, but worth flagging to whoever scopes the
   RAG layer: don't assume C4 must be resolved before M1–M5 architecture work begins.
4. **Closed-world shelf life** — Chibnall's stated reason for ending the show (avoiding
   "Midsomer Murders"-style episodic reuse of one closed world) implies C3 Closed World
   has an inherent expiration point once reused past a certain number of cases. No current
   taxonomy code addresses reuse fatigue of a single closed-world setting.

**Caveat:** two rows above (ensemble misdirection-direction quote; casting-with-the-killer-
in-mind quote) came from WebSearch summaries where the search tool did not clearly name the
originating outlet — the linked URL is the best-available attribution from the raw search
results, not a manually confirmed byline. Verify against full source text before use.

## Nic Pizzolatto — *True Detective*

| Concept | Insight | Maps to taxonomy | Source |
|---|---|---|---|
| Anthology chosen for the sake of endings | "One of the reasons I wanted to do an anthology format is, I like stories with endings" — "continuing serial dramas, they tend to have really good beginnings and really long middles and then sort of have to hustle to develop an ending. And I like the idea of telling a self-contained story." | **C5 Resolution** — extends it: a resolution should be architected from the start as an ending, not backfilled onto an open-ended structure | [Assignment X](https://www.assignmentx.com/2014/interview-creator-nic-pizzolatto-on-the-true-grit-of-true-detective/) |
| Standalone seasons, shared sensibility not shared plot | "There's no relationship between the stories or characters, which was the result of fully committing to something new, but I do think that the seasons have a deep, close bond in sensibility and vision, a similar soul, though this is a more complex world and field of characters." | **C3 Closed World** — extends it to the anthology/format level: each "case" (season) is a fully sealed closed world with no cross-case continuity, but tonal/thematic identity persists above the case level | [Medium — "Q&A: True Detective Creator and Showrunner Nic Pizzolatto"](https://medium.com/@TrueDetective/q-a-8cc72b62c1a) |
| Character work over conspiracy complexity | Originally pitched Season 2 as involving "the secret occult history of the United States transportation system," then dropped it: "a comment from very early in the process, and something I ended up discarding in favor of closer character work and a more grounded crime story. The complexity of the historical conspiracy first conceived detracted from the characters and their reality, I felt, and those characters are ultimately what have to shape the world and story." | **M1 Suspect Architecture** / **F2 Suspect's Wound** — direct craft precedent for character-driven over puzzle-driven construction: plot complexity should be pruned when it competes with character reality, not layered on for its own sake | [Medium — "Q&A: True Detective Creator and Showrunner Nic Pizzolatto"](https://medium.com/@TrueDetective/q-a-8cc72b62c1a) |
| Detective story as a backward-built narrative engine | "It puts you in everything. That's why they're great engines for stories. They go everywhere. A detective story is really just the way you tell a narrative – you start with the ending. At the end, this person is dead. Now I'm going to go back and piece together the story that led to it." | **C1 Crime** / **C5 Resolution** — reframes the P1 skeleton as a construction method, not just a checklist: author (and generator) should build forward from a fixed endpoint (the crime/death) rather than discover the ending along the way | [The Killing Times](https://thekillingtimestv.wordpress.com/2015/06/20/true-detectives-nic-pizzolatto-i-write-best-about-people-whose-souls-are-on-the-line/) |
| Mystery as irresolvable, not just solvable | On why he keeps returning to the detective framework: "It's about the final unknowability of any investigation." | New concept — tension with **C5 Resolution**: Pizzolatto treats ambiguity/unknowability as a craft value in itself, not a flaw to be closed out; sits uneasily with a game mechanic that requires a definite, provable solution | [Vanity Fair](https://www.vanityfair.com/hollywood/2015/06/nic-pizzolatto-true-detective-season-2-better-than-season-1) |
| Interrogation framing as an unreliable-narrator device | Season 1's writers' bible described the 2012 interview scenes as "sparse, confessional in their austerity, somewhat in the style of Errol Morris — a man speaking into a camera," built so that "the narrating voice may lie, but the images we see never will" — the dual timeline exists specifically to let the audience catch detectives lying in their own retelling. | **F3 Unreliable Frame** — near-exact match: a structural device (split timeline: testimony vs. flashback-truth) built explicitly to let the audience/player detect deception by comparing an unreliable account against ground truth | [CBR](https://www.cbr.com/true-detective-season-1-hid-cohle-hart-investigators-until-episode-6/) |
| Structure follows the story, not a house formula | On why Season 2 abandoned Season 1's split-timeline structure for a more linear one: "We were conscious of not wanting to repeat ourselves or remake the same album in a different setting, but I try to be open to whatever structure the story and characters suggest, so I never drew a line through those things." Also: "As the characters multiplied and their individual and group complications grew, a more integrated and linear structure worked best." | New concept — no direct P1–P4 analogue; candidate structural principle: timeline/framing complexity should scale with cast size and story needs, not be reused as a signature device across every case | [Den of Geek](https://www.denofgeek.com/tv/true-detective-season-2-analzying-nic-pizzolattos-interview-and-new-key-art/) |
| Multi-timeline as deliberate framing device, not a twist mechanism | On Season 3's return to a multi-timeline structure: "deliberate without being forced" — "Because of the ambition to spread this person's life over three time periods, that lent itself to using two of the time periods as narrative framing devices and then moving out of them as those time periods become their own stories." | New concept, related to **M6 Reveal Mechanic**: multiple timelines used as a *framing/access* device (how and when the audience learns things) rather than as a withheld-twist mechanism | [Collider](https://collider.com/true-detective-season-3-interview-nic-pizzolatto-mahershala-ali/) |
| Setting as a structural character | "The landscape is literally the third lead of the show." | **F4 Setting as Constraint** / **F13 Atmospheric Register** — setting isn't backdrop but an active structural element, comparable in weight to the two lead investigators | [The Arkham Digest](http://www.arkhamdigest.com/2014/01/interview-nic-pizzolatto-creatorwriter.html) |
| Character before mechanics, generally | "Authentic, vivid characters drive any story. After that, we look for refinements in language and detail, effective structure, the originality of the author's imagination." | **M1 Suspect Architecture** / **F2 Suspect's Wound** — reinforces character psychology as the load-bearing layer, with plot mechanics (structure, clue placement) explicitly secondary | [Florence in Print — "Writing advice from Nic Pizzolatto"](https://florenceinprint.com/writing-advice-from-nic-pizzolatto/) |

### New concepts flagged for taxonomy consideration

None of these exist in `extraction_protocols.py` P1–P4 yet — surfacing them here rather
than silently editing the taxonomy:

1. **Season/case-level closed world vs. cross-case continuity** — an anthology-specific
   extension of C3: each case must be a fully sealed closed world with zero narrative
   carryover to the next, while a *meta-level* sensibility/tone can still persist across
   cases. Relevant if the game ever supports multiple purchasable "seasons" or campaigns
   sharing a brand identity but not a plot.
2. **Backward-built narrative construction** — "start with the ending" as an authoring
   *method*, not just a structural requirement. Distinct from C5 (which describes what a
   resolution must contain); this is about generation order — fixing the crime/death first,
   then generating everything else to lead there, which is arguably how the generator
   already works but isn't named anywhere in the taxonomy.
3. **Irresolvability as a craft value** — Pizzolatto explicitly values a mystery's "final
   unknowability." This cuts against a game mechanic that needs a provably correct
   accusation, so it's flagged as a tension to be aware of rather than a concept to adopt
   wholesale — could inform optional "no clean answer" or ambiguous-culprit variants if the
   game ever wants that mode.
4. **Structure-scales-with-cast principle** — timeline/framing complexity (single reveal vs.
   split timeline vs. triple timeline) should track story/cast needs rather than be applied
   as a fixed template on every generated mystery.
5. **Timeline as framing/access device (distinct from M6 Reveal Mechanic)** — using multiple
   timelines to control *when* and *through whom* the player learns information, separate
   from the reveal-mechanic question of *how* the final answer is delivered.

**Caveat:** all quotes above were retrieved via `WebSearch` snippet/summary, not a full-text
`WebFetch` (assignmentx.com, thedailybeast.com, denofgeek.com, and similar hosts returned 403
per this session's egress policy). Scoped deliberately to craft commentary only —
Pizzolatto's 2014 plagiarism-allegation coverage was excluded as out of scope.

## Anthony Horowitz — *Magpie Murders*, *Foyle's War*, *Midsomer Murders*

| Concept | Insight | Maps to taxonomy | Source |
|---|---|---|---|
| Milieu-first plotting | On starting a new mystery: "What was its milieu? ... To me, this is always the most important question." He knows someone will kill someone else, but the driving questions come first: "but why? Who are they? What is their world?" For *Marble Hall Murders* the milieu (literary estates left behind by a dead author) generated the motive and cast before any clue or crime detail was decided. | Variant of **F4 Setting as Constraint**, but distinct in kind — F4 as currently scoped describes setting's *narrative function once chosen*; this is about *sequencing*: milieu is decided before crime, victim, or culprit. See "New concepts" below. | [Barnes & Noble — guest post by Anthony Horowitz](https://www.barnesandnoble.com/blog/anthony-horowitz-guest-post-marble-hall-murders/) |
| Milieu as "strangers thrown together" generator | Favors settings (hotels are a recurring example, *Moonflower Murders*) that plausibly assemble strangers or people who only half-know each other — the milieu's job is to manufacture a closed, socially mixed suspect pool, not just supply atmosphere. | **C3 Closed World**, **M4 Social World** — milieu choice is explicitly in service of generating the suspect architecture | [Novel Suspects — hotel-set mysteries roundup, summarizing Horowitz's stated approach](https://www.novelsuspects.com/book-list/suspenseful-novels-set-in-hotels-motels-and-inns/) (secondary attribution — corroborate before treating as verbatim) |
| Real history as the "envelope" for the mystery form | On why he built *Foyle's War* as a murder-mystery series rather than a straight war drama: "What I really wanted to do was to tell real stories that no one knew and to tell them in the envelope of a murder mystery series." He judged those true WWII stories (e.g. British restriction of Jewish emigration, a scandal in Churchill's secret army) would not have reached a mass audience without the mystery-genre packaging. | New concept — **genre-as-delivery-mechanism**: the whodunit shell is chosen instrumentally, to carry otherwise-hard-to-sell true material to a broad audience. No direct P1–P4 analogue. | [Anthony Horowitz's official site — "The return of Foyle's War"](https://anthonyhorowitz.com/journalism/article/the-return-of-foyles-war) (quote corroborated via multiple secondary summaries; recommend confirming exact wording against this primary source page) |
| Deliberately subverting the "solved-format" trope | Explicit reaction against the genre default: "After Midsomer Murders and Poirot, I wanted to write a slightly more complex drama which didn't just add up to 'oh yes, the butler did it!'" He used the WWII setting of *Foyle's War* to add a moral dimension — a detective who questions the relevance of solving one murder when hundreds of deaths are happening daily around him. | **C6 Investigator** / **M8 Investigator's Wound** — extends both: the investigator's doubt about the *worth* of solving the case is itself the subversion, not a twist on the culprit mechanic | [Midsomer Murders fan-archive writer page, quoting Horowitz on Foyle's War's origin](http://midsomermurders.org/anthonyhorowitz.htm) (secondary attribution; corroborate wording) |
| Meta-fictional mystery-within-a-mystery | *Magpie Murders*: a bestselling crime novelist dies under suspicious circumstances, and the clues to his real-world death are embedded in his own final, unfinished detective novel — giving the book two full mysteries, two suspect sets, and two solutions running in parallel. Horowitz has called constructing this "really difficult," noting the TV adaptation (from a ~630–640 page novel vs. his usual ~300) took two years and roughly half a dozen drafts to script into six episodes. | New concept — **nested mystery / mystery-as-evidence**: a second, fictional mystery functions as the evidence stream for a first, "real" one. No P1–P4 analogue — see below. | [Salon — "Magpie Murders is a metafiction marvel: Anthony Horowitz on adapting his mystery within a mystery"](https://www.salon.com/2022/10/23/magpie-mystery-pbs-anthony-horowitz-novel/) |
| Meta-fiction reframes the detective/narrator relationship | On writing himself as narrator opposite investigator Daniel Hawthorne in the Hawthorne & Horowitz series: "Turning myself into the narrator, the Watson to Hawthorne's Sherlock Holmes, turned the entire genre on its head." He frames the normal author/reader power relationship as inverted: the author is usually all-seeing, but as narrator-inside-his-own-book he is near-helpless — "If Hawthorne doesn't solve the crime, I won't even have a book!" | **F3 Unreliable Frame** (extends it — the narrator's stated helplessness is a structural device, not just a POV limitation), also touches **C6 Investigator**/sidekick dynamic (**F9 Sidekick/Foil**) | [Los Angeles Public Library — "Interview With an Author: Anthony Horowitz"](https://www.lapl.org/collections-resources/blogs/lapl/interview-author-anthony-horowitz) |
| Adapting inside someone else's established rules (screen-specific) | On writing for licensed/estate-owned properties (Poirot, Sherlock Holmes, James Bond) versus his own original work: "I have to be invisible, I have to hide inside the world of the original creators, obeying the rules, doing nothing that will annoy/upset their worldwide fans." Distinguishes this constrained mode from writing original material, where he has full authorial control. | New concept — **adaptation discipline / IP fidelity constraint**. Not covered by P1–P4, which assume original-mystery generation; relevant if the game ever licenses or emulates an existing IP's rules rather than generating fresh mysteries. | [Feathers of the Firebird — "Interview with Anthony Horowitz" (Sophie Masson, Aug 2016)](https://firebirdfeathers.com/2016/08/05/interview-with-anthony-horowitz/) |
| Page-to-screen is a distinct craft, not a transcription | Adapting his own 630–640-page *Magpie Murders* novel into a six-episode series required restructuring, not trimming — he called the mystery-within-a-mystery structure especially hard to carry onto screen, needing about two years and half a dozen drafts. The TV cut also gives Susan Ryeland direct on-screen scenes with the fictional detective Atticus Pünd (who exists only in the novel-within-the-novel) — a device the book doesn't use, exploiting a screen-native tool (shared physical framing of "real" and "fictional" characters) that prose can't replicate the same way. | Extends **M6 Reveal Mechanic** / **M7 Media/Audience** with a screen-specific corollary, echoing Rian Johnson's "medium-native fairness" concept already flagged in this document — visualizing the fictional detective as a physically co-present character is a TV-only device for making the nested mystery legible | [Salon — Anthony Horowitz interview](https://www.salon.com/2022/10/23/magpie-mystery-pbs-anthony-horowitz-novel/); device also described via [WTTW Chicago — "The Major Differences Between 'Magpie Murders' the TV Show and Book"](https://www.wttw.com/playlist/2022/11/15/magpie-muders-comparison) |

### New concepts flagged for taxonomy consideration

None of these exist in `extraction_protocols.py` P1–P4 yet — surfacing them here rather
than silently editing the taxonomy:

1. **Milieu-first sequencing** — Horowitz's single strongest, most repeated craft claim
   across interviews is that milieu (setting/social world) is chosen *before* victim, crime,
   or culprit, and that everything else is generated from it. This is different from F4
   Setting as Constraint, which (as currently scoped) describes what a chosen setting does
   narratively. This is about *creative process order* — a candidate note for
   `docs/WIRING.md`'s generation pipeline: consider whether the generator should sample/fix
   milieu before sampling crime/victim/culprit parts, mirroring how Horowitz says he works,
   rather than the current (implicit) order.
2. **Genre-as-delivery-mechanism** — using the whodunit shell instrumentally, to make
   otherwise hard-to-sell material (Horowitz's real WWII history in *Foyle's War*) palatable
   to a mass audience. Not directly applicable to mystery *generation* today, but relevant if
   the game ever wants "true crime" or historical-setting modes.
3. **Nested mystery / mystery-as-evidence** (*Magpie Murders*) — a second, fictional mystery
   embedded inside the frame mystery, where solving the embedded story supplies evidence for
   the frame story's solution. This is a much heavier structural device than anything in
   P1–P4 and would likely require its own protocol variant (two parallel C1–C6 skeletons,
   one embedded in the other) rather than a tweak to an existing code — flagging for
   discussion, not proposing changes here.
4. **Adaptation discipline / IP fidelity constraint** — craft rules for writing *inside*
   someone else's established universe/rules (estate-owned characters) versus generating an
   original mystery. Out of scope for the current generator (which always creates originals)
   but worth a one-line note if the game ever supports "in the style of X" modes bound by
   stricter rules.
5. **Screen-native nested-mystery legibility** — the *Magpie Murders* TV adaptation's device
   of letting Susan Ryeland physically interact on-screen with the fictional detective from
   the book-within-the-book (impossible in prose the same way) is a screen-specific technique
   for keeping a nested mystery legible to the audience. Related to, but distinct from, Rian
   Johnson's "medium-native clue fairness" already flagged above — this is about narrative
   *legibility* of a nested structure rather than fairness of individual clues.

**Caveat:** several rows above rely on secondary summaries/paraphrase from search-engine
snippets rather than a directly fetched primary page (barnesandnoble.com, salon.com,
lapl.org, firebirdfeathers.com, medium.com, anthonyhorowitz.com, crimereads.com, and
newstatesman.com all returned 403 on WebFetch this session). The milieu quote, the LAPL
"Watson" quote, and the Firebird "invisible" quote were each corroborated by two independent
search queries returning matching wording — higher confidence, but still unverified against
full source text.

---

## Sources

- Rian Johnson — [ScriptMag](https://scriptmag.com/interviews-features/rian-johnson-talks-screenwriting-and-what-classic-movies-can-teach-us), [No Film School](https://nofilmschool.com/rian-johnson-knives-out-screenplay), [PBS On Story](https://www.pbs.org/video/reinventing-the-classic-whodunnit-a-conversation-with-rian-johnson-7vtzs4/), [The Ringer](https://www.theringer.com/2023/01/25/tv/rian-johnson-interview-poker-face-peacock-natasha-lyonne)
- Steven Moffat — [Benjamin Grafton](https://benjamingrafton.com/interviews/2012/06/17/interview-with-stephen-moffat), [BBC News](https://feeds.bbci.co.uk/news/entertainment-arts-16266601), [Den of Geek](https://www.denofgeek.com/tv/sherlocks-fall-the-empty-hearse-and-magic-tricks/), [Empire](https://www.empireonline.com/movies/features/sherlock-series-3-secrets/), [Purdie Writing](http://purdiewriting.blogspot.com/2013/11/steven-moffat-on-writing.html), [PBS Masterpiece](https://www.pbs.org/video/masterpiece-sherlock-moffat-and-cumberbatch-on-the-reichenbach-fall/), [Glasgow Guardian](https://glasgowguardian.co.uk/2023/09/08/dr-who-is-sherlock-holmes-in-space-in-conversation-with-steven-moffat/)
- John Hoffman — [Gold Derby](https://www.goldderby.com/feature/john-hoffman-only-murders-in-the-building-showrunner-video-interview-2-1205830514/), [WGA East](https://www.wgaeast.org/onwriting/episode-65-john-hoffman-only-murders-in-the-building/), [Moviefone](https://www.moviefone.com/news/only-murders-in-the-building-interview-john-hoffman/), [Awards Radar](https://awardsradar.com/2022/06/22/john-hoffman-omitb/), [ScriptMag](https://scriptmag.com/interviews-features/creating-the-murder-mystery-comedy-with-only-murders-in-the-building-co-creator-and-showrunner-john-hoffman), [TheWrap](https://www.thewrap.com/only-murders-in-the-building-season-5-episode-10-john-hoffman-interview/)
- Chris Chibnall — [Royal Television Society](https://rts.org.uk/article/chris-chibnall-man-who-reinvented-cliffhanger), [Den of Geek](https://www.denofgeek.com/tv/chris-chibnall-interview-broadchurch-doctor-who-more/), [Fast Company](https://www.fastcompany.com/1683515/the-art-of-the-cliffhanger-broadchurch-creator-breaks-down-britains-most-tweeted-thriller), [Variety](https://variety.com/2014/tv/news/gracepoint-broadchurch-foxs-adaptation-differs-british-original-1201265784/), [IMDb](https://m.imdb.com/news/ni56224817/?ref_=nm_nwr_2), [AOL](https://www.aol.com/chris-chibnall-says-ended-broadchurch-170218365.html), [NPR](https://www.npr.org/2025/06/13/nx-s1-5276298/death-at-the-white-hart-when-the-publican-is-found-dead-everyones-a-suspect), [Great British Life](https://www.greatbritishlife.co.uk/magazines/dorset/26269470.broadchurch-writer-chris-chibnall-launching-book-bridport/)
- Nic Pizzolatto — [Assignment X](https://www.assignmentx.com/2014/interview-creator-nic-pizzolatto-on-the-true-grit-of-true-detective/), [Medium](https://medium.com/@TrueDetective/q-a-8cc72b62c1a), [The Killing Times](https://thekillingtimestv.wordpress.com/2015/06/20/true-detectives-nic-pizzolatto-i-write-best-about-people-whose-souls-are-on-the-line/), [Vanity Fair](https://www.vanityfair.com/hollywood/2015/06/nic-pizzolatto-true-detective-season-2-better-than-season-1), [CBR](https://www.cbr.com/true-detective-season-1-hid-cohle-hart-investigators-until-episode-6/), [Den of Geek](https://www.denofgeek.com/tv/true-detective-season-2-analzying-nic-pizzolattos-interview-and-new-key-art/), [Collider](https://collider.com/true-detective-season-3-interview-nic-pizzolatto-mahershala-ali/), [The Arkham Digest](http://www.arkhamdigest.com/2014/01/interview-nic-pizzolatto-creatorwriter.html), [Florence in Print](https://florenceinprint.com/writing-advice-from-nic-pizzolatto/)
- Anthony Horowitz — [Barnes & Noble](https://www.barnesandnoble.com/blog/anthony-horowitz-guest-post-marble-hall-murders/), [Novel Suspects](https://www.novelsuspects.com/book-list/suspenseful-novels-set-in-hotels-motels-and-inns/), [anthonyhorowitz.com](https://anthonyhorowitz.com/journalism/article/the-return-of-foyles-war), [midsomermurders.org](http://midsomermurders.org/anthonyhorowitz.htm), [Salon](https://www.salon.com/2022/10/23/magpie-mystery-pbs-anthony-horowitz-novel/), [LAPL](https://www.lapl.org/collections-resources/blogs/lapl/interview-author-anthony-horowitz), [Feathers of the Firebird](https://firebirdfeathers.com/2016/08/05/interview-with-anthony-horowitz/), [WTTW Chicago](https://www.wttw.com/playlist/2022/11/15/magpie-muders-comparison)

## Cross-source concepts worth flagging together

A few candidate new-taxonomy concepts were independently raised by more than one creator —
stronger signal than a single-source flag:

- **Production/process secrecy around the solution** (Moffat's cast-secrecy, Chibnall's
  watermarked scripts/NDAs) — two independent showrunners describe deliberately
  compartmentalizing who knows the solution and when, as its own craft discipline separate
  from the story itself.
- **Reveal/culprit as a late, mutable variable during construction** (Chibnall's changed-his-
  mind drafting and the Broadchurch/Gracepoint dual-solution case; Hoffman's parallel
  candidate-culprit development) — multiple creators treat "who did it" as something decided
  later and more provisionally than the C4-first framing the current taxonomy implies.
- **Medium-native fairness/legibility devices** (Johnson's sound-hidden clues; Horowitz's
  on-screen fictional-detective device in *Magpie Murders*) — screen affords fairness/clarity
  techniques prose structurally cannot use.
