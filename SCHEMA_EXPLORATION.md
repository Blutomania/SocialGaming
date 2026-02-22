# Mystery Schema Exploration

## The Problem

The current schema was designed around classic mysteries (Project Gutenberg: mansions, ships, Victorian England). It needs to handle a much wider space. Our test set of 6 queries reveals exactly where it breaks:

| Query | Current Schema Coverage | Gaps |
|---|---|---|
| Murder on Mars | crime_type ✓, environment ✓ | genre axis, cultural_context (Martian colony), MacGuffin |
| Art Theft in Amazonia | crime_type ✓, location ✓ | cultural tension (indigenous/colonial), MacGuffin (art) |
| Alchemical Forgery of the Abbasid Court | crime_type ✓, time_period ✓ | cultural_context (Islamic/Abbasid), special_tech (alchemy), MacGuffin (formula) |
| The Ghost-Signal of the Victorian Deep | time_period ✓ | genre_modifier (gothic), environment (submarine), MacGuffin (signal), ambiguous crime_type |
| A Steampunk Sabotage | crime_type ✓ | world_genre (steampunk), era ambiguity, special_tech (steam machinery) |
| The Genetic Identity Heist of New Tokyo | crime_type ✓, environment ✓ | world_genre (cyberpunk), cultural_context (Japanese-futurist), special_tech (genetic-editing), MacGuffin (genetic identity) |

### Consistent Gaps Across All 6 Queries

1. **`world_genre` is not a structured axis** — steampunk/cyberpunk/gothic/space-opera modify the *entire physics of the world*, not just the tone. Currently just a flat tag.
2. **`macguffin` doesn't exist** — the central contested object/data/thing is always present and load-bearing for motives and evidence. It's lost.
3. **`special_tech` doesn't exist** — every setting has a distinctive technology (alchemy, steam, CRISPR, AI). This determines what evidence is *physically possible*.
4. **`cultural_context` doesn't exist** — Abbasid court and New Tokyo need completely different character archetypes. Setting location ≠ cultural context.
5. **`time_period` is a loose string** — makes it impossible to systematically combine "crime structure from source A" with "setting from source B".

---

## Three Competing Schemas

### Schema A — Patched Flat
*Minimal change. Add missing fields to the existing flat structure.*

```json
{
  "crime_type": "forgery",
  "setting_location": "Baghdad",
  "setting_time_period": "medieval",
  "setting_environment": "royal_court",

  "world_genre": "historical_realistic",
  "cultural_context": "Islamic_Abbasid",
  "special_tech": "alchemy",
  "macguffin": "alchemical_formula",

  "characters": [...],
  "evidence": [...],
  "genre_tags": ["historical", "court_intrigue"],
  "motive_types": ["greed", "power"],
  "solution": {...}
}
```

**Pros:** Backward compatible. Easy to add to existing `MysteryScenario` dataclass.
**Cons:** No hierarchy — hard to know which fields are "load-bearing" vs metadata. `world_genre` and `genre_tags` overlap. Doesn't make the combinatorial logic explicit.

---

### Schema B — Orthogonal Axes (DNA Model)
*Every dimension is an independent, swappable axis. Maximum recombinability.*

The key insight: when you generate `A(1)+B(7)+R(3)`, each source mystery contributes a *specific axis*, not a whole story. Schema B makes those axes explicit and non-overlapping.

```json
{
  "WORLD": {
    "era": "medieval",
    "genre_modifier": "historical_realistic",
    "culture": "Islamic_Abbasid",
    "biome": "urban_court",
    "special_tech": "alchemy"
  },
  "CRIME": {
    "category": "forgery",
    "method": "deception_via_chemistry",
    "scale": "institutional",
    "macguffin": "alchemical_formula"
  },
  "CAST": {
    "culprit_archetype": "insider_scholar",
    "victim_type": "institution",
    "investigator_type": "court_appointed",
    "suspect_archetypes": ["rival_scholar", "court_vizier", "foreign_merchant"]
  },
  "PLOT": {
    "motive": "power",
    "twist_type": "false_culprit",
    "red_herring_count": 3,
    "clue_trail_length": 5
  }
}
```

**Era values (structured, not free string):**
`prehistoric` | `ancient` | `medieval` | `renaissance` | `industrial` | `victorian` | `edwardian` | `modern` | `near_future` | `far_future` | `alternate_history`

**Genre modifier values:**
`realistic` | `steampunk` | `cyberpunk` | `gothic` | `noir` | `space_opera` | `fantasy_adjacent` | `solarpunk`

**Crime category values:**
`murder` | `theft` | `forgery` | `sabotage` | `heist` | `disappearance` | `blackmail` | `identity_crime` | `signal_anomaly`

**Macguffin values:**
`artifact` | `data` | `identity` | `formula` | `land_or_resource` | `person` | `signal` | `currency`

**Pros:** Each axis is independently swappable — combinatorial recipe `A(WORLD) + B(CRIME) + C(CAST) + D(PLOT)` is unambiguous. Makes the versioning system explicit.
**Cons:** More complex to extract from raw text. May lose narrative coherence on wild combinations.

---

### Schema C — Skeleton + Flavor (2-Layer)
*Separate what a mystery IS (logic) from what it LOOKS LIKE (aesthetics).*

```json
{
  "SKELETON": {
    "crime_structure": "institutional_forgery",
    "clue_count": 5,
    "red_herring_count": 2,
    "twist_type": "false_culprit",
    "solution_logic": "deductive",
    "plot_beats": ["crime_discovered", "wrong_suspect_accused", "alibi_breaks", "hidden_motive_revealed", "confrontation"]
  },
  "FLAVOR": {
    "era": "medieval",
    "genre_modifier": "historical_realistic",
    "culture": "Islamic_Abbasid",
    "environment": "royal_court",
    "special_tech": "alchemy",
    "macguffin": "formula",
    "character_archetypes": ["court_scholar", "palace_vizier", "foreign_spy", "royal_patron"]
  }
}
```

**Pros:** Skeleton guarantees narrative coherence — a forged-will mystery *stays coherent* even when you put it in New Tokyo. Flavor can swap freely without breaking plot logic.
**Cons:** Skeleton is harder to extract automatically from raw text. Requires more sophisticated AI parsing.

---

## Test Matrix

How well does each schema handle the 6 queries?

| Query | Schema A (Patched Flat) | Schema B (Orthogonal Axes) | Schema C (Skeleton + Flavor) |
|---|---|---|---|
| **Murder on Mars** | ✓ Adds world_genre + macguffin | ✓ era=far_future, genre=space_opera, culture=Martian_colony | ✓ skeleton=locked_room, flavor swaps cleanly |
| **Art Theft in Amazonia** | ~ macguffin=art, cultural_context rough | ✓ culture=Indigenous+Colonial_tension, macguffin=artifact | ~ skeleton=theft_trail, cultural tension hard to encode in skeleton |
| **Alchemical Forgery of Abbasid Court** | ~ better but culture+tech still loose | ✓ All axes fill cleanly | ✓ skeleton=institutional_forgery, flavor=Islamic_Abbasid+alchemy |
| **Ghost-Signal of the Victorian Deep** | ~ crime_type="signal_anomaly" awkward | ✓ category=signal_anomaly, genre=gothic fills the supernatural gap | ~ plot_beats handle it, but signal_anomaly is an odd skeleton |
| **Steampunk Sabotage** | ~ world_genre+special_tech patch it | ✓ genre=steampunk, category=sabotage, special_tech=steam_machinery | ✓ skeleton=sabotage, flavor=steampunk fills perfectly |
| **Genetic Identity Heist of New Tokyo** | ~ Many fields needed | ✓ All axes fill cleanly, macguffin=identity | ✓ skeleton=identity_swap, flavor=cyberpunk+New_Tokyo+CRISPR |

**Legend:** ✓ = handles cleanly, ~ = handles with friction/workarounds, ✗ = breaks

---

## Recommendation

**Use Schema B (Orthogonal Axes) as the primary component index.**

Rationale:
- All 6 queries fill cleanly with no workarounds
- The versioning recipe `A(WORLD) + B(CRIME) + C(CAST) + D(PLOT)` maps directly to Schema B's 4 top-level axes
- It's the most honest representation of what the combinatorial engine actually does
- Extraction from raw text is feasible: era and genre are reliably detectable; macguffin and cultural_context are reliably extractable with a targeted AI prompt

**Borrow from Schema C:** Add `crime_structure` and `plot_beats` to Schema B's `PLOT` block. This gives coherence guarantees without the full 2-layer complexity.

### Final Recommended Index Schema

```json
{
  "WORLD": {
    "era": "< era enum >",
    "genre_modifier": "< genre_modifier enum >",
    "culture": "string (free, but guided)",
    "biome": "< biome enum >",
    "special_tech": "string"
  },
  "CRIME": {
    "category": "< crime_category enum >",
    "method": "string",
    "scale": "personal | institutional | societal",
    "macguffin": "< macguffin enum >"
  },
  "CAST": {
    "culprit_archetype": "string",
    "victim_type": "person | institution | artifact | data | reputation",
    "investigator_type": "string",
    "suspect_archetypes": ["string"]
  },
  "PLOT": {
    "crime_structure": "< structure enum >",
    "motive": "< motive enum >",
    "twist_type": "< twist enum >",
    "red_herring_count": "int",
    "clue_trail_length": "int",
    "plot_beats": ["string"]
  }
}
```

#### Enum Reference

> **Revised values** — see *Enum Rationale* section below for the reasoning behind each change.

| Axis | Values |
|---|---|
| `era` | prehistoric, ancient, medieval, renaissance, industrial, victorian, modern, near_future, far_future |
| `genre_modifier` | steampunk, cyberpunk, biopunk, gothic, space_opera, solarpunk, postapocalyptic, supernatural, weird_west |
| `environment` | urban, rural, wilderness, ocean, arctic, jungle, desert, court_or_palace, estate_or_manor, ship_or_submarine, space_station, underground, laboratory, factory |
| `crime_category` | murder, theft, heist, forgery, fraud, sabotage, blackmail, kidnapping, disappearance, impersonation, mysterious_event |
| `macguffin` | artifact, information, identity, technology, person, land, resource, reputation |
| `motive` | greed, revenge, power, survival, ideology, love, jealousy, loyalty, obsession |
| `twist_type` | false_culprit, victim_is_culprit, hidden_victim, multiple_culprits, double_cross, unreliable_narrator, no_crime_at_all |
| `crime_structure` | locked_room, open_suspect_pool, institutional, conspiracy, theft_trail, identity_swap, impossible_crime, vanishing_act |

**Note:** `tone` is **not** a version-hash axis — it lives in the Session Config layer (see below).

---

#### Enum Rationale

**`era`**
- Removed `alternate_history` — this is a *world-physics modifier*, not a time period. It belongs in `genre_modifier`.
- Removed `edwardian` — a 10-year sliver that blurs into `victorian`. Absorbed.
- `industrial` and `victorian` kept separate: `industrial` = Gilded Age America / Continental Europe; `victorian` = British Empire cultural context. Distinction is load-bearing for cast archetypes.

**`genre_modifier`**
- Removed `realistic` — the absence of a modifier. Represented as `null`.
- Removed `noir` — this is **tone**, not world-physics. A cyberpunk story can be noir. A Victorian story can be noir. Moved to Session Config `tone` axis.
- Removed `fantasy_adjacent` — too vague. Replaced by `supernatural` (magic/ghosts/curses explicitly real) and `weird_west` (frontier + supernatural).
- Added `biopunk` — genetic editing as dominant technology. Distinct from cyberpunk (neural implants + megacorps). Needed for Genetic Identity Heist query.
- Added `postapocalyptic` — civilization collapse changes world-physics fundamentally (no institutions, no forensics infrastructure).

**`environment`** *(renamed from `biome`)*
- Renamed: the old `biome` mixed natural landscapes with built environments and location types inconsistently.
- Added built environments: `court_or_palace`, `estate_or_manor`, `ship_or_submarine`, `space_station`, `laboratory`, `factory`.
- Removed `space` and `submarine` as standalone values — `space_station` and `ship_or_submarine` are more precise.

**`crime_category`**
- Removed `signal_anomaly` — too narrow (derived from one query). Absorbed into `mysterious_event`.
- Renamed `identity_crime` → `impersonation` — more specific and unambiguous.
- Added `fraud` — distinct from `forgery` (forgery = fake object; fraud = fake transaction/scheme).
- Added `kidnapping` — distinct from `disappearance` (kidnapping implies a known demand; disappearance is ambiguous).

**`macguffin`**
- Collapsed `formula`, `signal`, `data` → `information` — all three are information in different containers.
- Split `land_or_resource` → `land` + `resource` — two distinct things with different legal/social weight.
- Absorbed `currency` into `resource`.
- Added `technology` — a machine, blueprint, or capability (distinct from information *about* the technology).
- Added `reputation` — the central object in blackmail mysteries; worth making explicit.

**`motive`**
- Removed `self_preservation` — duplicate of `survival`. One kept.
- Added `loyalty` — acting on behalf of a group, family, nation, or code. Common in institutional and historical mysteries.
- Added `obsession` — pathological fixation on a person, object, or idea. Distinct from love.

**`twist_type`**
- Removed `impossible_crime` — already covered by `crime_structure`. Duplication removed.
- Added `victim_is_culprit` — faked death, self-orchestration. A staple (Agatha Christie device).
- Added `multiple_culprits` — everyone did it (Orient Express pattern). Distinct from double_cross.

**`crime_structure`**
- Renamed `open_field` → `open_suspect_pool` — clarifies what this actually means (many suspects, no access constraint).
- Added `conspiracy` — crime is part of a larger coordinated plot. Distinct in investigation frame from all others.
- `impossible_crime` kept here (removed from `twist_type`). This is the right home: it describes the *structure* of the crime, not the reveal.

---

## Session Architecture: Two-Layer Design

The system separates **what the mystery is** from **how it is experienced**. These are two distinct layers with different mutability and control.

### Layer 1 — Version Hash (locked at game start)

Encodes the mystery's logical content. Deterministic, shareable, reproducible. Defined by all Schema B axes:

```
era + genre_modifier + environment + crime_category + macguffin + motive + twist_type + crime_structure
```

The version string is generated at game creation and **cannot be changed during play**. Changing the version = starting a new game.

### Layer 2 — Session Config (host-controlled, adjustable during play)

Defines how the mystery content is *expressed* — narration style, atmosphere, difficulty. Same mystery, different surface.

| Setting | Default | Options |
|---|---|---|
| `tone` | `neutral` | `neutral \| noir \| cozy \| thriller \| horror \| comedic \| dramatic` |
| `rating` | `teen` | `family \| teen \| mature` |
| `difficulty` | `medium` | `easy \| medium \| hard \| expert` |
| `pacing` | `host_driven` | `host_driven \| timed` |

**Defaults are intentionally middle-ground** — most sessions will never touch these settings. The system is *reactive, not proactive*: no preference prompts at game start, settings change only when someone asks.

### Role-Based Control

| Role | Can do |
|---|---|
| **Host** (game organizer) | Set version at game creation; adjust any Session Config setting mid-game |
| **Player** | Interact with mystery content only — no settings access |

**Rationale:** Prompting all players for preferences interrupts game flow. The host has the mental model of a DM or room owner (familiar from Jackbox, Among Us, tabletop). Players trust them to calibrate the experience.

### How Mid-Game Config Changes Work

- Host issues a quiet command (e.g., `/tone cozy`, `/difficulty easy`)
- Other players are not interrupted
- Changes apply at the **next natural scene transition** (next clue reveal, next scene) — never mid-sentence
- Optionally, the narration can absorb the shift: *"The atmosphere grows lighter..."*

### What Cannot Change Mid-Game

- The mystery version (version hash)
- Who the culprit is, what the crime was, what the twist is
- Any axis from Layer 1

---

## Next Steps

1. Update `MysteryScenario` dataclass in `mystery_data_acquisition.py` to use Schema B structure with revised enums
2. Write an extraction prompt that pulls these axes from raw book text
3. Run extraction against the 359 books in `https://github.com/Blutomania/mystery-crime-books`
4. Validate: check that era, crime_category, and macguffin can be extracted reliably (target: >85% accuracy)
5. Build the combinatorial engine that assembles `A(WORLD) + B(CRIME) + C(CAST) + D(PLOT)` into a coherent mystery
6. Implement Session Config layer with host-only controls and the 4 settings above
