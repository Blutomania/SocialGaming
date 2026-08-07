# Choose Your Mystery - Data Acquisition Plan

## Phase 1: Content Sources & Collection (Weeks 1-4)

### A. Public Domain Mystery Novels
**Primary Sources:**
- Project Gutenberg (gutenberg.org) - 70,000+ free books, many mysteries
- Internet Archive (archive.org) - Millions of texts, searchable by genre
- Wikisource - Curated public domain texts
- Standard Ebooks - High-quality formatted public domain books

**Target Authors (Pre-1928):**
- Arthur Conan Doyle (Sherlock Holmes)
- Agatha Christie (early works)
- Edgar Allan Poe
- Wilkie Collins
- G.K. Chesterton

**Collection Method:**
- API access (Gutenberg has metadata API)
- Bulk download via rsync
- Web scraping with rate limiting (respect robots.txt)

### B. Public Court Transcripts
**Sources:**
- PACER (US Federal Court records) - paid access
- State court archives (varies by state)
- Famous trial transcripts (Scopes, OJ Simpson publicly available)

**Legal Note:** Court records are public but republication may have restrictions

### C. Creative Commons Mystery Content
**Sources:**
- Wattpad (filter by CC license)
- Archive of Our Own (AO3) - fan fiction, some CC licensed
- Reddit writing prompts (/r/WritingPrompts)
- NaNoWriMo community stories

### D. Screenplay Databases
**Sources:**
- Internet Movie Script Database (IMSDb)
- The Script Lab
- Drew's Script-O-Rama

**Legal Note:** Many screenplays posted are "for educational use" - verify licensing


## Phase 2: Database Schema Design (Weeks 3-5)

### Core Entity Structure

```
MYSTERY_SCENARIOS
├── scenario_id (UUID)
├── title
├── source_text (full text)
├── genre_tags []
├── setting (time_period, location, environment_type)
├── crime_type (murder, theft, fraud, etc.)
└── metadata (author, year, source_url, license)

CHARACTERS
├── character_id (UUID)
├── scenario_id (FK)
├── name
├── role (victim, suspect, witness, detective, red_herring)
├── archetype (butler, jealous_spouse, business_partner, etc.)
├── personality_traits []
├── motive (if suspect)
└── key_dialogue_samples []

EVIDENCE
├── evidence_id (UUID)
├── scenario_id (FK)
├── type (physical, testimonial, circumstantial)
├── description
├── relevance_to_solution (critical, supporting, red_herring)
└── discovery_context

MOTIVES
├── motive_id (UUID)
├── motive_type (greed, revenge, jealousy, self_preservation, etc.)
├── description
└── frequency_in_dataset

PLOT_BEATS
├── beat_id (UUID)
├── scenario_id (FK)
├── sequence_order
├── beat_type (crime_discovery, first_clue, revelation, twist, solution)
└── description
```

### Recommended Database Technology

**Option 1: PostgreSQL + Vector Extension (pgvector)**
- Pros: Relational structure + semantic search capability
- Use Case: Store structured data + embeddings for similarity search
- Why: You need both precise queries (get all "murder on spaceship" scenarios) AND semantic matching ("find mysteries with betrayal themes")

**Option 2: MongoDB + Pinecone/Weaviate**
- Pros: Flexible schema for varying story structures
- Use Case: Rapid prototyping, changing requirements
- Why: Mystery structures vary wildly; NoSQL allows flexibility

**Recommendation:** Start with PostgreSQL + pgvector
- Better for your structured data needs
- Can add vector search later
- More mature tooling
- Better for team collaboration


## Phase 3: Data Processing Pipeline (Weeks 4-8)

### Extraction Pipeline

```python
# Conceptual flow - not production code

1. RAW TEXT INGESTION
   ├── Download from source
   ├── Convert to standardized format (UTF-8 text)
   ├── Metadata extraction (author, year, source)
   └── Store raw text

2. NLP PROCESSING
   ├── Entity extraction (characters, locations)
   ├── Scene segmentation
   ├── Dialogue extraction
   └── Action/description separation

3. STRUCTURAL ANALYSIS
   ├── Identify crime type and method
   ├── Map character relationships
   ├── Extract evidence mentions
   ├── Timeline construction
   └── Solution pathway identification

4. SEMANTIC ENRICHMENT
   ├── Generate embeddings (OpenAI, Cohere, or open-source)
   ├── Topic modeling
   ├── Motive classification
   └── Archetype tagging

5. QUALITY VALIDATION
   ├── Completeness check (has crime, suspects, solution?)
   ├── Coherence scoring
   ├── Duplicate detection
   └── Manual review flagging
```

### Tools & Technologies

**Text Processing:**
- spaCy or NLTK for NLP
- LangChain for LLM integration
- Anthropic Claude for intelligent extraction

**Data Ingestion:**
- BeautifulSoup4 for web scraping
- Playwright for dynamic sites
- requests for API access

**Storage:**
- PostgreSQL for structured data
- S3/MinIO for raw text storage
- Redis for caching


## Phase 4: AI Integration Strategy (Weeks 6-12)

### Option A: Fine-Tuning Approach
- Requires large dataset (1000+ quality mysteries)
- Higher cost, higher quality
- Best for: Custom model behavior

### Option B: RAG (Retrieval Augmented Generation)
- Works with smaller dataset (100+ quality mysteries)
- Lower cost, more flexible
- Best for: Your use case (dynamic mystery generation)

### Option C: Hybrid Approach (RECOMMENDED)
1. Store structured patterns (motives, archetypes, plot beats) in database
2. Use RAG to retrieve relevant examples
3. Prompt engineer with retrieved context
4. Generate new mystery scenarios

**Example Flow:**
```
User Prompt: "Murder on Mars colony"
    ↓
Retrieve similar scenarios: 
  - Closed environment mysteries (submarine, space station, island)
  - Sci-fi settings
  - Murder mysteries with limited suspects
    ↓
Extract patterns:
  - Character archetypes (scientist, engineer, commander)
  - Common motives (resource scarcity, secrets, mission sabotage)
  - Evidence types (technical logs, surveillance, alibis)
    ↓
Generate new mystery using:
  - Retrieved examples as context
  - Structured templates from database
  - Claude API for creative generation
    ↓
Output: Complete mystery scenario
```


## Phase 5: Legal & Ethical Considerations

### Copyright Compliance
- ✅ Public domain (pre-1928 in US)
- ✅ Creative Commons licensed content
- ✅ Fair use for analysis (extracting patterns, not reproduction)
- ❌ Copyrighted full-text republication
- ⚠️ Court transcripts (public but verify republication rights)

### Best Practices
1. Keep source attribution metadata
2. Document licensing for each source
3. Don't reproduce full copyrighted texts
4. Extract patterns/structures, not verbatim content
5. Consult legal counsel before launch


## Success Metrics

### Data Quality Metrics
- Completeness rate: % of mysteries with all required elements
- Coherence score: AI-evaluated logical consistency
- Diversity score: Variety of settings, motives, methods
- Usability score: Can generate playable mystery from this data?

### Dataset Goals
- **Phase 1 Target:** 100 fully processed, high-quality mysteries
- **Phase 2 Target:** 500 mysteries with automated processing
- **Phase 3 Target:** 1000+ mysteries with quality validation


## Immediate Next Steps (This Week)

1. **Legal Review**
   - Consult with IP lawyer about fair use vs. licensing
   - Document your intended use case clearly

2. **Proof of Concept**
   - Manually process 5-10 public domain mysteries
   - Create database schema for these examples
   - Test generation with Claude API using these as context

3. **Tool Setup**
   - Set up PostgreSQL database
   - Create Python environment with spaCy, LangChain
   - Get API keys (Anthropic Claude, OpenAI for embeddings)

4. **First Extraction Script**
   - Build scraper for Project Gutenberg
   - Process one Sherlock Holmes story end-to-end
   - Validate data quality manually


## Budget Considerations

### One-Time Costs
- Legal consultation: $1,000-3,000
- Developer time (if outsourcing): $5,000-15,000
- Computing resources (cloud): $500-1,000

### Ongoing Costs
- API costs (Claude, embeddings): $200-500/month during processing
- Database hosting: $50-200/month
- Storage: $20-50/month


## Risk Mitigation

### Top Risks
1. **Legal liability** → Strict licensing compliance, legal review
2. **Data quality issues** → Manual validation of first 100 entries
3. **Insufficient data** → Start with smaller, high-quality dataset
4. **Technical complexity** → Build MVP with manual processing first
5. **Cost overruns** → Use open-source tools, cloud credits, staged approach


## Alternative Approaches to Consider

### Alternative 1: Synthetic Data Generation
- Use Claude to generate training mysteries from scratch
- Pros: No legal issues, perfect structure
- Cons: Less authentic, may lack variety
- Hybrid: Generate 50%, collect 50%

### Alternative 2: Crowdsourced Content
- Commission mystery writers on Fiverr/Upwork
- Pros: Custom content, full rights
- Cons: Expensive, time-consuming
- Cost: ~$100-300 per mystery

### Alternative 3: Licensing Existing Libraries
- Contact mystery publishers for licensing
- Pros: High quality, large quantity
- Cons: Expensive, may not allow AI training
- Cost: Potentially $10,000-100,000+

### Alternative 4: Pattern-Only Extraction
- Don't store full texts, only structural patterns
- Pros: Minimal legal risk, efficient storage
- Cons: Less rich for generation
- Best for: MVP approach
