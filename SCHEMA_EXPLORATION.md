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

| Axis | Values |
|---|---|
| `era` | prehistoric, ancient, medieval, renaissance, industrial, victorian, edwardian, modern, near_future, far_future, alternate_history |
| `genre_modifier` | realistic, steampunk, cyberpunk, gothic, noir, space_opera, fantasy_adjacent, solarpunk |
| `biome` | ocean, jungle, arctic, desert, space, underground, urban, court, rural, submarine |
| `crime_category` | murder, theft, forgery, sabotage, heist, disappearance, blackmail, identity_crime, signal_anomaly |
| `macguffin` | artifact, data, identity, formula, land_or_resource, person, signal, currency |
| `motive` | greed, revenge, power, survival, ideology, love, jealousy, self_preservation |
| `twist_type` | false_culprit, hidden_victim, impossible_crime, double_cross, unreliable_narrator, no_crime_at_all |
| `crime_structure` | locked_room, open_field, institutional, theft_trail, identity_swap, impossible_crime, vanishing_act |

---

## Next Steps

1. Update `MysteryScenario` dataclass in `mystery_data_acquisition.py` to use Schema B structure
2. Write an extraction prompt that pulls these axes from raw book text
3. Run extraction against the 359 books in `https://github.com/Blutomania/mystery-crime-books`
4. Validate: check that era, crime_category, and macguffin can be extracted reliably (target: >85% accuracy)
5. Build the combinatorial engine that assembles `A(WORLD) + B(CRIME) + C(CAST) + D(PLOT)` into a coherent mystery
