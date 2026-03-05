# Getting Started — Choose Your Mystery

## What Exists Right Now

### Core Files

| File | What it does |
|------|-------------|
| `mystery_data_acquisition.py` | Scrapes Gutenberg + extracts structured data with Claude |
| `mystery_generator.py` | Takes a prompt → generates complete mystery JSON |
| `gameplay_validator.py` | Automatically checks if a mystery is solvable, fair, and balanced |
| `demo_acquisition.py` | Full demo — no API key needed |

### Schema Documentation

| File | What it covers |
|------|---------------|
| `MYSTERY_EXTRACTION_REQUIREMENTS.md` | Every field, why it exists, validation rules |
| `CLAUDE.md` | Session continuity guide for AI-assisted development |

### Test Set

`test_queries/` — Six structured query definitions:
1. Murder on Mars
2. Art Theft in Amazonia
3. The Alchemical Forgery of the Abbasid Court
4. The Ghost-Signal of the Victorian Deep
5. A Steampunk Sabotage
6. The Genetic Identity Heist of New Tokyo

---

## Step 1: Run the Demo (No API Key Needed)

```bash
python demo_acquisition.py
```

This creates a fully structured Victorian locked-room mystery in `./mystery_database/`.
Examine the output to understand the complete schema before writing code against it.

Key things to notice in the output:
- `physical_clues` vs `testimonial_revelations` — two separate arrays
- Every character has `is_culprit`, `interrogation_behavior`, `what_they_hide`
- Red herrings have `false_conclusion`, `why_misleading`, `what_disproves_it`
- `solution_steps` are ordered and reference real clue IDs

---

## Step 2: Validate the Demo Mystery

```bash
python gameplay_validator.py
```

This runs all checks against the demo mystery. Expected output:
```
SOLVABILITY:         PASS
RED HERRING FAIRNESS: PASS
SETTING COHERENCE:   PASS
INTERROGATION:       PASS
DIFFICULTY:          EASY
RECOMMENDATION:      PASS — Mystery is ready for gameplay.
```

---

## Step 3: Generate from a Test Query (Requires API Key)

First, run the acquisition pipeline to seed the database:

```bash
export ANTHROPIC_API_KEY=your-key
python mystery_data_acquisition.py
```

Then generate a mystery from a test query:

```bash
python mystery_generator.py
# Generates TEST_QUERIES[0]: "Murder on Mars" by default
```

To generate a different query, edit the last line of `mystery_generator.py`:
```python
demo_generate(prompt=TEST_QUERIES[2])  # Alchemical Forgery
```

Then validate the generated output:
```python
from gameplay_validator import MysteryGameplayValidator
v = MysteryGameplayValidator("./mystery_database/generated/your_mystery.json")
print(v.generate_full_report(num_players=4))
```

---

## Step 4: Understand the Schema

Read `MYSTERY_EXTRACTION_REQUIREMENTS.md` before modifying any schema fields.

The most important concepts:

### Evidence is split by how it's found
- `PhysicalClue`: players find these by examining locations
- `TestimonialRevelation`: players extract these by interrogating NPCs
- Both are shareable units under the 75/25 rule

### Tech level constrains evidence
```
pre_industrial → no digital or biological
industrial     → no digital or biological
contemporary   → no biological
sci_fi         → all 7 categories
```

### One culprit, always
```python
culprits = [c for c in characters if c.is_culprit]
assert len(culprits) == 1
```

### Red herrings must be disprovable
Every red herring must have `what_disproves_it` = a clue_id that proves the herring wrong.

---

## Next Actions (Prioritized)

### This Session
1. Run `python demo_acquisition.py`
2. Run `python gameplay_validator.py`
3. Read `MYSTERY_EXTRACTION_REQUIREMENTS.md`
4. Try generating `TEST_QUERIES[0]` with the real pipeline

### Next Session
1. Generate all six test queries
2. Validate each generated output
3. Review for quality: do the mysteries make logical sense?
4. Identify which test queries reveal schema gaps

### Month 1
1. Process 20-50 Gutenberg mysteries to build the RAG database
2. Tune generation prompts based on test query outputs
3. Manual playtest 3-5 generated mysteries
4. Integrate with game backend (see `mystery_database_plan.md`)

---

## Cost Estimate

| Activity | Cost |
|----------|------|
| Run demo | Free |
| Process 5 Gutenberg mysteries | ~$1.25 |
| Generate 6 test mysteries | ~$0.90 |
| Build 50-mystery database | ~$12.50 |
| **Total to first playtest** | **~$15** |

---

## If Something Breaks

**JSON parse error from Claude:**
The pipeline uses regex to strip markdown code fences before parsing. If Claude
returns malformed JSON, check the raw response with `print(message.content[0].text)`.

**Validator FAIL — red herring fairness:**
Make sure every red herring has `what_disproves_it` pointing to a real clue/testimony ID.

**Validator FAIL — setting coherence:**
Check that `PhysicalClue.category` values match what's allowed for the mystery's `world_tech_level`.

**Generator missing `is_culprit`:**
The generation prompt explicitly requires exactly one `is_culprit=true` character.
If Claude omits it, the generator raises `ValueError` before saving.

**"No database found":**
Run `demo_acquisition.py` (creates sample) or `mystery_data_acquisition.py` (real pipeline).
