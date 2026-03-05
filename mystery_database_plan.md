# Choose Your Mystery — Strategic Plan

## Current Status (2026-03-05)

### Complete (POC)
- Full schema with `PhysicalClue` / `TestimonialRevelation` split
- `mystery_data_acquisition.py`: Gutenberg scraper + Claude extraction
- `mystery_generator.py`: RAG-based generator from prompts
- `gameplay_validator.py`: Automated quality checks
- `demo_acquisition.py`: No-API demo (Victorian locked room)
- Six test query definitions in `test_queries/`
- `MYSTERY_EXTRACTION_REQUIREMENTS.md`: Canonical schema spec
- `CLAUDE.md`: Session continuity guide

### In Progress
- Testing the six canonical queries through the full pipeline
- Manual review of generator output quality

### Not Yet Started
- Parquet dataset parsing (source not yet confirmed)
- PostgreSQL + pgvector migration
- Game server integration
- NPC dialogue generation
- Player knowledge tracking (75/25 sharing interface)

---

## Phase 1: POC Validation (Current)

**Goal:** Confirm the schema works for all six test queries.

**Steps:**
1. Run `demo_acquisition.py` → validate with `gameplay_validator.py`
2. Process 3-5 Gutenberg mysteries to seed the RAG database
3. Generate all six test queries
4. Validate each generated output
5. Manual review: do the mysteries hold logical water?
6. Identify and fix schema gaps revealed by testing

**Success criteria:**
- All six test queries produce mysteries that pass `gameplay_validator.py`
- Generated mysteries pass human review for logical coherence
- Validator pass rate > 80% before manual fixes

---

## Phase 2: Quality & Scale (Next 4-8 Weeks)

**Goal:** Build a high-quality RAG database of 50-100 processed mysteries.

**Steps:**
1. Process 50-100 Gutenberg mysteries (prioritize diverse settings and crime types)
2. Manual spot-check 10-20 extractions for quality
3. Tune Claude extraction prompts based on common failure modes
4. Build genre diversity into the corpus:
   - At least 10 different eras represented
   - At least 5 different crime types
   - At least 3 different mystery types (whodunit, locked_room, procedural)

**Target distribution:**
- By mystery type: 40% whodunit, 30% locked_room, 20% procedural, 10% other
- By difficulty: 30% easy, 50% medium, 20% hard

---

## Phase 3: Production Infrastructure

When scaling beyond ~1,000 mysteries or adding multiple simultaneous users.

### Database Migration: PostgreSQL + pgvector

**Why:**
- JSON files: O(n) search; limited query capabilities
- PostgreSQL: relational queries + vector similarity search

**Schema (PostgreSQL):**
```sql
CREATE TABLE scenarios (
    scenario_id UUID PRIMARY KEY,
    title TEXT,
    crime_type TEXT,
    mystery_type TEXT,
    world_era TEXT,
    world_tech_level TEXT,
    stakes TEXT,
    embedding VECTOR(1536),
    full_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON scenarios (crime_type, world_era, world_tech_level);
CREATE INDEX ON scenarios USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE character_patterns (
    id UUID PRIMARY KEY,
    scenario_id UUID REFERENCES scenarios,
    archetype TEXT,
    role TEXT,
    faction TEXT,
    motive_type TEXT
);

CREATE TABLE clue_patterns (
    id UUID PRIMARY KEY,
    scenario_id UUID REFERENCES scenarios,
    category TEXT,
    relevance TEXT,
    analysis_required BOOLEAN,
    tech_level TEXT
);
```

**Migration steps:**
1. Export existing JSON scenarios to SQL
2. Generate embeddings (Claude or sentence-transformers)
3. Migrate retrieval in `mystery_generator.py` to vector search
4. Keep JSON export for backward compatibility

### Caching: Redis
- Cache generated mysteries (avoid regenerating identical prompts)
- TTL: 24 hours for generated mysteries

### Async Processing
- Current: sequential API calls (~30s per mystery)
- With asyncio: parallel extraction passes (~10s per mystery)
- 3x speedup for batch processing

---

## Phase 4: Game Integration

### API Endpoint

```python
@app.route('/api/generate-mystery', methods=['POST'])
def generate_mystery():
    data = request.json
    mystery = generator.generate_mystery(data['prompt'], data['num_players'])
    validation = validator.validate(mystery)

    return {
        'mystery_id': mystery['scenario_id'],
        'title': mystery['title'],
        'discovery_scenario': mystery['discovery_scenario'],
        'surface_observations': mystery['surface_observations'],
        # Do NOT send: solution, culprit_name, is_culprit, hidden_details
    }
```

### Player Knowledge Tracking

```python
class PlayerKnowledge:
    def __init__(self, player_id: str):
        self.known_clues: List[str] = []        # clue_XXX IDs
        self.known_testimonies: List[str] = []   # testimony_XXX IDs

    def get_sharing_decision(self):
        """Player must share 75% each round."""
        all_items = self.known_clues + self.known_testimonies
        num_to_share = max(1, int(len(all_items) * 0.75))
        return {
            'all_items': all_items,
            'must_share': num_to_share,
            'can_withhold': len(all_items) - num_to_share
        }
```

### NPC Dialogue Generation (Future)

Each `TestimonialRevelation` has a `trigger_condition`. Use Claude to generate
NPC dialogue in response to player questions:

- If question matches `trigger_condition` → reveal the testimony
- If no match → generate in-character deflection using `interrogation_behavior`

---

## Content Source Strategy

### Current: Project Gutenberg (Public Domain)

✅ Legal for extraction and pattern use
✅ Rich variety of mystery styles
⚠️ Mostly pre-1928, mostly Western, mostly English

**Target authors for initial corpus:**
- Arthur Conan Doyle (Sherlock Holmes — procedural, Victorian)
- Agatha Christie (early works — cozy, whodunit)
- G.K. Chesterton (Father Brown — moral/philosophical)
- Edgar Allan Poe (gothic, early detective)
- Wilkie Collins (sensation, Victorian)

### Gap: Non-Western, Historical, Sci-Fi Settings

The six test queries require settings not covered by Gutenberg.

**Option A: Synthetic generation**
Use Claude to generate training mysteries for underrepresented settings.
- Pro: No legal issues, perfect schema compliance
- Con: Less authentic

**Option B: Manual pattern injection**
Write 5-10 high-quality examples per underrepresented setting type.
- Pro: High quality, game-specific
- Con: Labor intensive

**Recommendation:** Option B for the six test query categories.

---

## Parquet Dataset Integration

If a parquet dataset of mystery scenarios becomes available:

1. Confirm dataset schema (column names, data types)
2. Create `parquet_ingestion.py`:
   ```python
   import pandas as pd
   from mystery_data_acquisition import MysteryDatabase

   def ingest_parquet(file_path: str):
       df = pd.read_parquet(file_path)
       db = MysteryDatabase()
       for _, row in df.iterrows():
           scenario = row_to_mystery_scenario(row)  # map columns to schema
           db.save_scenario(scenario)
   ```
3. Run through `gameplay_validator.py` after ingestion

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Validator pass rate (generated) | >90% |
| All 6 test queries pass validation | 100% |
| Difficulty distribution | 30/50/20% E/M/H |
| Human review rating | >4/5 |
| Generation time | <30s |

---

## Budget

| Activity | Cost |
|----------|------|
| Process 100 Gutenberg mysteries | ~$25 |
| Generate 200 test mysteries | ~$30 |
| Production API costs | ~$50-200/month |
| Production database hosting | ~$50-100/month |
| **MVP total (one-time)** | **~$55** |

For comparison: human mystery writers charge $100-300 per mystery.

---

## Legal

✅ Project Gutenberg content: Public domain (pre-1928)
✅ Pattern extraction (not full text reproduction): Generally acceptable
⚠️ AI-generated content for commercial use: Consult Anthropic's terms
❌ Copyrighted novels without permission
❌ Full text reproduction of copyrighted works

**Before commercial launch:** IP attorney review recommended.
