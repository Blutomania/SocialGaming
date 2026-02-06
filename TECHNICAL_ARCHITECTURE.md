# Choose Your Mystery - Technical Architecture Plan

## System Overview

```
+------------------+     +-------------------+     +---------------------+
|                  |     |                   |     |                     |
|   Client Apps    +---->+   Game Server     +---->+   Mystery Engine    |
|  (Web/Mobile)    |     |   (Real-time)     |     |   (AI Generation)  |
|                  |     |                   |     |                     |
+------------------+     +--------+----------+     +----------+----------+
                                  |                           |
                                  v                           v
                         +--------+----------+     +----------+----------+
                         |                   |     |                     |
                         |   Game State DB   |     |  Mystery Knowledge  |
                         |   (Player/Session)|     |     Database        |
                         |                   |     |                     |
                         +-------------------+     +---------------------+
```

---

## 1. Mystery Knowledge Database (MKD)

The foundational data layer. This is a structured, curated database built from mystery literature, true crime, screenplays, forensic references, and podcast transcripts. The LLM references this database at generation time to produce mysteries that feel authentic, logically consistent, and narratively rich.

### 1.1 Data Sources & Ingestion Pipeline

```
+------------------+
|  Raw Sources     |
|  - Mystery novels|     +--------------+     +----------------+     +--------+
|  - Screenplays   +---->+ Ingestion    +---->+ NLP/Entity     +---->+  MKD   |
|  - True crime    |     | Pipeline     |     | Extraction     |     |        |
|  - Forensics     |     +--------------+     +----------------+     +--------+
|  - Podcasts      |
+------------------+
```

**Ingestion Pipeline Steps:**
1. **Source Acquisition** - Digitized texts, licensed content, public domain works
2. **Preprocessing** - OCR cleanup, transcript normalization, format standardization
3. **Entity Extraction (NLP)** - Characters, locations, weapons, motives, evidence types
4. **Relationship Mapping** - Who connects to whom, what evidence links to what suspect
5. **Classification & Tagging** - Crime type, era, setting, complexity, tone
6. **Human Review** - QA pass to validate extracted data accuracy
7. **Embedding Generation** - Vector embeddings for semantic search during generation

### 1.2 Database Schema

#### `crimes` - The Core Crime Templates
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| crime_type | ENUM | murder, robbery, kidnapping, fraud, arson, sabotage, poisoning, etc. |
| sub_type | VARCHAR | e.g., "locked room murder", "heist", "cold case" |
| setting_era | VARCHAR | modern, victorian, futuristic, medieval, etc. |
| setting_locale | VARCHAR | mansion, ship, space station, small town, etc. |
| complexity_rating | INT (1-10) | How many layers of deduction required |
| num_suspects_range | INT[] | Recommended min/max suspect count |
| estimated_playtime | INT | Minutes |
| tone | ENUM | noir, cozy, thriller, comedic, horror |
| source_work | VARCHAR | Original source reference |
| source_type | ENUM | novel, screenplay, true_crime, forensic_manual, podcast |

#### `character_archetypes` - Suspect/Witness Templates
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| archetype_name | VARCHAR | "the jealous spouse", "the loyal butler", "the corrupt official" |
| role_type | ENUM | suspect, witness, victim, bystander, red_herring |
| personality_traits | JSONB | Array of traits: nervous, calculating, charming, etc. |
| typical_motives | JSONB | greed, revenge, passion, cover-up, accident, ideology |
| speech_patterns | JSONB | Dialect hints, vocabulary level, verbal tics |
| deception_style | ENUM | deflects, over-explains, omits, lies_directly, half_truths |
| relationship_roles | JSONB | business_partner, family, romantic, rival, stranger |
| source_references | JSONB | Which works this archetype draws from |

#### `motives` - Why Crimes Happen
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| motive_category | ENUM | financial, passion, revenge, power, ideology, cover_up, accident |
| motive_detail | TEXT | Specific scenario description |
| complexity | INT (1-5) | How hard to uncover |
| common_evidence | JSONB | What clues typically point to this motive |
| red_herring_potential | INT (1-5) | How easily this motive misleads |
| associated_crime_types | UUID[] | FK to crimes |

#### `evidence_types` - Clues and Physical Evidence
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| evidence_category | ENUM | physical, testimonial, digital, forensic, circumstantial, documentary |
| evidence_name | VARCHAR | "bloody fingerprint", "forged letter", "alibi gap" |
| discovery_method | VARCHAR | How players find it (crime scene search, interrogation, lab analysis) |
| reliability | INT (1-5) | Can it be faked or misinterpreted? |
| points_to | ENUM | suspect, motive, timeline, location, weapon |
| is_red_herring_capable | BOOLEAN | Can this evidence type be used to mislead? |

#### `plot_structures` - Narrative Scaffolding
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| structure_name | VARCHAR | "classic whodunit", "unreliable witness", "hidden identity", etc. |
| act_breakdown | JSONB | What happens in each phase of investigation |
| twist_types | JSONB | Available plot twists compatible with this structure |
| min_suspects | INT | Minimum cast size for this structure to work |
| clue_chain_template | JSONB | Ordered sequence of discovery that leads to solution |
| misdirection_slots | INT | How many red herrings this structure supports |

#### `interrogation_patterns` - Dialogue Frameworks
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| pattern_name | VARCHAR | "the slow reveal", "contradicting testimony", "emotional breakdown" |
| trigger_conditions | JSONB | What player actions or evidence trigger this pattern |
| dialogue_beats | JSONB | Ordered emotional/informational beats in the conversation |
| breakpoint_clues | JSONB | What evidence causes the NPC to crack or change behavior |
| source_references | JSONB | Screenplays/novels this pattern is modeled after |

#### `forensic_procedures` - Realistic Investigation Methods
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| procedure_name | VARCHAR | "fingerprint analysis", "toxicology report", "phone records" |
| time_to_complete | VARCHAR | In-game time cost |
| accuracy_rate | FLOAT | Can it give false results? |
| reveals | JSONB | What information this procedure unlocks |
| requires | JSONB | Prerequisites (evidence collected, lab access, etc.) |

### 1.3 Vector Store (Semantic Layer)

In addition to the relational schema above, all text content is embedded into a **vector database** for semantic retrieval during mystery generation:

```
+---------------------+         +----------------------+
|  Relational DB      |         |  Vector Store        |
|  (PostgreSQL)       |         |  (pgvector / Pinecone)|
|                     |         |                      |
|  Structured fields  |         |  Text embeddings of: |
|  Relationships      |<------->|  - Scene descriptions|
|  Enums & filters    |         |  - Dialogue samples  |
|  Game state         |         |  - Character bios    |
|                     |         |  - Evidence narratives|
+---------------------+         +----------------------+
```

**Why both?** The relational DB handles structured queries ("give me all poison-related motives in a Victorian setting"), while the vector store handles semantic queries ("find character dialogue that feels like a nervous suspect hiding something").

---

## 2. Mystery Engine (AI Generation Layer)

The brain of the game. Takes a player prompt + MKD references and produces a complete, solvable mystery.

### 2.1 Generation Pipeline

```
Player Prompt                    Mystery Knowledge DB
"A murder on Mars"               (structured + vector)
        |                                |
        v                                v
+-------+--------------------------------+-------+
|                                                 |
|            MYSTERY ENGINE                       |
|                                                 |
|  Step 1: Context Assembly                       |
|    - Parse prompt for setting, tone, crime type |
|    - Query MKD for matching templates           |
|    - Retrieve relevant archetypes & structures  |
|                                                 |
|  Step 2: Skeleton Generation (LLM Call #1)      |
|    - Crime, victim, culprit, motive             |
|    - Cast of characters (5-8)                   |
|    - Evidence chain (solution path)             |
|    - Red herrings (2-3)                         |
|                                                 |
|  Step 3: Validation                             |
|    - Is the mystery logically solvable?         |
|    - Are there enough clues?                    |
|    - Are red herrings distinguishable?          |
|    - Does the timeline hold up?                 |
|                                                 |
|  Step 4: Content Expansion (LLM Call #2)        |
|    - Full character backstories & dialogue trees|
|    - Scene descriptions & searchable areas      |
|    - Evidence details & forensic reports        |
|    - Interrogation response matrices            |
|                                                 |
|  Step 5: Difficulty Calibration                 |
|    - Adjust clue visibility by player count     |
|    - Scale misdirection by difficulty setting   |
|                                                 |
+-------------------------------------------------+
        |
        v
  Complete Mystery Package (JSON)
  Ready for Game Server
```

### 2.2 Mystery Package Output Format

```json
{
  "mystery_id": "uuid",
  "setting": {
    "location": "Olympus Mons Research Station, Mars",
    "era": "2157",
    "atmosphere": "isolated, tense, claustrophobic"
  },
  "crime": {
    "type": "murder",
    "victim": { "name": "Dr. Yuki Tanaka", "role": "Lead Geologist" },
    "method": "poisoned oxygen supply",
    "time_of_death": "0300 station time"
  },
  "solution": {
    "culprit": "character_id_3",
    "motive": "cover up falsified research data",
    "evidence_chain": ["clue_1", "clue_5", "clue_8", "clue_12"]
  },
  "characters": [
    {
      "id": "character_id_1",
      "name": "Commander Sarah Wells",
      "role": "witness",
      "personality": "authoritative, hiding guilt about safety lapses",
      "knowledge": ["knows about airlock malfunction", "saw victim arguing"],
      "will_reveal_easily": ["airlock info"],
      "requires_pressure": ["the argument details"],
      "will_deny": ["her own negligence"],
      "dialogue_style": "military precision, clipped sentences"
    }
  ],
  "locations": [
    {
      "name": "Geology Lab",
      "searchable_items": ["research logs", "chemical cabinet", "security footage"],
      "clues_available": ["clue_1", "clue_3"],
      "red_herrings": ["unrelated chemical spill report"]
    }
  ],
  "clues": [
    {
      "id": "clue_1",
      "type": "physical",
      "description": "A half-empty vial of compound XR-7 in the geology lab",
      "points_to": "character_id_3",
      "discovery_method": "search geology lab chemical cabinet",
      "is_red_herring": false
    }
  ]
}
```

### 2.3 LLM Integration

| Component | Model | Purpose |
|-----------|-------|---------|
| Mystery skeleton generation | Claude / GPT-4 class | Complex reasoning for plot coherence |
| Character dialogue (real-time) | Claude Haiku / GPT-4o-mini | Fast responses during interrogations |
| Scene descriptions | Claude / GPT-4 class | Rich, atmospheric prose |
| Validation checks | Deterministic + LLM | Logic verification of solvability |
| Avatar generation | Stable Diffusion / DALL-E | Character portraits |
| Voice (future) | ElevenLabs / PlayHT | NPC voice during interrogations |

---

## 3. Game Server (Real-Time Multiplayer)

### 3.1 Architecture

```
                    +------------------+
                    |  Load Balancer   |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
       +------+------+ +----+----+ +-------+-----+
       | Game Server  | | Game    | | Game Server  |
       | Instance 1   | | Server 2| | Instance N   |
       +------+-------+ +----+----+ +------+------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------+---------+
                    |    Redis         |
                    |  (Session State  |
                    |   + Pub/Sub)     |
                    +--------+---------+
                             |
                    +--------+---------+
                    |   PostgreSQL     |
                    |  (Persistent     |
                    |   Game Data)     |
                    +------------------+
```

### 3.2 Real-Time Communication

- **WebSockets** for live game state updates (turn changes, shared evidence, chat)
- **REST API** for non-real-time operations (login, game creation, history)
- **Server-Sent Events** for spectator mode

### 3.3 Game State Management

```
Session Lifecycle:

  CREATE_GAME ──> LOBBY ──> SETUP ──> INVESTIGATE ──> SOLVE ──> RESULTS
                   │         │          │               │          │
                   │         │          │               │          │
                Players    Prompt     Turn-based      Guess      Winner
                join       entered    interrogations  phase      revealed
                           AI gen     scene searches  penalties  stats
                           starts     info sharing    tracked    saved
```

---

## 4. Client Architecture

### 4.1 Platform Strategy

**Phase 1 (MVP):** Web app (React/Next.js) - accessible on any device
**Phase 2:** Progressive Web App with offline support
**Phase 3:** Native mobile (React Native or Flutter)

### 4.2 Key UI Components

| Screen | Description |
|--------|-------------|
| Lobby | Join/create game, enter alias, share invite link |
| Setup | Enter mystery prompt, generate/select avatars, configure settings |
| Crime Scene | Interactive environment to search for clues |
| Interrogation | Chat-style interface with AI NPCs, real-time dialogue |
| Crime Board | Drag-and-drop evidence board, personal notes, shared vs. private zones |
| Info Sharing | Checkbox UI - select 75% of findings to share with group |
| Accusation | Final guess interface - select culprit, motive, evidence |
| Results | Solution reveal, scoring, shareable recap video |

---

## 5. Infrastructure & Deployment

### 5.1 Cloud Architecture

```
+--------------------------------------------------+
|                    AWS / GCP                      |
|                                                   |
|  +-------------+  +-------------+  +----------+  |
|  | ECS/GKE     |  | RDS/CloudSQL|  | S3/GCS   |  |
|  | (Game       |  | (PostgreSQL |  | (Assets, |  |
|  |  Servers)   |  |  + pgvector)|  |  Media)  |  |
|  +-------------+  +-------------+  +----------+  |
|                                                   |
|  +-------------+  +-------------+  +----------+  |
|  | ElastiCache |  | CloudFront/ |  | Lambda/  |  |
|  | (Redis)     |  | CDN         |  | Cloud Fn |  |
|  +-------------+  +-------------+  +----------+  |
|                                                   |
|  +-------------+  +-------------+                 |
|  | API Gateway |  | CloudWatch/ |                 |
|  |             |  | Monitoring  |                 |
|  +-------------+  +-------------+                 |
+--------------------------------------------------+
```

### 5.2 Cost Considerations

| Component | Cost Driver | Optimization Strategy |
|-----------|------------|----------------------|
| LLM calls (generation) | Per mystery generated (~$0.10-0.50) | Cache common elements, batch generation |
| LLM calls (interrogation) | Per message (~$0.002-0.01) | Use smaller models, limit turn count |
| Database | Storage + queries | Efficient indexing, read replicas |
| WebSockets | Concurrent connections | Connection pooling, auto-scaling |
| Image generation | Per avatar (~$0.02-0.04) | Cache popular styles, offer presets |

---

## 6. Development Phases

### Phase 1: Foundation (Months 1-3)
- [ ] Design and build Mystery Knowledge Database schema
- [ ] Build ingestion pipeline for first 50 source works
- [ ] Basic mystery generation with LLM + MKD retrieval
- [ ] Text-based prototype (2-3 players, web-only)
- [ ] Core info-sharing mechanic (75/25 checkbox UI)

### Phase 2: Playable Alpha (Months 4-6)
- [ ] Real-time multiplayer via WebSockets
- [ ] AI NPC interrogation (text chat)
- [ ] Crime scene search interface
- [ ] Crime board with drag-and-drop evidence
- [ ] MKD expanded to 200+ source works
- [ ] Mystery validation system (solvability checks)

### Phase 3: Visual & Social (Months 7-9)
- [ ] AI avatar generation integration
- [ ] Polished UI/UX with atmospheric design
- [ ] Shareable game recaps and highlights
- [ ] Spectator mode
- [ ] Analytics dashboard for game balance tuning

### Phase 4: Launch Prep (Months 10-12)
- [ ] Closed beta with target audience
- [ ] Performance optimization and load testing
- [ ] Monetization integration ($19.99 purchase)
- [ ] MKD expanded to 500+ source works
- [ ] Voice integration for NPC dialogue (stretch)

---

## 7. MKD Growth Strategy

The Mystery Knowledge Database is a **living asset** that grows over time:

```
Launch:     ~200 source works  ──>  ~500 character archetypes
Year 1:     ~500 source works  ──>  ~1,200 archetypes, 300 plot structures
Year 2:    ~1,000 source works ──>  ~2,500 archetypes, 800 plot structures
Ongoing:    Community submissions, partnership with publishers
```

**Content Partnerships to Pursue:**
- Public domain mystery works (Agatha Christie pre-1929, Arthur Conan Doyle, etc.)
- Licensed true crime databases
- Forensic science educational publishers
- Podcast networks (true crime transcripts)
- Screenplay databases (IMSDb, public domain scripts)

---

## 8. AI Cost Model & Revenue Sustainability

The core tension: every AI call costs money, but heavy AI usage is what makes the game special. The architecture must minimize cost-per-session without degrading the experience.

### 8.1 Cost Breakdown Per Game Session (4 players, 3 rounds)

| AI Call | When | Model Tier | Est. Cost | Frequency |
|---------|------|-----------|-----------|-----------|
| Mystery generation (skeleton) | Game start | Large (Claude/GPT-4) | $0.08-0.15 | 1x per game |
| Mystery validation (2nd pass) | Game start | Large | $0.05-0.10 | 1x per game |
| Incident video generation | Game start | Video (Runway/Sora) | $0.10-0.50 | 1x per game |
| Avatar generation | Setup | Image (SDXL/DALL-E) | $0.02-0.04 | 4x per game |
| NPC interrogation responses | Each "Talk to Witness" turn | Small (Haiku/4o-mini) | $0.002-0.01 | ~4-8x per game |
| Clue/scene descriptions | Each "Look for Clues" turn | Small | $0.001-0.005 | ~4-8x per game |
| Research results | Each "Do Research" turn | Small | $0.001-0.005 | ~2-4x per game |
| Solution reveal cinematic | Game end | Large + Video | $0.10-0.30 | 1x per game |

**Estimated total AI cost per game session: $0.50 - $1.50**

### 8.2 Cost Optimization Strategies

**Pre-generation (the biggest lever):**
- The mystery skeleton, all NPC backstories, all clue descriptions, and all possible interrogation responses can be generated ONCE at game start
- NPC dialogue doesn't need to be real-time generative for every message — the engine pre-generates a **response matrix**: what each NPC says based on which evidence the player has shown them
- This converts many small real-time LLM calls into one larger upfront call

```
INSTEAD OF:                          DO THIS:
  12 real-time LLM calls             1 large generation call at start
  during gameplay                    that pre-computes all responses
  ($0.01 each = $0.12)              ($0.15 once)
  + latency per turn                 + instant responses during play
```

**Smart model routing:**
- Use large models (Claude Sonnet/Opus, GPT-4) only for generation and validation
- Use small models (Claude Haiku, GPT-4o-mini) for any real-time dialogue that can't be pre-generated
- Use deterministic code (not AI) for evidence chain logic, timeline checks, and scoring

**Caching and reuse:**
- Scene descriptions for common settings (temple, marketplace) can be cached and lightly varied
- Character portrait styles can use preset bases with minor AI customization
- Common forensic analysis results can be templated

**The video question:**
- AI video generation is the most expensive single item ($0.10-0.50 per clip)
- Consider: is the incident video worth the cost, or could an illustrated slideshow with narration achieve 80% of the effect at 10% of the cost?
- Option A: Full AI video (premium experience, high cost)
- Option B: AI-generated still images + text narration (lower cost, still immersive)
- Option C: Video for paid tier, stills for free tier (if freemium model)

### 8.3 Revenue Model Options

At $19.99 one-time purchase with ~$1.00 AI cost per session:

| Sessions played | AI cost | Revenue | Margin |
|----------------|---------|---------|--------|
| 5 sessions | $5.00 | $19.99 | 75% |
| 20 sessions | $20.00 | $19.99 | 0% (breakeven) |
| 50 sessions | $50.00 | $19.99 | -150% (loss) |

**The one-time purchase model breaks down if players play frequently.** Alternatives:

**Option A: Freemium + Mystery Packs**
- Free: 2-3 curated mysteries (no AI generation cost)
- $4.99/pack: 5 AI-generated mystery sessions
- Effectively $1.00/session to the player, covering AI costs with margin

**Option B: Subscription**
- $4.99/month: Unlimited mysteries
- Works if average player plays 3-4x/month (cost ~$4, revenue $5)
- Risk: power users who play 15x/month

**Option C: Hybrid Purchase + Credits**
- $9.99 one-time: Game + 10 AI mystery credits
- $2.99 for 5 additional credits
- Players who play casually never pay more; frequent players buy credits

**Option D: Ad-supported free tier**
- Free with ads between rounds
- Premium ($9.99) removes ads + adds video cinematics + premium avatars

### 8.4 Cost Trajectory

AI costs are dropping rapidly. Architecture decisions made today should account for:
- LLM inference costs dropping ~50% per year
- Image generation costs dropping ~40% per year
- Video generation still maturing — costs will drop significantly as competition increases
- What costs $1.00/session today may cost $0.25/session in 2 years

**Recommendation:** Launch with a credit/session-based model that covers costs now, with the expectation of transitioning to a more generous model as costs decrease.

---

## 9. Security & Fair Play

- Mystery solutions are **never sent to the client** - all validation happens server-side
- Player guesses are submitted as sealed commitments (hashed) to prevent cheating in multiplayer
- Rate limiting on interrogation to prevent brute-force questioning
- AI responses are filtered for harmful content
- Player data stored with encryption at rest
