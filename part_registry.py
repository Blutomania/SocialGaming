"""
Part Registry — Atomic Part Decomposition, Setting Compatibility, and Provenance

Each source mystery is atomized into 8 typed parts using the SOURCE(INDEX) notation
from test_mysteries.py:

    A(1) = crime_type from Mystery A
    C(4) = suspect_archetype from Mystery C
    F(6) = reveal_mechanic from Mystery F

A generated mystery's provenance is logged as a recipe, e.g.:
    C(4) + F(2) + A(6) + D(5) + B(3)

This makes every output auditable and non-repeatable.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# PART TYPE DEFINITIONS (8 axes, 1-indexed)
# ============================================================================

PART_TYPE_NAMES = [
    "crime_type",        # index 1 — the crime and its central question
    "setting_element",   # index 2 — the bounded space and its constraints
    "motive",            # index 3 — why the culprit acted
    "suspect_archetype", # index 4 — the type of person who did it
    "red_herring",       # index 5 — deliberate misdirection
    "reveal_mechanic",   # index 6 — how the solution is demonstrated
    "social_dynamic",    # index 7 — power structures and group psychology
    "evidence_type",     # index 8 — the kind of proof that breaks the case
]

# Content of each part from the test corpus (SOURCE → list of 8 descriptions)
# Order matches PART_TYPE_NAMES (1-indexed in notation, 0-indexed here)
PART_CONTENT = {
    "A": [
        "sealed-environment homicide inside a Martian colony dome",
        "isolated colony with no escape for 72 hours — every resident is suspect",
        "suppressed scientific discovery; whistleblower silenced before reaching Earth",
        "corporate saboteur disguised as trusted colleague",
        "life-support malfunction staged to look like an accident",
        "technical expertise turned against victim via manipulated environmental systems",
        "group paranoia under extreme confinement — trust collapses hierarchically",
        "environmental data log used as alibi-breaker; system timestamps contradict testimony",
    ],
    "B": [
        "high-value artifact theft during a communications blackout",
        "geographic isolation in the Amazon; tropical storm cuts off all escape routes",
        "black-market sale or ideological repatriation of stolen cultural heritage",
        "inside job by a trusted researcher who arranged their own access",
        "evidence planted to implicate the local guide — racial and class prejudice exploited",
        "artifact hidden in plain sight, disguised as a mundane object at the station",
        "clash between academic integrity and commercial exploitation of indigenous culture",
        "photographic record with timestamp discrepancy exposes false alibi",
    ],
    "C": [
        "document forgery presented to the highest authority as authentic sacred text",
        "layered court hierarchy with restricted access to the royal library",
        "political destabilization — discrediting a rival faction at the Caliph's court",
        "brilliant scholar with a secret allegiance to a rival power",
        "suspicion cast on a foreign envoy to create a diplomatic incident",
        "anachronistic detail in the forged manuscript — language not yet coined at claimed date",
        "patronage network where loyalty is currency; debts owed determine who can be pressured",
        "ink composition and material analysis of parchment reveals anachronism",
    ],
    "D": [
        "staged disappearance and faked death aboard a Victorian deep-sea vessel",
        "maritime isolation — mid-ocean, Victorian technology, no communication once submerged",
        "blackmail silenced before the ship reached port and the victim could speak",
        "ship's officer with a secret past who had the most to lose from exposure",
        "supernatural folklore of the deep exploited to explain the disappearance as 'the sea'",
        "incriminating message encoded inside the victim's final Morse transmission",
        "rigid naval hierarchy concealing complicity — rank protects the powerful",
        "Morse code log with deliberate errors forming a second message when decoded",
    ],
    "E": [
        "industrial sabotage of a revolutionary invention at its public debut",
        "grand public exposition — high-stakes demonstration before investors and press",
        "patent theft and competitor elimination before the invention could be witnessed",
        "rival inventor posing as an admirer and generous sponsor",
        "anarchist pamphlets found at the scene — political misdirection",
        "sabotage required pre-event access with a specific key only officials possessed",
        "investor pressure and financial desperation distorts everyone's loyalty",
        "engineering diagram with unauthorized annotations in a different hand",
    ],
    "F": [
        "biometric identity theft — a genetic signature stolen and used to authorize transactions",
        "surveillance state megacity where genetic identity is the only currency",
        "inheritance seizure and corporate power grab enabled by the victim's death",
        "trusted biotech aide with deep biometric access and intimate knowledge of the victim",
        "rival corporation framed via planted genetic data in the transaction logs",
        "genetic anomaly in the clone's signature — a microscopic imperfection in the copy",
        "loyalty networks within the corporate hierarchy; who owes their position to whom",
        "biometric transaction log with microsecond gaps indicating post-mortem authorization",
    ],
}

# Setting compatibility rules for each part type
# Parts with "universal" motives/mechanics work in any setting
# Parts with period/environment markers need filtering or adaptation
SETTING_COMPAT = {
    # crime_type (index 1): mostly universal, method-specific parts may need adaptation
    "crime_type": {
        "A": "universal",        # murder is universal
        "B": "universal",        # theft is universal
        "C": "universal",        # forgery is universal
        "D": "universal",        # disappearance/faked death is universal
        "E": "universal",        # sabotage is universal
        "F": ["far_future", "near_future"],  # biometric theft needs tech
    },
    # setting_element (index 2): highly period/environment specific
    "setting_element": {
        "A": ["near_future", "far_future", "space"],
        "B": ["contemporary", "tropical"],
        "C": ["medieval", "historical", "royal_court"],
        "D": ["victorian", "maritime"],
        "E": ["steampunk", "victorian", "exposition"],
        "F": ["far_future", "cyberpunk"],
    },
    # motive (index 3): almost always universal
    "motive": {
        "A": "universal",  # suppressing a discovery
        "B": "universal",  # greed / ideology
        "C": "universal",  # political ambition
        "D": "universal",  # blackmail
        "E": "universal",  # financial desperation
        "F": "universal",  # inheritance / power
    },
    # suspect_archetype (index 4): mostly universal, some tech-specific
    "suspect_archetype": {
        "A": "universal",        # corporate saboteur
        "B": "universal",        # inside job by trusted researcher
        "C": "universal",        # brilliant scholar with hidden allegiance
        "D": "universal",        # officer with secret past
        "E": "universal",        # rival posing as admirer
        "F": ["far_future", "near_future"],  # biotech aide
    },
    # red_herring (index 5): universal by definition
    "red_herring": {s: "universal" for s in "ABCDEF"},
    # reveal_mechanic (index 6): sometimes tech-specific
    "reveal_mechanic": {
        "A": ["near_future", "far_future"],  # data log analysis
        "B": "universal",                     # hidden in plain sight
        "C": "universal",                     # anachronistic detail
        "D": "universal",                     # hidden message in transmission
        "E": "universal",                     # physical key access
        "F": ["far_future", "near_future"],  # genetic anomaly
    },
    # social_dynamic (index 7): universal
    "social_dynamic": {s: "universal" for s in "ABCDEF"},
    # evidence_type (index 8): sometimes tech-specific
    "evidence_type": {
        "A": ["near_future", "far_future"],   # data log
        "B": "universal",                      # photographic record
        "C": "universal",                      # material analysis
        "D": "universal",                      # coded message
        "E": "universal",                      # physical document
        "F": ["far_future", "near_future"],   # biometric log
    },
}

# Period and environment keywords for inferring setting from a free-text description
PERIOD_KEYWORDS = {
    "ancient": ["ancient", "greek", "roman", "egyptian", "athen", "sparta", "pharaoh",
                "amphitheater", "agora", "forum", "toga", "century bc", "bce"],
    "medieval": ["medieval", "castle", "knight", "feudal", "monastery", "plague",
                 "crusade", "guild", "1100", "1200", "1300", "1400"],
    "medieval_islamic_golden_age": ["abbasid", "caliphate", "baghdad", "vizier",
                                    "islamic", "caliph", "golden age"],
    "victorian": ["victorian", "1800s", "19th century", "gaslight", "hansom",
                  "empire", "colonial", "telegram", "jack the ripper"],
    "steampunk": ["steampunk", "aether", "airship", "clockwork", "brass"],
    "contemporary": ["contemporary", "modern", "today", "present day", "21st century",
                     "smartphone", "internet", "cctv"],
    "near_future": ["near future", "2050", "2060", "2070", "2080", "2100",
                    "space colony", "ai", "neural", "mars colony"],
    "far_future": ["far future", "cyberpunk", "megacity", "genetic", "nanobots",
                   "quantum", "clone", "biometric"],
}

ENVIRONMENT_KEYWORDS = {
    "space": ["space", "orbit", "station", "colony", "mars", "lunar", "zero gravity"],
    "maritime": ["ship", "sea", "ocean", "port", "nautical", "vessel", "submarine"],
    "jungle": ["jungle", "rainforest", "amazon", "canopy", "tropical", "river basin"],
    "royal_court": ["court", "palace", "throne", "vizier", "caliph", "sultan", "king",
                    "queen", "chancellor"],
    "exposition": ["exposition", "exhibition", "world fair", "demonstration hall"],
    "cyberpunk": ["megacity", "corporate tower", "neon", "cyberpunk", "implant"],
    "mansion": ["mansion", "manor", "estate", "country house", "drawing room"],
    "agora": ["agora", "marketplace", "public square", "forum", "stoa"],
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class MysteryPart:
    """
    A single typed, labeled part from a source mystery.

    Notation: SOURCE_ID(PART_INDEX), e.g. C(4), A(6), F(2)
    - SOURCE_ID: letter A-F (test corpus) or string (corpus extraction)
    - PART_INDEX: 1-based position in PART_TYPE_NAMES
    """
    source_id: str          # "A", "B", ..., "F", or "corpus_42"
    part_index: int         # 1-8 (matches PART_TYPE_NAMES)
    part_type: str          # e.g. "suspect_archetype"
    content: str            # extracted description of this part
    source_title: str       # human-readable source name

    # Setting compatibility
    setting_tags: List[str] = field(default_factory=list)
    # "universal" = works anywhere; otherwise list of compatible periods/environments

    def label(self) -> str:
        """Return canonical label: SOURCE_ID(PART_INDEX), e.g. C(4)."""
        return f"{self.source_id}({self.part_index})"

    def is_universal(self) -> bool:
        return "universal" in self.setting_tags

    def is_compatible(self, period: str = "", environment: str = "") -> bool:
        """True if this part can work in the given setting."""
        if self.is_universal() or not self.setting_tags:
            return True
        if period and any(period in tag or tag in period for tag in self.setting_tags):
            return True
        if environment and any(environment in tag or tag in environment for tag in self.setting_tags):
            return True
        return False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MysteryPart":
        return cls(**d)


@dataclass
class ProvenanceRecipe:
    """
    Records exactly which part from which source was used for each slot.

    Recipe format: C(4) + F(2) + A(6) + D(5) + B(3)
    Each token is SOURCE_ID(PART_INDEX).
    """
    slots: List[Tuple[str, int, str]]  # [(source_id, part_index, part_type), ...]
    target_setting: str
    generated_title: str = ""

    def format(self) -> str:
        """Format as e.g. 'C(4) + F(2) + A(6)'."""
        return " + ".join(f"{sid}({idx})" for sid, idx, _ in self.slots)

    def to_dict(self) -> dict:
        return {
            "recipe": self.format(),
            "slots": [
                {"source_id": sid, "part_index": idx, "part_type": ptype}
                for sid, idx, ptype in self.slots
            ],
            "target_setting": self.target_setting,
            "generated_title": self.generated_title,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProvenanceRecipe":
        slots = [(s["source_id"], s["part_index"], s["part_type"]) for s in d["slots"]]
        return cls(
            slots=slots,
            target_setting=d.get("target_setting", ""),
            generated_title=d.get("generated_title", ""),
        )


# ============================================================================
# PART REGISTRY
# ============================================================================

class PartRegistry:
    """
    Stores atomized mystery parts and supports diversity-constrained retrieval.

    Core workflow:
        1. populate()           — load test corpus (always available)
        2. load_extractions()   — add corpus extraction JSONs
        3. get_candidates()     — filter by part type + setting compatibility
        4. sample_for_gen()     — diversity-constrained sampling across all slots
        5. build_recipe()       — construct auditable ProvenanceRecipe
    """

    def __init__(self, db_dir: str = "./mystery_database"):
        self.db_dir = Path(db_dir)
        self.parts: List[MysteryPart] = []
        self._registry_path = self.db_dir / "part_registry.json"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self):
        self.db_dir.mkdir(parents=True, exist_ok=True)
        with open(self._registry_path, "w") as f:
            json.dump([p.to_dict() for p in self.parts], f, indent=2)

    def load(self) -> bool:
        if not self._registry_path.exists():
            return False
        with open(self._registry_path) as f:
            self.parts = [MysteryPart.from_dict(d) for d in json.load(f)]
        return bool(self.parts)

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------

    def populate_from_test_corpus(self):
        """Load all 6 × 8 = 48 parts from the canonical test mysteries.

        Uses PART_CONTENT (already embedded in this module) — does not depend
        on the shape of test_mysteries.TEST_MYSTERIES.
        """
        # Titles for the 6 test mysteries, keyed by single-letter ID
        TEST_TITLES = {
            "A": "Murder on Mars",
            "B": "Art Theft in Amazonia",
            "C": "The Alchemical Forgery of the Abbasid Court",
            "D": "The Ghost-Signal of the Victorian Deep",
            "E": "A Steampunk Sabotage",
            "F": "The Genetic Identity Heist of New Tokyo",
        }

        for mystery_id, contents in PART_CONTENT.items():
            title = TEST_TITLES.get(mystery_id, mystery_id)
            for idx_0, part_type in enumerate(PART_TYPE_NAMES):
                part_index = idx_0 + 1  # 1-based
                content = contents[idx_0] if idx_0 < len(contents) else ""
                if not content:
                    continue

                compat = SETTING_COMPAT.get(part_type, {}).get(mystery_id, "universal")
                if compat == "universal":
                    tags = ["universal"]
                elif isinstance(compat, list):
                    tags = compat
                else:
                    tags = ["universal"]

                part = MysteryPart(
                    source_id=mystery_id,
                    part_index=part_index,
                    part_type=part_type,
                    content=content,
                    source_title=title,
                    setting_tags=tags,
                )
                self.parts.append(part)

    def load_extractions(self, limit: int = 10000):
        """Add parts from saved corpus extraction JSONs."""
        extractions_dir = self.db_dir / "extractions"
        if not extractions_dir.exists():
            return 0

        added = 0
        for f in sorted(extractions_dir.glob("*.json"))[:limit]:
            try:
                with open(f) as fp:
                    data = json.load(fp)
                # test_*_p1p2.json files nest fields under "extracted" key
                if "extracted" in data:
                    data = data["extracted"]
                source_id = f"corpus_{f.stem[:8]}"
                title = data.get("_meta", {}).get("title", source_id)
                self._atomize_extraction(data, source_id, title)
                added += 1
            except Exception:
                continue
        return added

    def _atomize_extraction(self, extraction: dict, source_id: str, source_title: str):
        """Convert a corpus extraction dict into MysteryPart entries.

        Handles two formats:
        - Corpus JSONs: top-level keys, each value is {"value": str, "confidence": str, ...}
        - Test JSONs (after unwrapping "extracted"): same structure
        """
        # Map extraction JSON keys to part indices (matches actual extraction output)
        KEY_TO_IDX = {
            "crime":             1,
            "closed_world":      2,
            "culprit_and_motive": 3,
            "suspect_architecture": 4,
            "red_herring":       5,
            "reveal_mechanic":   6,
            "social_world":      7,
            "alibi":             8,
        }
        for key, idx in KEY_TO_IDX.items():
            raw = extraction.get(key)
            if not raw:
                continue
            # Each field is either a plain string or a dict with a "value" key
            if isinstance(raw, dict):
                content = raw.get("value", "")
                confidence = raw.get("confidence", "")
                # Skip low-confidence extractions — not useful as parts
                if confidence == "low":
                    continue
            else:
                content = str(raw)
            if not content or len(content) < 10:
                continue
            part_type = PART_TYPE_NAMES[idx - 1]
            tags = self._infer_tags(content)
            part = MysteryPart(
                source_id=source_id,
                part_index=idx,
                part_type=part_type,
                content=content[:500],
                source_title=source_title,
                setting_tags=tags,
            )
            self.parts.append(part)

    def _infer_tags(self, content: str) -> List[str]:
        """Heuristically infer setting compatibility from content text."""
        content_lower = content.lower()
        tags = []
        for period, keywords in PERIOD_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(period)
        for env, keywords in ENVIRONMENT_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(env)
        return tags if tags else ["universal"]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_candidates(
        self,
        part_type: str,
        period: str = "",
        environment: str = "",
    ) -> List[MysteryPart]:
        """Return all parts of the given type compatible with the target setting."""
        return [
            p for p in self.parts
            if p.part_type == part_type and p.is_compatible(period, environment)
        ]

    # ------------------------------------------------------------------
    # Diversity-Constrained Sampling
    # ------------------------------------------------------------------

    def sample_for_generation(
        self,
        part_types: Optional[List[str]] = None,
        target_setting: str = "",
        max_per_source: int = 2,
        seed: Optional[int] = None,
    ) -> Tuple[List[MysteryPart], ProvenanceRecipe]:
        """
        Sample one part per requested type, enforcing the diversity constraint:
        no single source mystery may contribute more than max_per_source parts.

        Returns: (selected_parts, provenance_recipe)
        """
        if part_types is None:
            part_types = PART_TYPE_NAMES

        rng = random.Random(seed)
        period, environment = _parse_setting(target_setting)
        source_counts: Dict[str, int] = defaultdict(int)
        selected: List[MysteryPart] = []

        # Shuffle slot order so diversity pressure rotates each run
        slots = list(enumerate(part_types))
        rng.shuffle(slots)

        slot_results: Dict[str, MysteryPart] = {}

        for _, part_type in slots:
            candidates = self.get_candidates(part_type, period, environment)
            if not candidates:
                # Fallback: relax setting filter
                candidates = [p for p in self.parts if p.part_type == part_type]
            if not candidates:
                continue

            # Apply diversity constraint
            eligible = [p for p in candidates if source_counts[p.source_id] < max_per_source]
            if not eligible:
                eligible = candidates  # graceful fallback

            rng.shuffle(eligible)
            chosen = eligible[0]
            slot_results[part_type] = chosen
            source_counts[chosen.source_id] += 1

        # Restore original slot order for display consistency
        selected = [slot_results[pt] for pt in part_types if pt in slot_results]

        recipe = ProvenanceRecipe(
            slots=[(p.source_id, p.part_index, p.part_type) for p in selected],
            target_setting=target_setting,
        )
        return selected, recipe

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        by_type: Dict[str, int] = defaultdict(int)
        by_source: Dict[str, int] = defaultdict(int)
        for p in self.parts:
            by_type[p.part_type] += 1
            by_source[p.source_id] += 1
        return {
            "total_parts": len(self.parts),
            "by_type": dict(by_type),
            "by_source": dict(by_source),
            "sources": sorted(set(p.source_id for p in self.parts)),
        }


# ============================================================================
# HELPERS
# ============================================================================

def _parse_setting(setting_str: str) -> Tuple[str, str]:
    """Infer period and environment from a free-text setting description."""
    s = setting_str.lower()
    period = ""
    environment = ""
    for p, keywords in PERIOD_KEYWORDS.items():
        if any(kw in s for kw in keywords):
            period = p
            break
    for e, keywords in ENVIRONMENT_KEYWORDS.items():
        if any(kw in s for kw in keywords):
            environment = e
            break
    return period, environment


def load_registry(db_dir: str = "./mystery_database") -> PartRegistry:
    """
    Load the part registry, bootstrapping from test corpus if needed.
    Call this from any CLI command that needs parts.
    """
    registry = PartRegistry(db_dir)
    if not registry.load():
        registry.populate_from_test_corpus()
        registry.load_extractions()
        registry.save()
    return registry
