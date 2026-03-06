"""
Test Mysteries - Canonical Source Set
======================================

Six reference mysteries used as the test corpus for the mystery versioning
and generation system. Each is identified by a letter (A-F) matching the
A(1), A(2)...A(X) part notation used throughout the system.

These are the "ur-texts" - the source material whose parts get mixed and
recombined when generating new mysteries for different settings.

Usage:
    from test_mysteries import TEST_MYSTERIES, get_mystery, get_all_ids

    mystery_a = get_mystery("A")
    all_titles = [m["title"] for m in TEST_MYSTERIES.values()]
"""

# ============================================================================
# THE SIX TEST MYSTERIES
# ============================================================================
#
# Each entry defines the source mystery's identity and structural metadata.
# Parts (A(1), A(2)...A(X)) are extracted from these by the parts extractor.
#
# part_types defines the decomposition axes used when breaking this mystery
# into reusable components.
# ============================================================================

TEST_MYSTERIES = {
    "A": {
        "id": "A",
        "title": "Murder on Mars",
        "crime_type": "murder",
        "setting_location": "Mars",
        "setting_time_period": "near_future",
        "setting_environment": "space_colony",
        "genre_tags": ["sci-fi", "closed_circle", "colony_thriller"],
        "description": (
            "A murder occurs inside a sealed Martian colony dome. "
            "The victim is a senior terraforming engineer. With no way off-planet "
            "for 72 hours, every resident is both suspect and potential next victim. "
            "The killer exploited the life-support systems to manufacture an alibi."
        ),
        "part_types": [
            "crime_type",       # A(1): sealed-environment homicide
            "setting_element",  # A(2): isolated colony, no escape
            "motive",           # A(3): suppressed discovery / whistleblower silenced
            "suspect_archetype",# A(4): corporate saboteur disguised as colleague
            "red_herring",      # A(5): life-support malfunction staged as accident
            "reveal_mechanic",  # A(6): technical expertise used against victim
            "social_dynamic",   # A(7): group paranoia under extreme confinement
            "evidence_type",    # A(8): environmental data log as alibi-breaker
        ],
    },

    "B": {
        "id": "B",
        "title": "Art Theft in Amazonia",
        "crime_type": "theft",
        "setting_location": "Amazon rainforest / remote research station",
        "setting_time_period": "contemporary",
        "setting_environment": "jungle_outpost",
        "genre_tags": ["heist", "wilderness", "artifact_recovery"],
        "description": (
            "A priceless Pre-Columbian artifact vanishes from a remote anthropological "
            "research station deep in the Amazon. The theft happened during a tropical "
            "storm that cut off communications. The artifact may have never left the "
            "jungle — or the station."
        ),
        "part_types": [
            "crime_type",       # B(1): high-value object theft
            "setting_element",  # B(2): geographic isolation, weather as cover
            "motive",           # B(3): black market / ideological repatriation
            "suspect_archetype",# B(4): inside job by trusted researcher
            "red_herring",      # B(5): evidence planted to implicate local guide
            "reveal_mechanic",  # B(6): artifact hidden in plain sight
            "social_dynamic",   # B(7): clash between academic and commercial interests
            "evidence_type",    # B(8): photographic record with timestamp discrepancy
        ],
    },

    "C": {
        "id": "C",
        "title": "The Alchemical Forgery of the Abbasid Court",
        "crime_type": "forgery",
        "setting_location": "Baghdad, Abbasid Caliphate",
        "setting_time_period": "medieval_islamic_golden_age",
        "setting_environment": "royal_court",
        "genre_tags": ["historical", "political_intrigue", "intellectual_mystery"],
        "description": (
            "A sacred alchemical manuscript presented to the Caliph is exposed as "
            "a forgery — but the original has disappeared. The forger had access to "
            "the royal library and deep knowledge of medieval Arabic script. "
            "The crime implicates scholars, viziers, and rival court factions."
        ),
        "part_types": [
            "crime_type",       # C(1): document forgery / intellectual property theft
            "setting_element",  # C(2): court politics, layered hierarchy of access
            "motive",           # C(3): political destabilization / discrediting a rival
            "suspect_archetype",# C(4): brilliant scholar with secret allegiance
            "red_herring",      # C(5): blame cast on foreign envoy
            "reveal_mechanic",  # C(6): anachronistic detail in the forged text
            "social_dynamic",   # C(7): patronage network, who owes whom
            "evidence_type",    # C(8): ink composition / material analysis
        ],
    },

    "D": {
        "id": "D",
        "title": "The Ghost-Signal of the Victorian Deep",
        "crime_type": "disappearance",
        "setting_location": "North Atlantic Ocean",
        "setting_time_period": "victorian",
        "setting_environment": "deep_sea_vessel",
        "genre_tags": ["gothic", "nautical", "supernatural_adjacent"],
        "description": (
            "The sole telegraph operator aboard a Victorian deep-sea cable-laying ship "
            "vanishes mid-voyage, leaving behind a cryptic final transmission. "
            "The crew is convinced the sea took him. The telegraph log tells a "
            "different story — one of blackmail, buried secrets, and a staged death."
        ),
        "part_types": [
            "crime_type",       # D(1): staged disappearance / faked death
            "setting_element",  # D(2): maritime isolation, Victorian technology
            "motive",           # D(3): blackmail silenced before reaching port
            "suspect_archetype",# D(4): officer with a secret past
            "red_herring",      # D(5): supernatural folklore manipulated as cover
            "reveal_mechanic",  # D(6): message hidden in the final transmission
            "social_dynamic",   # D(7): rigid naval hierarchy concealing complicity
            "evidence_type",    # D(8): Morse code log with deliberate errors
        ],
    },

    "E": {
        "id": "E",
        "title": "A Steampunk Sabotage",
        "crime_type": "sabotage",
        "setting_location": "A grand industrial exposition, alternate-history Europe",
        "setting_time_period": "steampunk_alternate_victorian",
        "setting_environment": "exposition_hall",
        "genre_tags": ["steampunk", "industrial_espionage", "alternate_history"],
        "description": (
            "On the opening night of the Great Aetheric Exposition, the centerpiece "
            "invention — a revolutionary aether engine — is destroyed in a dramatic "
            "explosion. The inventor survives but is blamed. Someone with engineering "
            "knowledge sabotaged the device to steal the patent and eliminate the "
            "competition before the demonstration could be witnessed by investors."
        ),
        "part_types": [
            "crime_type",       # E(1): sabotage / industrial espionage
            "setting_element",  # E(2): public spectacle, high-stakes demonstration
            "motive",           # E(3): patent theft, competitor elimination
            "suspect_archetype",# E(4): rival inventor posing as admirer
            "red_herring",      # E(5): anarchist pamphlets found at scene
            "reveal_mechanic",  # E(6): sabotage required pre-event access with a key
            "social_dynamic",   # E(7): investor pressure, financial desperation
            "evidence_type",    # E(8): engineering diagram with unauthorized annotations
        ],
    },

    "F": {
        "id": "F",
        "title": "The Genetic Identity Heist of New Tokyo",
        "crime_type": "identity_theft",
        "setting_location": "New Tokyo megacity",
        "setting_time_period": "far_future",
        "setting_environment": "cyberpunk_megacity",
        "genre_tags": ["cyberpunk", "bio-crime", "corporate_thriller"],
        "description": (
            "In a city where genetic identity is the only currency that matters, "
            "a biotech executive's genetic signature has been stolen and used to "
            "authorize a series of illegal transactions. The executive is dead — "
            "killed in a way that looks natural — and their DNA clone is already "
            "living their life. Unraveling the heist means understanding who "
            "benefits from an identity that no longer belongs to a living person."
        ),
        "part_types": [
            "crime_type",       # F(1): biometric identity theft / genetic fraud
            "setting_element",  # F(2): surveillance state, corporate megacity
            "motive",           # F(3): inheritance and corporate power seizure
            "suspect_archetype",# F(4): trusted biotech aide with deep access
            "red_herring",      # F(5): rival corporation framed via planted data
            "reveal_mechanic",  # F(6): genetic anomaly in the clone's signature
            "social_dynamic",   # F(7): loyalty networks within corporate hierarchy
            "evidence_type",    # F(8): biometric transaction log with microsecond gaps
        ],
    },
}


# ============================================================================
# CONVENIENCE ACCESSORS
# ============================================================================

def get_mystery(mystery_id: str) -> dict:
    """
    Retrieve a test mystery by its letter ID.

    Args:
        mystery_id: One of "A" through "F"

    Returns:
        Mystery dict with all metadata

    Raises:
        KeyError if the ID is not found
    """
    key = mystery_id.upper()
    if key not in TEST_MYSTERIES:
        valid = list(TEST_MYSTERIES.keys())
        raise KeyError(f"Mystery ID '{mystery_id}' not found. Valid IDs: {valid}")
    return TEST_MYSTERIES[key]


def get_all_ids() -> list:
    """Return all test mystery IDs in order."""
    return list(TEST_MYSTERIES.keys())


def get_part_label(mystery_id: str, part_index: int) -> str:
    """
    Return the canonical notation for a mystery part, e.g. 'C(4)'.

    Args:
        mystery_id: Letter ID of the source mystery (e.g. "C")
        part_index: 1-based index of the part

    Returns:
        String like "C(4)"
    """
    mystery = get_mystery(mystery_id)
    part_types = mystery["part_types"]
    if not (1 <= part_index <= len(part_types)):
        raise IndexError(
            f"Mystery {mystery_id} has {len(part_types)} parts (1-indexed). "
            f"Got index {part_index}."
        )
    return f"{mystery_id.upper()}({part_index})"


def list_mysteries() -> None:
    """Print a summary of all six test mysteries."""
    print("\n=== Test Mystery Corpus ===\n")
    for mid, m in TEST_MYSTERIES.items():
        print(f"  [{mid}] {m['title']}")
        print(f"       Crime : {m['crime_type']}")
        print(f"       Era   : {m['setting_time_period']}")
        print(f"       Setting: {m['setting_environment']}")
        print(f"       Parts : {len(m['part_types'])}")
        print()


if __name__ == "__main__":
    list_mysteries()
