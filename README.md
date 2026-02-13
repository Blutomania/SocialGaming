# Choose Your Mystery - Database Development Guide

## Overview

This repository contains the data acquisition and processing pipeline for building a mystery game database. The system:

1. **Acquires** mystery content from a curated GitHub corpus or Project Gutenberg
2. **Processes** raw text into structured data using Claude AI (four extraction variants)
3. **Stores** mysteries in a searchable database
4. **Generates** new mystery scenarios by combining patterns from the database

## Quick Start

### Prerequisites

```bash
# Python 3.8+
python --version

# Install dependencies
pip install -r requirements.txt

# Set up API key
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Step 1: Acquire Mystery Data

The recommended approach uses the **experiment runner** with the pre-curated GitHub corpus (359 mystery/crime books from [Blutomania/mystery-crime-books](https://github.com/Blutomania/mystery-crime-books)):

```bash
# Download 10 mystery books from the curated corpus and run all extraction variants
python run_experiment.py --source github --limit 10

# Or just download the corpus without processing
python run_experiment.py --source github --limit 20 --download-only

# Alternatively, scrape Project Gutenberg directly
python run_experiment.py --source gutenberg --query "sherlock holmes" --limit 3
```

You can also run the standalone acquisition script:

```bash
# This will download and process 3 Sherlock Holmes stories from Gutenberg
python mystery_data_acquisition.py
```

**What this does:**
- Downloads full-text mystery books (from GitHub corpus or Project Gutenberg)
- Extracts characters, evidence, motives using Claude AI
- Saves structured data to `./mystery_database/`

**Output:**
```
mystery_database/
├── index.json                    # Searchable index
├── scenarios/                    # Processed mysteries
│   ├── the_hound_of_the_baskervilles.json
│   ├── a_study_in_scarlet.json
│   └── ...
└── raw_texts/                    # Original source texts
```

### Step 2: Generate New Mysteries

```bash
# This generates a "Murder on Mars" mystery
python mystery_generator.py
```

**What this does:**
- Analyzes your prompt ("A murder on Mars")
- Retrieves similar mysteries from database
- Extracts patterns (character types, motives, evidence structures)
- Uses Claude to generate a complete new mystery
- Saves to `./mystery_database/generated/`

**Output:**
```json
{
  "title": "Red Planet Requiem",
  "setting": {
    "location": "Meridian Colony, Mars",
    "environment": "Research station dome",
    ...
  },
  "characters": [...],
  "evidence": [...],
  "solution": {...}
}
```

## Architecture

### Data Flow

```
User Prompt: "A murder on Mars"
    ↓
[1] Theme Extraction
    Extract: sci-fi setting, murder, closed environment
    ↓
[2] Database Retrieval
    Find similar: "Orient Express", "Submarine mystery", "Space station"
    ↓
[3] Pattern Extraction  
    Extract: Character archetypes, motive types, evidence patterns
    ↓
[4] AI Generation (Claude)
    Combine: User prompt + Retrieved patterns + Creative generation
    ↓
Complete Mystery Scenario
```

### Data Model

```
MysteryScenario
├── Metadata (title, author, source, license)
├── Classification (crime type, setting, genre tags)
├── Characters[]
│   ├── name, role (victim/suspect/witness)
│   ├── archetype (butler, spouse, rival)
│   ├── motive, alibi, secrets
│   └── personality, relationships
├── Evidence[]
│   ├── description, type, relevance
│   ├── location, what_it_reveals
│   └── analysis requirements
├── Solution
│   ├── culprit, method, motive
│   ├── key evidence, timeline
│   └── deduction path
└── Gameplay Data
    ├── investigation locations
    ├── difficulty, playtime
    └── strategic tips
```

## File Structure

```
choose-your-mystery/
├── run_experiment.py                # Experiment runner (download + all variants)
├── mystery_data_acquisition.py      # Baseline extraction (6 LLM calls)
├── mystery_extraction_lean.py       # Lean extraction (1 LLM call)
├── mystery_extraction_rich.py       # Rich extraction (8 LLM calls)
├── mystery_extraction_templates.py  # Template extraction (6 LLM calls)
├── mystery_generator.py             # Generate new mysteries via RAG
├── gameplay_validator.py            # Validate mystery solvability
├── scenario_assembler.py            # Assemble scenarios from extractions
├── scenario_presenter.py            # Present scenarios for review
├── demo_acquisition.py              # Demo (no API/network needed)
├── mystery_database_plan.md         # Comprehensive strategy doc
├── MYSTERY_EXTRACTION_REQUIREMENTS.md  # Extraction field spec
├── GETTING_STARTED.md               # Getting started guide
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── mystery_corpus/                  # Downloaded source texts (cached)
└── mystery_database/                # Processed output
    ├── index.json
    ├── scenarios/
    ├── generated/
    └── raw_texts/
```

## Corpus Sources

| Source | Flag | Description |
|--------|------|-------------|
| **GitHub corpus** | `--source github` | 359 pre-curated mystery/crime books from [Blutomania/mystery-crime-books](https://github.com/Blutomania/mystery-crime-books). Recommended. |
| **Project Gutenberg** | `--source gutenberg` | Search-based scraping. Use `--query` to specify terms. |

## Extraction Variants

The experiment runner (`run_experiment.py`) supports four extraction strategies:

| Variant | LLM Calls | Description |
|---------|-----------|-------------|
| `baseline` | 6 | Moderate detail, balanced cost/quality |
| `lean` | 1 | Single-call sparse seed, cheapest |
| `rich` | 8 | Maximum depth, most expensive |
| `template` | 6 | Reusable patterns and archetypes |

```bash
# Run specific variants
python run_experiment.py --source github --limit 5 --variants lean,rich

# Run all variants for comparison
python run_experiment.py --source github --limit 3 --variants baseline,lean,rich,template
```

## Usage Examples

### Custom Mystery Generation

```python
from mystery_generator import MysteryGenerator

generator = MysteryGenerator()

# Generate mystery for different prompts
mystery = generator.generate_mystery(
    user_prompt="An art theft in Renaissance Venice",
    num_players=6
)

# Access structured data
print(f"Title: {mystery['title']}")
print(f"Suspects: {len([c for c in mystery['characters'] if c['role'] == 'suspect'])}")
print(f"Culprit: {mystery['solution']['culprit']}")

# Save for game use
generator.save_generated_mystery(mystery)
```

### Database Search

```python
from mystery_data_acquisition import MysteryDatabase

db = MysteryDatabase()

# Find all murder mysteries in mansions
results = db.search_scenarios(
    crime_type='murder',
    setting_environment='mansion'
)

# Load a specific scenario
scenario = db.load_scenario('the_hound_of_the_baskervilles')
print(f"Characters: {len(scenario.characters)}")
```

### Batch Processing

The recommended way to batch-process books is through the experiment runner:

```bash
# Process 20 books from the curated GitHub corpus with the lean variant
python run_experiment.py --source github --limit 20 --variants lean

# Process 10 books from Gutenberg with all variants for comparison
python run_experiment.py --source gutenberg --query "agatha christie" --limit 10
```

Or programmatically:

```python
from mystery_data_acquisition import MysteryProcessor, MysteryDatabase

processor = MysteryProcessor()
db = MysteryDatabase()

# Process books from the cached corpus
import json
with open("mystery_corpus/corpus_index.json") as f:
    index = json.load(f)

for book in index["books"]:
    with open(f"mystery_corpus/{book['text_file']}") as f:
        text = f.read()
    scenario = processor.process_mystery(text, book)
    db.save_scenario(scenario)
```

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
DATABASE_PATH=./mystery_database    # Storage location
LOG_LEVEL=INFO                      # Logging verbosity
```

### API Costs (Estimate)

Processing 1 mystery book (50,000 words):
- Input tokens: ~15,000 tokens
- Output tokens: ~3,000 tokens
- Cost per book: ~$0.25 with Claude Sonnet

Generating 1 new mystery:
- Input tokens: ~5,000 tokens  
- Output tokens: ~4,000 tokens
- Cost per generation: ~$0.15 with Claude Sonnet

**Budget for 100 processed mysteries + 50 generated:** ~$33

## Performance Considerations

### Current Implementation (POC)

- **Storage:** JSON files (easy to inspect, no setup)
- **Search:** Linear scan of index (O(n))
- **Suitable for:** < 1,000 mysteries

### Production Recommendations

When scaling beyond POC:

1. **Database:** Migrate to PostgreSQL + pgvector
   - Relational queries for exact matches
   - Vector search for semantic similarity
   - Example: "Find mysteries similar to prompt X"

2. **Caching:** Add Redis for frequently accessed scenarios
   - Cache generated mysteries
   - Cache pattern extractions

3. **Processing:** Batch processing with async/parallel
   - Use asyncio for API calls
   - Process multiple books simultaneously
   - Estimated: 5x speedup

4. **Embeddings:** Generate vector embeddings for search
   - Use sentence-transformers or OpenAI embeddings
   - Enable semantic search: "mysterious butler characters"

## Legal Considerations

### Current Sources (Safe)

- Project Gutenberg - Public domain (pre-1928)
- GitHub corpus (Blutomania/mystery-crime-books) - Public domain books
- Court transcripts - Public records
- Creative Commons content - Licensed

### To Avoid

- Copyrighted novels without permission
- Recent screenplays (most are copyrighted)
- Podcast transcripts (usually copyrighted)

### Fair Use vs. Training Data

- **Extracting patterns** (motives, structures): Generally acceptable
- **Storing full text**: Requires proper licensing
- **AI training**: Consult legal counsel for commercial use

**Recommendation:** For commercial launch, consult IP attorney

## Roadmap

### Phase 1: POC (Current)
- ✅ Basic data acquisition from Gutenberg
- ✅ Curated GitHub corpus (359 mystery/crime books)
- ✅ AI-powered extraction with Claude (4 extraction variants)
- ✅ Experiment runner for side-by-side variant comparison
- ✅ JSON storage and search
- ✅ Mystery generation from prompts

### Phase 2: Quality & Scale
- [ ] Process 100+ quality mysteries
- [ ] Manual validation of extractions
- [ ] Improved pattern extraction
- [ ] Better search/retrieval

### Phase 3: Production Ready
- [ ] PostgreSQL + pgvector migration
- [ ] Vector embeddings for semantic search
- [ ] API endpoint for game integration
- [ ] Automated quality scoring

### Phase 4: Advanced Features
- [ ] Multi-language support
- [ ] Custom mystery templates
- [ ] Community mystery submissions
- [ ] Difficulty tuning

## Integration with Game

### Game Flow Integration

```python
# In your game server

from mystery_generator import MysteryGenerator

generator = MysteryGenerator()

@app.route('/api/create-game', methods=['POST'])
def create_game():
    # User submits prompt
    data = request.json
    prompt = data['prompt']  # "A murder on Mars"
    num_players = data['num_players']
    
    # Generate mystery
    mystery = generator.generate_mystery(prompt, num_players)
    
    # Store in game session
    game_session = GameSession(
        mystery=mystery,
        players=[...],
        current_phase='investigation'
    )
    
    return {
        'game_id': game_session.id,
        'mystery_title': mystery['title'],
        'characters': mystery['characters'],
        # Don't send solution to players yet!
    }
```

### Information Sharing Mechanism

The 75% sharing rule requires tracking what each player knows:

```python
class PlayerKnowledge:
    def __init__(self, player_id, mystery):
        self.player_id = player_id
        self.known_evidence = []
        self.interrogation_transcripts = []
    
    def add_evidence(self, evidence_id):
        self.known_evidence.append(evidence_id)
    
    def get_shareable_items(self):
        """Player must select 75% of their knowledge to share"""
        all_items = self.known_evidence + self.interrogation_transcripts
        num_to_share = int(len(all_items) * 0.75)
        return {
            'all_items': all_items,
            'must_share': num_to_share
        }
```

## Troubleshooting

### Common Issues

**"No database found" error**
- Solution: Run `mystery_data_acquisition.py` first

**"API key not found"**
- Solution: `export ANTHROPIC_API_KEY=your-key-here`

**"Failed to parse JSON from Claude"**
- Cause: Claude sometimes adds markdown formatting
- Solution: Code strips ```json``` markers, but edge cases exist
- Fix: Add better error handling and retry logic

**"Download failed" for Gutenberg books**
- Cause: Not all books have plain text format
- Solution: Code tries multiple formats, but some may fail
- Fix: Use `--source github` instead for the curated corpus, or skip problematic books

**"Processing very slow"**
- Cause: API calls are sequential
- Solution: For POC, acceptable. For production, use async
- Optimization: Batch process with asyncio

### Debug Mode

```python
# Add at top of script
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export LOG_LEVEL=DEBUG
python mystery_data_acquisition.py
```

## Contributing

### Adding New Data Sources

1. Add a new `download_*_corpus()` method to `CorpusManager` in `run_experiment.py`
2. Register the source as a `--source` choice in the CLI argument parser
3. Ensure proper rate limiting (respect robots.txt for scraped sources)
4. Document licensing/copyright status

### Improving Extraction

1. Update prompts in `MysteryProcessor` methods
2. Test on sample mysteries
3. Compare output quality
4. Iterate on prompt engineering

## Support

For questions or issues:
1. Check the comprehensive plan: `mystery_database_plan.md`
2. Review code comments (extensive "why" explanations)
3. File issue with example prompt/error

## License

This codebase: MIT License

Mystery content: Varies by source
- Project Gutenberg content: Public domain
- Generated mysteries: Check terms of AI provider

**Important:** Verify licensing before commercial use
