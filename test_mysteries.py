"""
test_mysteries.py
-----------------
Six hand-crafted test mysteries used as structural scaffolding and regression
tests for the part registry and mystery generator pipeline.

These are NOT sourced from the corpus — they are manually authored to cover
diverse settings and to test P1/P2 extraction quality.  Because they were
written as metadata (not full prose), the P2 narrative fields (resolution,
investigator, culprit_and_motive, reveal_mechanic) are intentionally sparse;
that is expected behaviour.  See SESSION_STATE.md §Extraction Table for the
full comparison against corpus extractions.

Usage
-----
    from test_mysteries import TEST_MYSTERIES, get_mystery_by_title

Schema per mystery
------------------
    title           : str
    setting_tags    : list[str]   — used for part-registry compatibility matching
    crime           : str
    victim          : str
    closed_world    : str         — why suspects cannot easily leave
    culprit         : str | None  — None if not defined in test metadata
    motive          : str | None
    investigator    : str | None
    alibi           : str         — the key false or misleading alibi
    red_herring     : str | None
    resolution      : str | None
    reveal_mechanic : str | None  — how the truth comes out
    source          : str         — always "hand_written" for these entries
"""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Mystery:
    title: str
    setting_tags: list
    crime: str
    victim: str
    closed_world: str
    alibi: str
    culprit: Optional[str] = None
    motive: Optional[str] = None
    investigator: Optional[str] = None
    red_herring: Optional[str] = None
    resolution: Optional[str] = None
    reveal_mechanic: Optional[str] = None
    source: str = "hand_written"


# ---------------------------------------------------------------------------
# The Six Test Mysteries
# ---------------------------------------------------------------------------

MURDER_ON_MARS = Mystery(
    title="Murder on Mars",
    setting_tags=["sci-fi", "closed_habitat", "space", "future"],
    crime="Murder of a senior geologist inside the pressurised research dome",
    victim="Dr. Yara Osei, chief geologist, Ares Base Alpha",
    closed_world=(
        "An airlock failure has locked down the base — no one can leave or "
        "arrive until the next supply shuttle in 72 hours"
    ),
    alibi=(
        "Lead engineer claims he was running a solo EVA suit diagnostic in "
        "the equipment bay, which has no surveillance feed"
    ),
    culprit="Lead engineer Marcus Holt",
    motive="Osei had discovered Holt falsified core-sample data to hide a "
           "fatal structural flaw in the dome, which would have ended his career",
    investigator=None,
    red_herring=(
        "Botanist left a heated argument with the victim on record — over "
        "resource allocation, not the core data"
    ),
    resolution=None,
    reveal_mechanic=None,
)

ART_THEFT_IN_AMAZONIA = Mystery(
    title="Art Theft in Amazonia",
    setting_tags=["jungle", "remote", "contemporary", "heist"],
    crime=(
        "Theft of three pre-Columbian gold artefacts from a field research "
        "camp's locked storage tent overnight"
    ),
    victim="The artefacts belong to the Kayapó community and are on loan to "
           "the academic expedition",
    closed_world=(
        "The camp is a two-day river journey from the nearest town; no one "
        "left overnight — river watch confirmed"
    ),
    alibi=(
        "Camp director says all six researchers were at the communal fire "
        "until midnight; storage tent was locked at 23:00"
    ),
    culprit=None,
    motive=None,
    investigator=None,
    red_herring=(
        "A local guide was seen near the storage tent at 22:45 — he was "
        "returning a borrowed torch"
    ),
    resolution=None,
    reveal_mechanic=None,
)

ALCHEMICAL_FORGERY_ABBASID = Mystery(
    title="The Alchemical Forgery of the Abbasid Court",
    setting_tags=["historical", "medieval", "middle_east", "court", "8th_century"],
    crime=(
        "Poisoning of the royal alchemist and substitution of the Caliph's "
        "medicinal gold tincture with a lethal mercury compound"
    ),
    victim="Master Alchemist Ibn Zafar al-Rashidi",
    closed_world=(
        "The House of Wisdom is sealed by Caliph's decree after the death — "
        "no scholar or servant may leave Baghdad until the murderer is found"
    ),
    alibi=(
        "The court physician swears he tested the tincture himself at dawn "
        "and found it pure — but he had no independent witness"
    ),
    culprit=None,
    motive=None,
    investigator=None,
    red_herring=(
        "A rival Greek translator had publicly accused Ibn Zafar of plagiarism "
        "the week before"
    ),
    resolution=None,
    reveal_mechanic=None,
)

GHOST_SIGNAL_VICTORIAN_DEEP = Mystery(
    title="The Ghost-Signal of the Victorian Deep",
    setting_tags=["historical", "victorian", "maritime", "submarine", "19th_century"],
    crime=(
        "Sabotage of the telegraph cable-laying vessel's depth-gauge, causing "
        "the death of a deep-sea diver who trusted the false reading"
    ),
    victim="Diver Thomas Crewe, the most experienced hand aboard",
    closed_world=(
        "The vessel is eight days from port in mid-Atlantic; no other ship "
        "within signalling range"
    ),
    alibi=(
        "First mate was on the bridge with the captain during the dive — "
        "confirmed by the captain's log, which the first mate himself keeps"
    ),
    culprit=None,
    motive=None,
    investigator=None,
    red_herring=(
        "Crewe had been writing letters to a London solicitor — suggesting a "
        "will dispute — but the letters were unrelated to the cable contract"
    ),
    resolution=None,
    reveal_mechanic=None,
)

STEAMPUNK_SABOTAGE = Mystery(
    title="A Steampunk Sabotage",
    setting_tags=["steampunk", "alternate_history", "industrial", "city", "19th_century"],
    crime=(
        "Destruction of the Grand Aether Engine at the World's Cogwork "
        "Exposition — three workers killed in the resulting steam explosion"
    ),
    victim="Three unnamed factory workers; primary investigative focus on the "
           "destruction of the engine itself",
    closed_world=(
        "The Exposition grounds are walled and gated; all attendees were "
        "registered and badge-checked; no unaccounted exits before the blast"
    ),
    alibi=(
        "The rival inventor was demonstrating his own automaton on the far "
        "side of the hall to a crowd of 200 at the time of detonation"
    ),
    culprit=None,
    motive=None,
    investigator=None,
    red_herring=(
        "A union agitator had made public threats against the Exposition the "
        "day before — but was actually locked up overnight by police"
    ),
    resolution=None,
    reveal_mechanic=None,
)

GENETIC_IDENTITY_HEIST_NEW_TOKYO = Mystery(
    title="The Genetic Identity Heist of New Tokyo",
    setting_tags=["sci-fi", "cyberpunk", "future", "city", "biotech"],
    crime=(
        "Theft of a person's genetic identity from the CivID Vault — used to "
        "frame them for a corporate assassination they did not commit"
    ),
    victim="Kenji Mori, mid-level biotech auditor",
    closed_world=(
        "The CivID Vault operates on a closed intranet; the breach window was "
        "11 minutes during a scheduled maintenance blackout — only eight "
        "authorised users were active"
    ),
    alibi=(
        "The systems architect logged out of the Vault network four minutes "
        "before the breach — but her biometric token was still pinging inside "
        "the building"
    ),
    culprit=None,
    motive=None,
    investigator=None,
    red_herring=(
        "Mori had recently filed an internal report on a colleague's data "
        "irregularities — the colleague had motive but no vault access"
    ),
    resolution=None,
    reveal_mechanic=None,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TEST_MYSTERIES: list = [
    MURDER_ON_MARS,
    ART_THEFT_IN_AMAZONIA,
    ALCHEMICAL_FORGERY_ABBASID,
    GHOST_SIGNAL_VICTORIAN_DEEP,
    STEAMPUNK_SABOTAGE,
    GENETIC_IDENTITY_HEIST_NEW_TOKYO,
]

_BY_TITLE = {m.title: m for m in TEST_MYSTERIES}


def get_mystery_by_title(title: str) -> Mystery:
    """Return a test mystery by exact title, or raise KeyError."""
    return _BY_TITLE[title]


def as_part_registry_rows() -> list:
    """
    Flatten the test mysteries into the same row format used by the full
    part registry so they can be injected during development / testing
    when the corpus hasn't been extracted yet.

    Each row is a dict with keys: type, content, setting_tags, source_id.
    """
    rows = []
    part_fields = [
        ("crime",           "crime_type"),
        ("victim",          "victim"),
        ("closed_world",    "closed_world"),
        ("alibi",           "alibi"),
        ("culprit",         "culprit"),
        ("motive",          "motive"),
        ("investigator",    "investigator"),
        ("red_herring",     "red_herring"),
        ("resolution",      "resolution"),
        ("reveal_mechanic", "reveal_mechanic"),
    ]
    for mystery in TEST_MYSTERIES:
        for attr, part_type in part_fields:
            content = getattr(mystery, attr)
            if content is None:
                continue
            rows.append({
                "type":         part_type,
                "content":      content,
                "setting_tags": mystery.setting_tags,
                "source_id":    f"test::{mystery.title}",
            })
    return rows


if __name__ == "__main__":
    rows = as_part_registry_rows()
    print(f"Test mysteries: {len(TEST_MYSTERIES)}")
    print(f"Part registry rows from test data: {len(rows)}")
    for row in rows:
        print(f"  [{row['type']:18s}] {row['content'][:60]}...")
