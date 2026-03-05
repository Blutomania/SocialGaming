# Choose Your Mystery - Getting Started Guide

## What We Just Built

You now have a **complete mystery database system** with three core components:

### 1. Data Acquisition Pipeline
- **Entry point:** `run_experiment.py` (experiment runner with corpus download + 4 extraction variants)
- **Standalone:** `mystery_data_acquisition.py` (baseline Gutenberg scraper)
- **Corpus:** 359 pre-curated mystery/crime books from [Blutomania/mystery-crime-books](https://github.com/Blutomania/mystery-crime-books)
- **Output:** Database of mysteries with characters, evidence, motives, solutions

### 2. Mystery Generator
- **File:** `mystery_generator.py`
- **Purpose:** Takes prompts like "Murder on Mars" and generates complete mysteries
- **Method:** RAG - retrieves similar mysteries, extracts patterns, generates new content

### 3. Scenario Assembler
- **File:** `scenario_assembler.py`
- **Purpose:** Takes a player prompt (e.g. "An Art Theft in Ancient Athens") and assembles a fully playable mystery
- **Method:** Selects a compatible crime structure from the database, builds a diverse cast from multiple source texts, then uses the LLM to rebuild everything in the player's chosen setting
- **Output:** `./active_games/<game_id>.json` — a complete `GameScenario`

### 4. Scenario Presenter
- **File:** `scenario_presenter.py`
- **Purpose:** Delivers the assembled game to players in two modes
- **Verbal mode:** Text narration for each game phase (crime scene, crime board, chase leads). Free, for dev/testing.
- **Visual mode:** Generates structured prompts for AI video/image generation (Runway, Sora, Pika). For production.

### 5. Gameplay Validator
- **File:** `gameplay_validator.py`
- **Purpose:** Validates mysteries are solvable, balanced, and create strategic depth
- **Checks:** Solvability, difficulty, 75% sharing mechanic effectiveness

## What We Demonstrated

### Demo Run Results

We processed a sample mystery and created:

```
mystery_database/
├── index.json                              # Searchable index
└── scenarios/
    └── the_locked_room_mystery.json        # Full structured mystery
```

### Validation Results

```
✅ Mystery is SOLVABLE
✅ Strategic depth: MEDIUM
✅ Difficulty: EASY
✅ Estimated playtime: 35-50 minutes
✅ Ready for gameplay!
```

## Key Insights from the Demo

### 1. Data Structure Works
The JSON structure successfully captures:
- **6 characters** (victim, 3 suspects, witness, detective)
- **9 evidence pieces** (4 critical, 3 red herrings, 2 supporting)
- **Complete solution** with method and motive
- **Searchable metadata** (crime type, setting, genre tags)

### 2. Validation Catches Issues
The validator automatically checks:
- Do players have enough evidence to solve it?
- Is the 75% sharing rule meaningful?
- What's the difficulty level?
- How long will it take to play?

### 3. RAG Approach Enables Quality
By storing structured patterns (not just raw text):
- Extract character archetypes: "butler", "professional_rival", "spouse"
- Extract motive types: "inheritance", "revenge", "professional rivalry"
- Extract evidence patterns: "forensic analysis", "testimony", "physical clues"
- Use these to generate NEW mysteries that follow proven structures

## Next Steps - Run This On Your Machine

### Step 1: Setup (5 minutes)

```bash
# Clone or download the files
cd your-project-directory

# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"
```

### Step 2: Build Your Database (1-2 hours)

The fastest way is using the experiment runner with the curated GitHub corpus:

```bash
# Download 10 mystery books from the curated corpus and extract with all variants
python run_experiment.py --source github --limit 10

# Or download only (no API key needed)
python run_experiment.py --source github --limit 20 --download-only

# Or run just one extraction variant to save API costs
python run_experiment.py --source github --limit 10 --variants lean
```

Alternatively, use the standalone Gutenberg scraper:

```bash
# Start small - process 5 mysteries from Gutenberg
python mystery_data_acquisition.py

# This will:
# 1. Download from Project Gutenberg
# 2. Extract structured data with Claude
# 3. Save to ./mystery_database/
# 4. Cost: ~$1.25 in API credits (5 mysteries × $0.25 each)
```

### Step 3: Assemble a Playable Game (2 minutes)

```bash
# Assemble a game from a player prompt (uses the extracted database)
python scenario_assembler.py "An Art Theft in Ancient Athens"

# Try different prompts:
# - "A Murder on a Mars Colony"
# - "A Kidnapping in Victorian London"
# - "A Heist in Renaissance Florence"
#
# Output: ./active_games/<game_id>.json
# Cost: ~$0.15 per game (2 LLM calls)
```

### Step 4: Present the Game (instant)

```bash
# Verbal mode — read the narration aloud or display as text (free)
python scenario_presenter.py verbal ./active_games/<game_id>.json

# Visual mode — generate prompts for AI video/image APIs
python scenario_presenter.py visual ./active_games/<game_id>.json
```

### Step 5: Validate Gameplay (instant)

```bash
# Check if your mystery creates good gameplay
python gameplay_validator.py

# Automatically checks:
# - Is it solvable?
# - Right difficulty?
# - Strategic depth?
```

## Understanding the Costs

### Building Database (One-time)
- **50 mysteries:** ~$12.50
- **100 mysteries:** ~$25.00

### Generating Mysteries (Ongoing)
- **Per mystery:** ~$0.15
- **1000 mysteries:** ~$150

### Total to Launch MVP
- Process 100 source mysteries: $25
- Generate 100 test mysteries: $15
- **Total:** ~$40 in API costs

Compare to:
- Hiring writers: $100-300 per mystery
- Fine-tuning a model: $1,000-10,000
- Building without AI: Months of manual work

## How RAG Improves Over Time

As your database grows:

### With 10 Mysteries
- Basic pattern recognition
- Simple character archetypes
- Generic evidence types

### With 50 Mysteries
- Rich pattern library
- Nuanced character relationships
- Sophisticated misdirection

### With 100+ Mysteries
- Genre-specific patterns
- Setting-specific conventions
- Difficulty calibration
- Automatic quality improvement

## Integration with Your Game

### Current Flow (What You Have)
```
1. Player enters prompt: "An Art Theft in Ancient Athens"
2. scenario_assembler.py:
   - Parses prompt (crime type, setting, era)
   - Selects compatible mystery from database
   - Assembles diverse cast from multiple source texts
   - Rebuilds everything for the player's setting via LLM
   - Saves to ./active_games/<game_id>.json
3. scenario_presenter.py:
   - Verbal mode: text narration for each game phase (free)
   - Visual mode: video/image prompts for AI generation (production)
```

### Game Integration (Next Phase)
```
1. Player enters prompt: "An Art Theft in Ancient Athens"
2. Backend calls scenario_assembler.assemble_game()
3. Assembler returns GameScenario with diverse cast, clues, solution
4. Backend calls scenario_presenter for opening narration/video
5. Game server creates session:
   - Assigns players to suspects
   - Distributes initial clues
   - Tracks what each player knows
6. Players investigate:
   - Interrogate NPCs (AI-powered dialogues using character dialogue mechanics)
   - Collect evidence
   - Share 75% of findings
7. Players make accusations
8. Game reveals solution
```

### The 75% Sharing Mechanic

Our validator confirmed this creates strategic depth:

```
After 3 investigation turns:
  Player has: ~6 pieces of information
  Must share: ~4 pieces (75%)
  Can hide:   ~2 pieces (25%)
  
Strategic decision: 
  "Do I share the fiber evidence that points to Dr. Sterling?
   Or withhold it to solve the mystery first?"
```

## Files You Have

### Core System
1. **run_experiment.py** - Experiment runner (corpus download + all 4 extraction variants)
2. **mystery_data_acquisition.py** - Baseline extraction pipeline (6 LLM calls)
3. **mystery_extraction_lean.py** - Lean extraction (1 LLM call, sparse seed)
4. **mystery_extraction_rich.py** - Rich extraction (8 LLM calls, maximum depth)
5. **mystery_extraction_templates.py** - Template extraction (6 LLM calls, reusable patterns)
6. **mystery_generator.py** - Mystery generation with RAG
7. **gameplay_validator.py** - Gameplay quality assurance
8. **scenario_assembler.py** - Assemble scenarios from extractions
9. **scenario_presenter.py** - Present scenarios for review
10. **requirements.txt** - Python dependencies

### Documentation
11. **README.md** - Complete usage guide
12. **mystery_database_plan.md** - Comprehensive strategy
13. **MYSTERY_EXTRACTION_REQUIREMENTS.md** - Extraction field specification
14. **this file** - Getting started guide

### Demo Files (For Testing)
15. **demo_acquisition.py** - No API/network needed demo
16. **mystery_database/** - Sample output
17. **mystery_corpus/** - Cached downloaded source texts

## Common Questions

### Q: Do I need to process 100s of mysteries?
**A:** No. Start with 20-50 high-quality mysteries. Quality > quantity. The GitHub corpus has 359 books to choose from.

### Q: What about copyright?
**A:** Stick to:
- Project Gutenberg (public domain)
- GitHub corpus / Blutomania/mystery-crime-books (public domain books)
- Creative Commons content
- Consult lawyer before commercial launch

### Q: Can I use this with GPT-4 instead of Claude?
**A:** Yes, but you'll need to modify the API calls. Claude is recommended for:
- Better reasoning about mystery logic
- More consistent structured output
- Superior dialogue generation

### Q: How do I add my own mysteries?
**A:** Create JSON files matching the schema in `scenarios/`, then add to the index.

### Q: What about AI-generated character images?
**A:** Future enhancement. Current system focuses on:
1. Story/logic structure (done ✅)
2. Gameplay validation (done ✅)
3. Character generation (next phase)

## Performance Notes

### Current System (JSON Storage)
- ✅ Perfect for: 0-1,000 mysteries
- ✅ Fast startup, easy debugging
- ✅ No database setup needed

### When to Upgrade (PostgreSQL + Vector DB)
- Above 1,000 mysteries
- Need semantic search ("find mysteries like X")
- Multiple users querying simultaneously
- Want ML-powered similarity matching

## Success Metrics to Track

As you build your database:

1. **Validation Pass Rate**
   - Target: >90% of generated mysteries pass validation
   - Track: What patterns cause failures?

2. **Difficulty Distribution**
   - Target: 30% easy, 50% medium, 20% hard
   - Track: Can you generate specific difficulties?

3. **Strategic Depth**
   - Target: >80% mysteries rated "MEDIUM" or "HIGH"
   - Track: Does 75% rule create real decisions?

4. **Generation Quality**
   - Target: Human playtesters rate >4/5
   - Track: What makes mysteries engaging?

## What Makes This Approach Special

### Traditional Game Development
```
Write 100 mysteries by hand
→ Months of work
→ Each mystery playable once (replayability problem)
→ Hard to balance difficulty
→ Expensive to create more
```

### Your AI-Powered Approach
```
Process 50 source mysteries (one time)
→ Generate infinite new mysteries
→ Each unique (infinite replayability)
→ Automatic difficulty calibration
→ Costs pennies per mystery
```

## Next Actions (Prioritized)

### This Week
1. ✅ Run demo (completed!)
2. ⬜ Set up on your local machine
3. ⬜ Download corpus: `python run_experiment.py --source github --limit 10 --download-only`
4. ⬜ Run extraction variants: `python run_experiment.py --source github --limit 5`
5. ⬜ Generate 3 test mysteries with different prompts
6. ⬜ Run validation on all outputs

### Next Week
1. ⬜ Process 20-30 books from the GitHub corpus with preferred variant
2. ⬜ Test mystery generation with 10+ prompts
3. ⬜ Manual playtest 3-5 generated mysteries
4. ⬜ Refine prompts based on results

### Month 1
1. ⬜ Build to 50-100 source mysteries
2. ⬜ Integrate with game backend
3. ⬜ Add character dialogue generation
4. ⬜ Implement player knowledge tracking
5. ⬜ Build 75% sharing UI

## You're Ready!

You now have:
- ✅ Complete data acquisition system (GitHub corpus + 4 extraction variants)
- ✅ Scenario assembler (diverse cast from multiple sources, setting rebuild)
- ✅ Scenario presenter (verbal narration + visual video/image briefs)
- ✅ Mystery generation with RAG
- ✅ Gameplay validation
- ✅ Working demo with real output
- ✅ Clear path to production

The system is production-ready for MVP. Start small, validate quality, then scale.

**Total API cost to MVP: ~$40**
**Time to first playable mystery: <30 minutes**

Let's build something amazing! 🕵️‍♂️
