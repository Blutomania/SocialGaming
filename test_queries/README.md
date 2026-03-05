# Test Queries — Choose Your Mystery

These six scenarios are the canonical test set for the generator and schema.

Any schema change to `mystery_data_acquisition.py` or `mystery_generator.py`
must be validated against all six before being considered stable.

They were chosen to cover the full range of settings the game needs to support:
- All four tech levels (pre_industrial, industrial, sci_fi, contemporary)
- Western and non-Western historical settings
- Modern, far-future, and alternate-history worlds
- Six different crime types
- Five different mystery types

---

## The Six Queries

| # | Query | File |
|---|-------|------|
| 1 | Murder on Mars | `01_murder_on_mars.json` |
| 2 | Art Theft in Amazonia | `02_art_theft_amazonia.json` |
| 3 | The Alchemical Forgery of the Abbasid Court | `03_alchemical_forgery_abbasid.json` |
| 4 | The Ghost-Signal of the Victorian Deep | `04_ghost_signal_victorian_deep.json` |
| 5 | A Steampunk Sabotage | `05_steampunk_sabotage.json` |
| 6 | The Genetic Identity Heist of New Tokyo | `06_genetic_identity_heist_new_tokyo.json` |

---

## Schema Coverage by Query

| Query | Era | Tech Level | Crime | Mystery Type | Key Schema Challenges |
|-------|-----|------------|-------|--------------|----------------------|
| Murder on Mars | near_future | sci_fi | murder | locked_room | digital + biological evidence; isolated colony; corporate vs. worker factions |
| Art Theft in Amazonia | modern | contemporary | theft | heist | remote jungle; cultural property stakes; terrain as investigation constraint |
| Alchemical Forgery Abbasid | medieval | pre_industrial | forgery | procedural | Non-Western historical; no modern forensics; court hierarchy limits questioning |
| Ghost-Signal Victorian Deep | victorian | industrial | disappearance | locked_room | Submarine; Victorian class norms; ambiguous crime type |
| Steampunk Sabotage | alternate_history | industrial | sabotage | whodunit | Alternate history; steampunk tech as evidence; guild faction dynamics |
| Genetic Identity Heist | near_future | sci_fi | identity_theft | heist | biological + digital evidence primary; corporate privacy shields; Tokyo corporate culture |

---

## Generating from These Queries

```python
from mystery_generator import MysteryGenerator, TEST_QUERIES

generator = MysteryGenerator()

# Generate any of the six
mystery = generator.generate_mystery(TEST_QUERIES[2], num_players=4)
# TEST_QUERIES[2] = "The Alchemical Forgery of the Abbasid Court"

generator.save_generated_mystery(mystery)
```

Or from the command line (generates TEST_QUERIES[0] by default):
```bash
python mystery_generator.py
```

---

## Validating Generated Output

```python
from gameplay_validator import MysteryGameplayValidator

# After generating and saving a mystery:
validator = MysteryGameplayValidator("./mystery_database/generated/my_mystery.json")
print(validator.generate_full_report(num_players=4))
```

---

## Evidence Category Notes by Tech Level

The `world_tech_level` constrains which `category` values are valid in `physical_clues`.

### pre_industrial (Abbasid Forgery)
Valid: `physical, chemical, documentary, testimonial, environmental`
Key evidence types: manuscript dating, reagent testing, ink analysis, witness testimony

### industrial (Victorian Deep, Steampunk Sabotage)
Valid: `physical, chemical, documentary, testimonial, environmental`
Key evidence types: fiber analysis, basic chemistry, mechanical failure inspection

### sci_fi (Murder on Mars, Genetic Identity Heist)
Valid: all 7 (`physical, biological, digital, chemical, documentary, testimonial, environmental`)
Key evidence types: DNA, telemetry logs, genetic sequences, biometric records

### contemporary (Art Theft in Amazonia)
Valid: `physical, chemical, documentary, testimonial, environmental, digital`
Key evidence types: fingerprints, GPS data, photography, forensic anthropology
