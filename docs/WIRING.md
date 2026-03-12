# Technical Wiring — Choose Your Mystery

How the pieces connect. Written so you don't have to hold it all in your head.

---

## Data flow (end to end)

```
User prompt  ("1920s Harlem jazz club")
     │
     ▼
part_registry.py — sample_for_generation()
     │  Pulls compatible atomized parts from the 1,469-part corpus
     │  Returns: List[MysteryPart], Recipe
     │
     ▼
Claude API  (one call, structured JSON prompt)              ← call 1
     │  Parts act as hard constraints — Claude fleshes out prose
     │  Returns: mystery dict  (see Mystery JSON Schema below)
     │
     ▼
localize_mystery()                                          ← call 2 (always)
     │  Rewrites all character names, occupations, titles, and embedded
     │  text so they fit the setting's time period and culture.
     │  "Dr. Pemberton" in Ancient Athens → "Alexios the Physician"
     │  Minor characters may get playful period puns (e.g. "Vidiomnius")
     │  Preserves plot, culprit, evidence logic — surface text only.
     │
     ▼
coherence_validator.py — check_mystery()                    ← free, no API call
     │  Checks P1 causal chain + witness depth + evidence variety
     │  Returns: CoherenceReport  (passed, blocking_count, warning_count)
     │
     ├─── [opt-in] generate_cinematic_brief()               ← call 3 (opt-in)
     │         One extra Claude call
     │         Returns: cinematic_brief dict  (see Cinematic Brief Schema below)
     │         Stored at mystery_dict["cinematic_brief"]
     │
     ▼
mystery_dict  saved to  mystery_database/generated/<slug>_<timestamp>.json
```

### Call budget per generation

| Step | Calls | Condition |
|---|---|---|
| Mystery generation | 1 | always |
| Localization | 1 | always (quality fix, not opt-in) |
| Cinematic brief | 1 | opt-in only |
| Coherence check | 0 | free |
| **Total** | **2–3** | |

---

## Mystery JSON schema

Every generated mystery is a dict with these top-level keys:

```json
{
  "title": "string",

  "setting": {
    "location": "string",
    "time_period": "string",
    "environment": "string",
    "description": "2–3 sentences — MUST explain why suspects cannot leave"
  },

  "crime": {
    "type": "string",
    "what_happened": "string",
    "when": "string",
    "initial_discovery": "string"
  },

  "characters": [
    {
      "name": "string",
      "role": "victim | suspect | detective | witness",
      "occupation": "string  — explains their presence in the closed world",
      "motive": "string  — specific stake; never blank for suspects",
      "alibi": "string  — specific location, activity, and corroborating detail",
      "secret": "string  — 2-sentence concrete fact anchoring interrogation"
    }
  ],

  "evidence": [
    {
      "id": "E1",
      "name": "string",
      "description": "string  — what it is, where found, what it initially suggests",
      "type": "physical | testimonial | circumstantial | documentary",
      "relevance": "critical | supporting | red_herring"
    }
  ],

  "solution": {
    "culprit": "string",
    "method": "string",
    "motive": "string",
    "key_evidence": ["E1", "E2"],
    "how_to_deduce": "step-by-step logic chain (3+ steps)"
  },

  "gameplay_notes": {
    "difficulty": "EASY | MEDIUM | HARD",
    "estimated_playtime": "string",
    "key_twists": ["string"]
  },

  "_provenance": { ... },     // recipe dict — which corpus parts were used
  "_coherence": {             // written after check_mystery() runs
    "passed": true,
    "blocking": 0,
    "warnings": 2,
    "witness_gaps": []
  },
  "_meta": {
    "num_players": 4,
    "setting_input": "original user prompt"
  },

  "cinematic_brief": { ... }  // only present when opt-in was enabled
}
```

**Validation rules enforced by `coherence_validator.py`:**
- At least 2 physical evidence items
- At least 1 red-herring evidence item of type physical or documentary
- At least 2 critical evidence items
- Each suspect must have a non-blank alibi and motive
- Each suspect's secret must be ≥ 2 sentences
- `solution.key_evidence` must reference ≥ 2 evidence IDs
- `solution.how_to_deduce` must contain ≥ 3 reasoning steps
- `setting.description` must explain the isolation mechanic

---

## Localization pass

**Function:** `localize_mystery(mystery_dict)` in both `app.py` and `cli.py`

**Always runs** — it's a quality fix, not an opt-in. Anachronistic names are immersion-breaking.

**What it changes:**
- Character names → era/culture appropriate (no "Dr. Pemberton" in Ancient Athens)
- Occupations → period equivalents ("CEO" → "Merchant Prince", "Doctor" → "Healer")
- Honorifics and titles → era-correct ("Mr." has no place in Ancient Rome)
- All text fields that contain names: secrets, alibis, motives, evidence descriptions, title
- Minor characters may receive playful period puns (encouraged, not mandatory):
  - A Roman witness named "I Saw Everything" → "Vidiomnius"
  - A gossipy Harlem bystander → "Tells-It-All Thomas"
  - One or two per mystery maximum — witnesses and minor suspects only

**What it does NOT change:**
- Plot, culprit identity, evidence logic, solution
- Internal fields: `_provenance`, `_coherence`, `_meta`, `cinematic_brief`

**Setting-to-name conventions (guidance for the prompt):**

| Setting | Name style | Occupation examples |
|---|---|---|
| Ancient Greece/Rome | Single name or nomen+cognomen | Physician, Senator, Tribune, Merchant |
| Ottoman Empire | Arabic/Turkish given names | Kadi (judge), Bey, Effendi, Merchant |
| Medieval Europe | Given name + epithet | Blacksmith, Steward, Apothecary, Knight |
| Victorian Britain | Title + surname | Inspector, Dr., Rev., Lady |
| 1920s Harlem | Nickname-friendly | Numbers runner, Club owner, Doorman |
| Present day | No constraint | Modern titles fine |
| Sci-fi / future | Invent plausibly | Any era or invented culture |

---

## Cinematic brief schema

Stored at `mystery_dict["cinematic_brief"]`. Purpose: drop-in prompt for AI video
generators (Sora, Runway Gen-3, Pika). Covers the opening 15–30 second sequence only —
no spoilers, pure cinematic hook.

```json
{
  "logline": "One sentence. Visual, urgent, present tense. Under 20 words.",

  "opening_shot": "Establishing shot — lens, light, movement, no dialogue. 2–3 sentences.",

  "crime_reveal_shot": "The discovery moment — camera angle, reaction, sound. 2–3 sentences.",

  "atmosphere_tags": ["neon-soaked", "claustrophobic", "frozen silence"],

  "sound_design": "What the audience hears before any dialogue. One sentence.",

  "cast_visuals": [
    {
      "name": "character name",
      "appearance": "Clothing, posture, distinguishing detail. One sentence.",
      "first_seen_doing": "Their first on-screen action. One sentence."
    }
  ],

  "title_card": "The text overlay that ends the opening sequence."
}
```

### How to use with a video API (future wiring)

```python
brief = mystery_dict["cinematic_brief"]

# Runway Gen-3 example
payload = {
    "prompt": f"{brief['opening_shot']} {brief['atmosphere_tags']}",
    "duration": 10,
}

# Sora example
payload = {
    "prompt": brief["opening_shot"],
    "style": ", ".join(brief["atmosphere_tags"]),
}
```

The schema is intentionally stable — wire once, use with any video provider.

---

## Where the cinematic brief is triggered

### In the UI (`app.py`)

```
user_prompt  text input
cinematic_on = st.checkbox("Generate cinematic brief", value=False)
                                                        ^^^^^^^^^^^
                                                        OFF by default

[Generate Mystery] button
  → generate_mystery()          # 1 Claude call always
  → check_mystery()             # free, always
  → if cinematic_on:
      generate_cinematic_brief() # 1 extra Claude call, opt-in only
```

The brief is shown in a collapsible expander "Cinematic Brief (video prompt)" below the
coherence badge in the left column.

### In the CLI (`cli.py`)

```bash
python cli.py generate --setting "..." --cinematic   # opt-in flag
```

---

## Coherence validator — what it checks

`coherence_validator.check_mystery(mystery_dict)` runs three check families:

| Family | What it checks | Cost |
|---|---|---|
| P1 causal chain | crime → victim → closed_world → culprit → resolution unbroken | free |
| Witness foundation | alibi / motive / secret depth per character | free |
| Scene investigation | physical evidence, red herrings, evidence variety | free |

Returns `CoherenceReport`:
- `passed` — True if zero blocking issues
- `blocking_count` — issues that must be fixed before gameplay
- `warning_count` — issues worth reviewing but non-blocking
- `witness_gaps` — list of characters with shallow interrogation anchors

`check_parts(parts)` is a cheaper pre-generation check (runs on the sampled parts
before the Claude call, catches missing part types early).

---

## Part registry — how parts are sampled

`part_registry.py` holds 1,469 atomized parts extracted from public-domain mystery fiction.

Each part has:
- `part_type` — one of the P1–P4 taxonomy types (crime_type, victim_profile, motive, etc.)
- `source_id` — which source text it came from (e.g. `C` for Christie corpus)
- `part_index` — position within that source
- `content` — the extracted text
- `setting_tags` — semantic tags used for compatibility matching

`sample_for_generation(target_setting=...) → (List[MysteryPart], Recipe)` picks one part
per required type, weighted toward setting-compatible parts.

The `Recipe` object serialises as `"C(4)+F(2)+A(6)+..."` — a reproducible fingerprint of
which parts were used. Stored at `mystery_dict["_provenance"]["recipe"]`.

---

## Extraction protocols (P1–P4)

| Protocol | Taxonomy | What it extracts |
|---|---|---|
| P1 Skeleton | C1–C6 | Crime, victim, closed world, culprit, motive, resolution |
| P2 Architecture | M1–M8 | Narrative structure, pacing, reveal mechanics |
| P3 Craft | F1–F8 | Prose technique, dialogue, atmosphere |
| P4 Texture | F9–F12 | Sensory detail, micro-tensions, period colour |

Run P1 first. Only escalate to P2/P3 if P1 quality is high. P4 is for corpus enrichment,
not for generation gating.

```bash
python cli.py extract --protocol P1      # cheapest, run first
python cli.py extract --protocol P1P2    # full corpus run (~359 books)
```

---

## API authentication

Priority order:
1. `ANTHROPIC_API_KEY` environment variable (local dev, HuggingFace Secrets)
2. Bearer token from `/home/claude/.claude/remote/.session_ingress_token` (CI / hosted runner)

See `extract_test_mysteries.py:_get_token()` for the reference implementation.

---

## Active branches

| Branch | What's on it |
|---|---|
| `claude/setup-api-and-mysteries-LRLQK` | UI, cinematic brief, 13 generated mysteries, session log |
| `claude/mystery-versioning-system-TPblK` | Part registry, CLI, corpus pipeline |

Merge `mystery-versioning-system-TPblK` once quality validation (tasks 2–3) is confirmed.
