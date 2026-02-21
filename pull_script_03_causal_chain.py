"""
Pull Script 03 — Causal Chain Extraction
==========================================

Extracts the cause→effect clue graph from a mystery source text and
produces a PlayableMystery — the canonical target schema shared by all
pull scripts.

Why causal chain vs. flat evidence list:
    A flat list tells you what the clues ARE.
    A causal chain tells you how clues UNLOCK each other and which
    combination uniquely identifies the culprit. That structure is
    what makes a mystery solvable in a bounded number of rounds.

Playability is measured by three metrics:
    MCD  — Minimum Clue Depth: fewest clues needed to reach a unique solution
    RSE  — Round-to-Solution Estimate: rounds needed with N players + 75% sharing
    UST  — Unique Solution Test: exactly one valid culprit given the critical clue set

Run without API key (demo mode):
    python pull_script_03_causal_chain.py

Run with real extraction (requires ANTHROPIC_API_KEY):
    python pull_script_03_causal_chain.py --real
"""

import os
import re
import json
import math
import random
import argparse
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# TARGET SCHEMA — PlayableMystery
# This is the shared output format for all 7 pull scripts.
# Every pull script must produce a PlayableMystery JSON.
# ============================================================

# Canonical vocabulary for investigation topics.
#
# Every entry in PlayableCharacter.interrogation_topics and every
# PlayableClue.topic_tag must be a key from this dict.
# The values are human-readable display labels shown to players
# before they type their interrogation question.
#
# Character interrogation topics (ask a person):
#   alibi               — Whereabouts & alibi
#   relationship_with_victim — Relationship with victim
#   motive              — Motive & grievances
#   witness_account     — What they saw or heard
#   expertise_and_access — Specialist knowledge or access
#   victim_behaviour    — Victim's recent behaviour
#   knowledge_of_others — Knowledge of others present
#   evidence_observed   — Evidence they personally observed
#
# Location examination topics (search a place):
#   scene_condition     — State of the scene
#   entry_exit          — Entry & exit points
#   physical_trace      — Physical traces & objects
#   documents_records   — Documents & records
INVESTIGATION_TOPICS: Dict[str, str] = {
    # Character interrogation
    "alibi":                    "Whereabouts & alibi",
    "relationship_with_victim": "Relationship with victim",
    "motive":                   "Motive & grievances",
    "witness_account":          "What they saw or heard",
    "expertise_and_access":     "Specialist knowledge or access",
    "victim_behaviour":         "Victim's recent behaviour",
    "knowledge_of_others":      "Knowledge of others present",
    "evidence_observed":        "Evidence they personally observed",
    # Location examination
    "scene_condition":          "State of the scene",
    "entry_exit":               "Entry & exit points",
    "physical_trace":           "Physical traces & objects",
    "documents_records":        "Documents & records",
}

# Canonical archetype classes — setting-agnostic social function categories.
#
# archetype_class drives game logic (default topic suggestions, role heuristics).
# archetype_label is free text shown to players (e.g. "Butler", "Colony Medic",
# "Grand Vizier") — it changes with the setting, the class does not.
#
# Nine classes covering the investigative space:
#   intimate_partner  — romantic/spousal relation to victim
#   family            — blood or legal relation
#   rival             — direct competitor or antagonist
#   authority         — person with power, status, or command
#   professional      — person with specialist knowledge or skills
#   worker            — person employed in service or labour
#   associate         — peer with no close personal tie to the victim
#   investigator      — person whose role involves uncovering truth
#   criminal_associate — person with ties to criminal activity
#
# default_topics: suggested interrogation_topics for a character of this class.
# These are starting points — CausalChainExtractor may override per character.
ARCHETYPE_CLASSES: Dict[str, Dict] = {
    "intimate_partner": {
        "label": "Intimate Partner",
        "description": "Romantic or spousal relationship to the victim",
        "default_topics": [
            "alibi", "relationship_with_victim", "victim_behaviour", "knowledge_of_others",
        ],
    },
    "family": {
        "label": "Family Member",
        "description": "Blood or legal relation to the victim",
        "default_topics": [
            "alibi", "relationship_with_victim", "motive", "documents_records",
        ],
    },
    "rival": {
        "label": "Rival",
        "description": "Direct competitor or antagonist",
        "default_topics": [
            "alibi", "relationship_with_victim", "motive", "knowledge_of_others",
        ],
    },
    "authority": {
        "label": "Authority Figure",
        "description": "Person with power, high status, or command",
        "default_topics": [
            "alibi", "witness_account", "knowledge_of_others",
        ],
    },
    "professional": {
        "label": "Professional",
        "description": "Person with specialist knowledge or skills",
        "default_topics": [
            "alibi", "expertise_and_access", "evidence_observed", "knowledge_of_others",
        ],
    },
    "worker": {
        "label": "Worker",
        "description": "Person employed in service or labour",
        "default_topics": [
            "alibi", "witness_account", "knowledge_of_others",
        ],
    },
    "associate": {
        "label": "Associate",
        "description": "Peer with no close personal tie to the victim",
        "default_topics": [
            "alibi", "witness_account", "knowledge_of_others",
        ],
    },
    "investigator": {
        "label": "Investigator",
        "description": "Person whose role involves uncovering truth",
        "default_topics": [
            "evidence_observed", "expertise_and_access", "knowledge_of_others",
        ],
    },
    "criminal_associate": {
        "label": "Criminal Associate",
        "description": "Person with ties to criminal activity",
        "default_topics": [
            "alibi", "motive", "knowledge_of_others",
        ],
    },
}


@dataclass
class PlayableClue:
    """
    A single node in the causal clue graph.

    Why graph instead of list:
        Clues have prerequisites (you can't deduce X until you know Y)
        and they unlock each other. A graph captures that structure so
        the simulator can model realistic round-by-round discovery.
    """
    clue_id: str
    description: str              # Abstract — setting-agnostic wording
    evidence_type: str            # physical | testimonial | circumstantial
    is_red_herring: bool = False

    # Graph edges
    prerequisite_clues: List[str] = field(default_factory=list)  # must find these first
    leads_to: List[str] = field(default_factory=list)            # unlocks these

    # Who this clue affects
    implicates: List[str] = field(default_factory=list)          # character_ids pointed at
    eliminates: List[str] = field(default_factory=list)          # character_ids ruled out

    # Red herring bookkeeping
    disprovable_by: Optional[str] = None   # clue_id that disproves this if red herring

    # Gameplay tuning
    round_weight: int = 1          # 1=early game, 2=mid, 3=late, 4=final reveal
    shareable: bool = True         # False = one of the 25% a player may withhold

    # Interrogation routing — used by ScriptedNPCResponder during gameplay
    discoverable_from: str = ""              # character_id or location_id that surfaces this clue
    topic_tag: str = ""                      # must be a key in INVESTIGATION_TOPICS
    discovery_hints: List[str] = field(default_factory=list)  # example questions that unlock this clue


@dataclass
class PlayableCharacter:
    """
    A character role stripped of setting-specific details.

    Why abstract roles:
        "Dr. Sterling" can become "the colony medic" on Mars or
        "the apothecary" in 1920s Paris. The role and motive_type
        survive the transplant; the name and costume do not.

    archetype_class vs archetype_label:
        archetype_class is canonical (from ARCHETYPE_CLASSES) and drives game
        logic — default topic suggestions, role heuristics. It never changes
        across setting transplants.
        archetype_label is free text shown to players. It changes with the
        setting: "Butler" on Earth → "Life Support Technician" on Mars →
        "Grand Chamberlain" in 1400s Byzantium.
    """
    character_id: str
    role: str                      # culprit | victim | witness | suspect | investigator
    archetype_class: str           # key from ARCHETYPE_CLASSES (e.g. "professional", "worker")
    archetype_label: str           # setting-specific display name (e.g. "Physician", "Butler")
    motive_type: Optional[str]     # greed | revenge | fear | jealousy | ideology | love | None
    motive_description: str = ""
    alibi: str = ""
    alibi_valid: bool = True
    revealing_clues: List[str] = field(default_factory=list)  # clue_ids that expose this character
    interrogation_topics: List[str] = field(default_factory=list)  # keys from INVESTIGATION_TOPICS; shown as menu before player types their question


@dataclass
class PlayableMystery:
    """
    The canonical output schema for all pull scripts.

    Populated by Script 3 via causal chain extraction.
    Evaluated by PlayabilityCalculator for game fitness.
    """
    mystery_id: str
    source_id: str                 # links back to original MysteryScenario
    extraction_method: str = "causal_chain"

    # Crime basics
    crime_type: str = ""           # murder | theft | fraud | kidnapping …
    crime_description: str = ""
    victim_id: Optional[str] = None

    # Ground truth (hidden from players until solved)
    culprit_id: Optional[str] = None
    solution_motive_type: str = ""
    solution_method: str = ""

    # Graph
    characters: List[PlayableCharacter] = field(default_factory=list)
    clue_chain: List[PlayableClue] = field(default_factory=list)

    # Calculated playability metrics
    minimum_clue_depth: int = 0
    red_herring_ratio: float = 0.0
    rounds_to_solve: Dict[str, int] = field(default_factory=dict)  # "3_players": N
    unique_solution_test: bool = False
    playability_score: float = 0.0

    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# EXTRACTION — REAL (Claude API)
# ============================================================

class CausalChainExtractor:
    """
    Extracts the causal clue chain from raw mystery text using Claude.

    Why Claude for extraction:
        Building a cause→effect clue graph requires deep reading comprehension
        and inference that rule-based NLP cannot reliably produce.
    """

    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-sonnet-4-6"

    def extract(self, raw_text: str, metadata: Dict) -> PlayableMystery:
        """Full extraction pipeline: characters → clues → solution → build mystery."""
        source_id = metadata.get("id", "unknown")
        mystery_id = f"causal_{re.sub(r'[^a-z0-9]+', '_', metadata.get('title', 'mystery').lower())}"

        print("  [1/3] Extracting characters and roles...")
        characters = self._extract_characters(raw_text)

        print("  [2/3] Extracting causal clue chain...")
        char_ids = [c.character_id for c in characters]
        clue_chain = self._extract_clue_chain(raw_text, char_ids)

        print("  [3/3] Extracting solution...")
        solution = self._extract_solution(raw_text, char_ids)

        mystery = PlayableMystery(
            mystery_id=mystery_id,
            source_id=source_id,
            crime_type=solution.get("crime_type", "unknown"),
            crime_description=solution.get("crime_description", ""),
            victim_id=solution.get("victim_id"),
            culprit_id=solution.get("culprit_id"),
            solution_motive_type=solution.get("motive_type", ""),
            solution_method=solution.get("method", ""),
            characters=characters,
            clue_chain=clue_chain,
        )
        return mystery

    def _extract_characters(self, text: str) -> List[PlayableCharacter]:
        """Extract characters as abstract roles, not setting-specific names."""
        archetype_classes = " | ".join(ARCHETYPE_CLASSES.keys())
        prompt = f"""Analyze this mystery and extract each key character.

{text[:5000]}

For each character return a JSON object with:
- character_id: short snake_case identifier (e.g. "char_culprit", "char_victim")
- role: one of culprit | victim | witness | suspect | investigator
- archetype_class: the character's social function — must be one of:
    {archetype_classes}
  Choose based on their relationship to the victim and social role, not their job title.
  This value must survive a setting transplant (the same class applies whether the
  mystery is Victorian, futuristic, or medieval).
- archetype_label: a setting-specific display label shown to players
  (e.g. "Physician", "Butler", "Colony Medic", "Grand Vizier", "Rival Scholar").
  This should match the mystery's setting and tone.
- motive_type: one of greed | revenge | fear | jealousy | ideology | love | null
- motive_description: 1 sentence, or empty string if not applicable
- alibi: their claimed alibi, or empty string
- alibi_valid: true if alibi holds up, false if it breaks down
- interrogation_topics: list of 3–5 keys from the canonical INVESTIGATION_TOPICS vocabulary below.
  Use an empty list for deceased characters. Only include topics this character can genuinely speak to.

  Valid topic keys (character interrogation):
    alibi                 — Whereabouts & alibi
    relationship_with_victim — Relationship with victim
    motive                — Motive & grievances
    witness_account       — What they saw or heard
    expertise_and_access  — Specialist knowledge or access
    victim_behaviour      — Victim's recent behaviour
    knowledge_of_others   — Knowledge of others present
    evidence_observed     — Evidence they personally observed

Respond ONLY with a JSON array of these objects. Include 4–8 characters."""

        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)
            return [
                PlayableCharacter(
                    character_id=c.get("character_id", f"char_{i}"),
                    role=c.get("role", "suspect"),
                    archetype_class=c.get("archetype_class", "associate"),
                    archetype_label=c.get("archetype_label", c.get("archetype_class", "Unknown")),
                    motive_type=c.get("motive_type"),
                    motive_description=c.get("motive_description", ""),
                    alibi=c.get("alibi", ""),
                    alibi_valid=c.get("alibi_valid", True),
                    interrogation_topics=c.get("interrogation_topics", []),
                )
                for i, c in enumerate(data)
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: character extraction failed ({e}), using empty list")
            return []

    def _extract_clue_chain(self, text: str, char_ids: List[str]) -> List[PlayableClue]:
        """
        Extract the causal clue graph.

        Why prerequisite/leads_to links matter:
            They define the order in which clues become discoverable per round.
            Without them, we can't estimate RSE accurately.
        """
        char_list = ", ".join(char_ids)
        prompt = f"""Analyze this mystery and map every significant clue as a node in a causal graph.

{text[:7000]}

Known character IDs: {char_list}

For each clue return a JSON object with:
- clue_id: short snake_case id (e.g. "c1_locked_door", "c2_fiber_in_keyhole")
- description: abstract, setting-agnostic 1–2 sentence description of what this clue reveals
- evidence_type: physical | testimonial | circumstantial
- is_red_herring: true if this clue misleads, false if it advances the solution
- prerequisite_clues: list of clue_ids that must be found BEFORE this clue becomes available (can be empty)
- leads_to: list of clue_ids that discovering this clue makes available next
- implicates: list of character_ids this clue points toward as guilty
- eliminates: list of character_ids this clue rules out
- disprovable_by: clue_id that disproves this clue if it is a red herring, else null
- round_weight: integer 1–4 indicating natural discovery timing (1=opening, 4=final)
- shareable: true if players would naturally share this, false if they might withhold it
- discoverable_from: the character_id or location_id (use "location_<name>" for physical locations)
  that a player must interrogate or examine to surface this clue
- topic_tag: must be a key from the canonical vocabulary below matching the source's topic list
- discovery_hints: list of 2–3 example questions a player could ask to discover this clue,
  phrased naturally as a player would speak them (e.g. "Were there fingerprints on the weapon?")

  Valid topic_tag keys for characters:
    alibi | relationship_with_victim | motive | witness_account |
    expertise_and_access | victim_behaviour | knowledge_of_others | evidence_observed

  Valid topic_tag keys for locations (discoverable_from starts with "location_"):
    scene_condition | entry_exit | physical_trace | documents_records

Return ONLY a JSON array of these objects. Include all meaningful clues (aim for 6–12).
Clues should form a connected graph leading to the solution."""

        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)
            return [
                PlayableClue(
                    clue_id=c.get("clue_id", f"c{i}"),
                    description=c.get("description", ""),
                    evidence_type=c.get("evidence_type", "physical"),
                    is_red_herring=c.get("is_red_herring", False),
                    prerequisite_clues=c.get("prerequisite_clues", []),
                    leads_to=c.get("leads_to", []),
                    implicates=c.get("implicates", []),
                    eliminates=c.get("eliminates", []),
                    disprovable_by=c.get("disprovable_by"),
                    round_weight=c.get("round_weight", 1),
                    shareable=c.get("shareable", True),
                    discoverable_from=c.get("discoverable_from", ""),
                    topic_tag=c.get("topic_tag", ""),
                    discovery_hints=c.get("discovery_hints", []),
                )
                for i, c in enumerate(data)
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: clue chain extraction failed ({e}), using empty list")
            return []

    def _extract_solution(self, text: str, char_ids: List[str]) -> Dict:
        """Extract the ground-truth solution: culprit, motive, method."""
        char_list = ", ".join(char_ids)
        prompt = f"""Read this mystery and identify the solution.

{text[:6000]}

Known character IDs: {char_list}

Respond ONLY with JSON containing:
- crime_type: murder | theft | fraud | kidnapping | disappearance | other
- crime_description: 1–2 sentences describing the crime
- victim_id: character_id of the victim (from the known IDs above)
- culprit_id: character_id of the culprit (from the known IDs above)
- motive_type: greed | revenge | fear | jealousy | ideology | love
- method: 1 sentence describing how the crime was committed"""

        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip().strip("```json").strip("```").strip()
            return json.loads(raw)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: solution extraction failed ({e}), returning empty")
            return {}


# ============================================================
# EXTRACTION — MOCK (no API required)
# ============================================================

class MockCausalChainExtractor:
    """
    Produces a hand-crafted PlayableMystery from the locked-room sample
    mystery without making any API calls.

    Why a mock:
        Lets us validate the schema, calculator, and storage layer before
        spending API credits. Same reason demo_acquisition.py exists.
    """

    def extract(self, raw_text: str, metadata: Dict) -> PlayableMystery:
        print("  [DEMO] Using pre-built causal chain (no API call)")

        characters = [
            PlayableCharacter(
                character_id="char_victim",
                role="victim",
                archetype_class="authority",
                archetype_label="Nobleman",
                motive_type=None,
                alibi="",
                alibi_valid=True,
                interrogation_topics=[],   # deceased — not interrogatable
            ),
            PlayableCharacter(
                character_id="char_culprit",
                role="culprit",
                archetype_class="professional",
                archetype_label="Physician",
                motive_type="jealousy",
                motive_description="Preventing a rival from benefiting from a research foundation",
                alibi="Claims he was in his guest room all evening",
                alibi_valid=False,
                revealing_clues=["c5_fibers", "c6_sedative"],
                interrogation_topics=[
                    "alibi",                    # movements that evening
                    "relationship_with_victim",  # why he was invited/trusted
                    "expertise_and_access",      # forensic/medical knowledge
                    "victim_behaviour",          # victim's fear and why he was called
                ],
            ),
            PlayableCharacter(
                character_id="char_spouse",
                role="suspect",
                archetype_class="intimate_partner",
                archetype_label="Spouse",
                motive_type="greed",
                motive_description="Disinherited by will change",
                alibi="Claims she was in her chambers",
                alibi_valid=True,
                revealing_clues=["c3_will_change"],
                interrogation_topics=[
                    "alibi",                    # where she was
                    "relationship_with_victim",  # marriage dynamics
                    "victim_behaviour",          # husband's paranoia / why physician was invited
                    "knowledge_of_others",       # who else was present / their movements
                ],
            ),
            PlayableCharacter(
                character_id="char_relative",
                role="suspect",
                archetype_class="family",
                archetype_label="Niece",
                motive_type="greed",
                motive_description="Discovered exclusion from will",
                alibi="Was in the library",
                alibi_valid=True,
                revealing_clues=["c3_will_change"],
                interrogation_topics=[
                    "alibi",             # was in the library
                    "documents_records", # saw the will document
                    "motive",            # family tension / disinheritance
                    "knowledge_of_others",
                ],
            ),
            PlayableCharacter(
                character_id="char_witness",
                role="witness",
                archetype_class="worker",
                archetype_label="Butler",
                motive_type=None,
                alibi="Heard nothing unusual",
                alibi_valid=True,
                interrogation_topics=[
                    "witness_account",      # found the body; observations that evening
                    "knowledge_of_others",  # household routine; guest movements
                ],
            ),
            PlayableCharacter(
                character_id="char_investigator",
                role="investigator",
                archetype_class="investigator",
                archetype_label="Inspector",
                motive_type=None,
                interrogation_topics=[
                    "evidence_observed",    # forensic results and crime scene analysis
                    "expertise_and_access", # locked-room mechanism reconstruction
                    "knowledge_of_others",  # suspect interview findings
                ],
            ),
        ]

        # The causal chain for the locked-room murder:
        #
        # Round 1 (opening):
        #   c1_body_discovered  →  c2_weapon_clean, rh1_locked_door, rh2_sealed_windows
        #   c3_will_change      →  implicates spouse + relative
        #
        # Round 2 (mid-game):
        #   c4_victim_paranoia  →  reveals culprit had special access
        #   c4 + c3  →  c5_fibers, c6_sedative (culprit-specific)
        #
        # Round 3 (closing):
        #   c5_fibers           →  uniquely implicates culprit
        #   c6_sedative         →  confirms only physician could administer
        #   c7_string_trick     →  disproves rh1 and rh2
        #
        # MCD path: c3 → c4 → c5 (+ c6 for confirmation) = 4 clues

        clue_chain = [
            PlayableClue(
                clue_id="c1_body_discovered",
                description="The victim is found dead in a locked room with no apparent entry or exit.",
                evidence_type="physical",
                is_red_herring=False,
                prerequisite_clues=[],
                leads_to=["c2_weapon_clean", "rh1_locked_door", "rh2_sealed_windows", "c3_will_change"],
                implicates=[],
                eliminates=[],
                round_weight=1,
                shareable=True,
                discoverable_from="char_witness",
                topic_tag="witness_account",
                discovery_hints=[
                    "What did you find when you entered the study this morning?",
                    "Can you describe exactly what you saw when you discovered the body?",
                    "Was the door locked when you arrived?",
                ],
            ),
            PlayableClue(
                clue_id="c2_weapon_clean",
                description="The murder weapon bears no fingerprints, suggesting deliberate staging by someone knowledgeable.",
                evidence_type="physical",
                is_red_herring=False,
                prerequisite_clues=["c1_body_discovered"],
                leads_to=["c4_victim_paranoia"],
                implicates=[],
                eliminates=[],
                round_weight=1,
                shareable=True,
                discoverable_from="location_study",
                topic_tag="physical_trace",
                discovery_hints=[
                    "Were there any fingerprints on the murder weapon?",
                    "What does the condition of the letter opener tell you?",
                    "Is there any sign the crime scene was staged?",
                ],
            ),
            PlayableClue(
                clue_id="c3_will_change",
                description="The victim recently changed their will to exclude family members in favor of a professional cause.",
                evidence_type="testimonial",
                is_red_herring=False,
                prerequisite_clues=["c1_body_discovered"],
                leads_to=["c4_victim_paranoia"],
                implicates=["char_spouse", "char_relative"],
                eliminates=[],
                round_weight=1,
                shareable=True,
                discoverable_from="char_relative",
                topic_tag="documents_records",
                discovery_hints=[
                    "Did you see any legal documents belonging to the deceased?",
                    "Were there recent changes to the estate arrangements?",
                    "What did you find in the library that evening?",
                ],
            ),
            PlayableClue(
                clue_id="c4_victim_paranoia",
                description="The victim had been increasingly fearful and had specifically invited a trusted specialist to stay.",
                evidence_type="testimonial",
                is_red_herring=False,
                prerequisite_clues=["c3_will_change"],
                leads_to=["c5_fibers", "c6_sedative", "c7_string_trick"],
                implicates=["char_culprit"],
                eliminates=["char_spouse", "char_relative"],
                round_weight=2,
                shareable=True,
                discoverable_from="char_spouse",
                topic_tag="victim_behaviour",
                discovery_hints=[
                    "Had your husband been acting differently before his death?",
                    "Why was the physician invited to stay at the house?",
                    "Was your husband afraid of something or someone?",
                ],
            ),
            PlayableClue(
                clue_id="c5_fibers",
                description="Fabric fibers from a distinctive garment are found lodged at the point of forced entry, uniquely identifying the perpetrator.",
                evidence_type="physical",
                is_red_herring=False,
                prerequisite_clues=["c4_victim_paranoia"],
                leads_to=[],
                implicates=["char_culprit"],
                eliminates=["char_spouse", "char_relative", "char_witness"],
                round_weight=3,
                shareable=True,
                discoverable_from="location_study",
                topic_tag="physical_trace",
                discovery_hints=[
                    "Was any trace evidence found near the keyhole or entry point?",
                    "Were there any fibres or material left behind by the killer?",
                    "Can the entry point tell us anything about who was there?",
                ],
            ),
            PlayableClue(
                clue_id="c6_sedative",
                description="Chemical analysis shows the victim was sedated before death — a method only someone with medical expertise could execute undetected.",
                evidence_type="physical",
                is_red_herring=False,
                prerequisite_clues=["c4_victim_paranoia"],
                leads_to=[],
                implicates=["char_culprit"],
                eliminates=["char_spouse", "char_relative", "char_witness"],
                round_weight=3,
                shareable=False,   # The investigator might withhold this pending lab confirmation
                discoverable_from="char_investigator",
                topic_tag="evidence_observed",
                discovery_hints=[
                    "What did the toxicology report reveal?",
                    "Was there any evidence the victim had been drugged?",
                    "Could someone without medical training have done this?",
                ],
            ),
            PlayableClue(
                clue_id="c7_string_trick",
                description="The 'locked from inside' condition is shown to be reproducible from outside using a simple mechanical technique known to specialists.",
                evidence_type="physical",
                is_red_herring=False,
                prerequisite_clues=["c4_victim_paranoia"],
                leads_to=[],
                implicates=["char_culprit"],
                eliminates=["char_spouse", "char_relative"],
                disprovable_by=None,
                round_weight=3,
                shareable=True,
                discoverable_from="char_investigator",
                topic_tag="expertise_and_access",
                discovery_hints=[
                    "Is it actually possible to lock the door from outside?",
                    "How could the killer have created the locked-room illusion?",
                    "What specialist knowledge would be needed to fake an inside lock?",
                ],
            ),
            PlayableClue(
                clue_id="rh1_locked_door",
                description="The crime scene appears to be an impossible locked room — no way in or out.",
                evidence_type="physical",
                is_red_herring=True,
                prerequisite_clues=["c1_body_discovered"],
                leads_to=[],
                implicates=[],
                eliminates=[],
                disprovable_by="c7_string_trick",
                round_weight=1,
                shareable=True,
                discoverable_from="location_study",
                topic_tag="scene_condition",
                discovery_hints=[
                    "How was access to the room restricted?",
                    "Is there any way someone could have entered from outside?",
                ],
            ),
            PlayableClue(
                clue_id="rh2_sealed_windows",
                description="All windows are sealed shut, reinforcing the impossibility of external entry.",
                evidence_type="physical",
                is_red_herring=True,
                prerequisite_clues=["c1_body_discovered"],
                leads_to=[],
                implicates=[],
                eliminates=[],
                disprovable_by="c7_string_trick",
                round_weight=1,
                shareable=True,
                discoverable_from="location_study",
                topic_tag="scene_condition",
                discovery_hints=[
                    "What was the state of the windows?",
                    "Could anyone have entered through a window?",
                ],
            ),
        ]

        source_id = metadata.get("id", "demo_locked_room")
        mystery_id = f"causal_{re.sub(r'[^a-z0-9]+', '_', metadata.get('title', 'mystery').lower())}"

        return PlayableMystery(
            mystery_id=mystery_id,
            source_id=source_id,
            crime_type="murder",
            crime_description="A prominent figure is found stabbed in a study locked from the inside.",
            victim_id="char_victim",
            culprit_id="char_culprit",
            solution_motive_type="jealousy",
            solution_method="Sedation followed by stabbing; locked-room illusion created with string-through-keyhole technique.",
            characters=characters,
            clue_chain=clue_chain,
        )


# ============================================================
# PLAYABILITY CALCULATOR
# ============================================================

class PlayabilityCalculator:
    """
    Evaluates a PlayableMystery for game fitness.

    Applies three metrics (MCD, RSE, UST) then produces a composite
    playability score in [0, 1].

    Why simulate instead of score subjectively:
        A simulation respects the actual game rules (round count,
        75% sharing) rather than proxy heuristics like "clue count".
    """

    # Scoring thresholds
    MCD_MIN = 4
    MCD_MAX = 8
    RSE_LIMIT = 4          # must be solvable within this many rounds
    PLAYER_COUNTS = [3, 4, 5]
    CLUES_PER_PLAYER_PER_ROUND = 1
    SHARE_FRACTION = 0.75

    def calculate(self, mystery: PlayableMystery) -> PlayableMystery:
        """Run all metrics and write results back into the mystery object."""
        mystery.minimum_clue_depth = self._mcd(mystery)
        mystery.red_herring_ratio = self._rhr(mystery)
        mystery.unique_solution_test = self._ust(mystery)
        mystery.rounds_to_solve = {
            f"{n}_players": self._rse(mystery, n)
            for n in self.PLAYER_COUNTS
        }
        mystery.playability_score = self._score(mystery)
        return mystery

    # ----------------------------------------------------------
    # MCD — Minimum Clue Depth
    # ----------------------------------------------------------

    def _mcd(self, mystery: PlayableMystery) -> int:
        """
        BFS over the causal graph to find the shortest clue path that
        uniquely identifies the culprit.

        Why BFS:
            We want the minimum number of clues, not the first path found.
            BFS guarantees the shortest path in an unweighted graph.
        """
        culprit = mystery.culprit_id
        if not culprit:
            return 0

        clue_map = {c.clue_id: c for c in mystery.clue_chain}
        real_clues = [c for c in mystery.clue_chain if not c.is_red_herring]

        # Root clues: those with no prerequisites
        roots = [c for c in real_clues if not c.prerequisite_clues]

        # BFS: track (found_clue_ids, depth)
        # A solution path ends when the culprit is uniquely implicated
        from collections import deque
        queue = deque()
        for root in roots:
            queue.append((frozenset([root.clue_id]), 1))

        visited = set()
        best_depth = len(real_clues)  # worst case: all clues needed

        while queue:
            found, depth = queue.popleft()
            state_key = found
            if state_key in visited:
                continue
            visited.add(state_key)

            if self._uniquely_identifies_culprit(found, clue_map, culprit, mystery):
                best_depth = min(best_depth, depth)
                continue  # don't explore deeper from a solved state

            if depth >= best_depth:
                continue

            # Expand: find clues whose prerequisites are all satisfied
            for clue in real_clues:
                if clue.clue_id in found:
                    continue
                if all(p in found for p in clue.prerequisite_clues):
                    queue.append((found | frozenset([clue.clue_id]), depth + 1))

        return best_depth

    def _uniquely_identifies_culprit(
        self,
        found_ids: frozenset,
        clue_map: Dict[str, PlayableClue],
        culprit: str,
        mystery: PlayableMystery,
    ) -> bool:
        """
        Returns True if the found clue set implicates the culprit and
        eliminates all other suspects.
        """
        suspects = {c.character_id for c in mystery.characters if c.role == "suspect"}
        culprit_implicated = any(
            culprit in clue_map[cid].implicates
            for cid in found_ids
            if cid in clue_map
        )
        if not culprit_implicated:
            return False

        eliminated = set()
        for cid in found_ids:
            if cid in clue_map:
                eliminated.update(clue_map[cid].eliminates)

        other_suspects = suspects - {culprit}
        return other_suspects.issubset(eliminated)

    # ----------------------------------------------------------
    # RSE — Round-to-Solution Estimate
    # ----------------------------------------------------------

    def _rse(self, mystery: PlayableMystery, num_players: int) -> int:
        """
        Simulate N-player gameplay with 75% sharing and estimate how many
        rounds until the collective shared pool reaches MCD critical clues.

        Returns the round number (1–4), or 99 if unsolvable in 4 rounds.

        Why simulate stochastically:
            Clue distribution among players is random. Running 200 trials
            and taking the median gives a realistic estimate rather than
            an optimistic best-case.
        """
        mcd = mystery.minimum_clue_depth
        if mcd == 0:
            return 1

        real_clue_ids = [c.clue_id for c in mystery.clue_chain if not c.is_red_herring]
        if not real_clue_ids:
            return 99

        clue_map = {c.clue_id: c for c in mystery.clue_chain}
        trials = 200
        results = []

        for _ in range(trials):
            shared_pool: set = set()
            available = {
                c.clue_id for c in mystery.clue_chain
                if not c.is_red_herring and not c.prerequisite_clues
            }
            solved_round = 99

            for round_num in range(1, self.RSE_LIMIT + 1):
                # Each player finds one clue from the available pool
                found_this_round: set = set()
                for _ in range(num_players * self.CLUES_PER_PLAYER_PER_ROUND):
                    eligible = list(available - found_this_round - shared_pool)
                    if not eligible:
                        break
                    chosen = random.choice(eligible)
                    found_this_round.add(chosen)

                # 75% of found clues get shared
                num_shared = math.ceil(len(found_this_round) * self.SHARE_FRACTION)
                newly_shared = set(random.sample(list(found_this_round), min(num_shared, len(found_this_round))))
                shared_pool.update(newly_shared)

                # Unlock new clues whose prerequisites are now in the shared pool
                for clue in mystery.clue_chain:
                    if clue.is_red_herring:
                        continue
                    if clue.clue_id not in available and all(
                        p in shared_pool for p in clue.prerequisite_clues
                    ):
                        available.add(clue.clue_id)

                # Check if MCD is satisfied
                if self._uniquely_identifies_culprit(
                    frozenset(shared_pool), clue_map, mystery.culprit_id, mystery
                ):
                    solved_round = round_num
                    break

            results.append(solved_round)

        # Return median (conservative estimate)
        results.sort()
        return results[len(results) // 2]

    # ----------------------------------------------------------
    # Red Herring Ratio
    # ----------------------------------------------------------

    def _rhr(self, mystery: PlayableMystery) -> float:
        """Fraction of clues that are red herrings."""
        total = len(mystery.clue_chain)
        if total == 0:
            return 0.0
        red = sum(1 for c in mystery.clue_chain if c.is_red_herring)
        return round(red / total, 2)

    # ----------------------------------------------------------
    # UST — Unique Solution Test
    # ----------------------------------------------------------

    def _ust(self, mystery: PlayableMystery) -> bool:
        """
        After collecting ALL non-red-herring clues, does exactly one
        character remain as the culprit?

        Why check all clues, not just MCD path:
            If even the full clue set leaves ambiguity, the mystery is broken.
        """
        if not mystery.culprit_id:
            return False

        clue_map = {c.clue_id: c for c in mystery.clue_chain}
        all_real = frozenset(c.clue_id for c in mystery.clue_chain if not c.is_red_herring)
        return self._uniquely_identifies_culprit(
            all_real, clue_map, mystery.culprit_id, mystery
        )

    # ----------------------------------------------------------
    # Composite Playability Score
    # ----------------------------------------------------------

    def _score(self, mystery: PlayableMystery) -> float:
        """
        Composite score in [0, 1].

        Components:
            UST pass/fail  — 0.4 weight (a broken mystery is disqualified)
            MCD in range   — 0.3 weight
            RSE ≤ 4 rounds — 0.2 weight (median across player counts)
            RHR in range   — 0.1 weight (20–40% red herrings is ideal)
        """
        score = 0.0

        # UST: required
        if not mystery.unique_solution_test:
            return 0.0
        score += 0.4

        # MCD: ideal range 4–8
        mcd = mystery.minimum_clue_depth
        if self.MCD_MIN <= mcd <= self.MCD_MAX:
            score += 0.3
        elif mcd > 0:
            # Partial credit: penalise proportionally to distance from range
            distance = min(abs(mcd - self.MCD_MIN), abs(mcd - self.MCD_MAX))
            score += max(0.0, 0.3 - distance * 0.05)

        # RSE: at least one player count solvable in ≤4 rounds
        rse_values = list(mystery.rounds_to_solve.values())
        if rse_values and min(rse_values) <= self.RSE_LIMIT:
            score += 0.2
        elif rse_values:
            best = min(rse_values)
            score += max(0.0, 0.2 - (best - self.RSE_LIMIT) * 0.05)

        # RHR: ideal 0.20–0.40
        rhr = mystery.red_herring_ratio
        if 0.20 <= rhr <= 0.40:
            score += 0.1
        elif rhr > 0:
            score += 0.05  # some red herrings, just outside range

        return round(score, 3)


# ============================================================
# STORAGE
# ============================================================

class CausalChainDatabase:
    """
    Saves PlayableMystery objects as JSON under ./causal_chain_output/.

    Why separate from MysteryDatabase:
        Each pull script produces a different schema variant.
        Keeping outputs in separate folders avoids collision and makes
        comparison across scripts straightforward.
    """

    def __init__(self, storage_path: str = "./causal_chain_output"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def save(self, mystery: PlayableMystery) -> str:
        path = os.path.join(self.storage_path, f"{mystery.mystery_id}.json")
        with open(path, "w") as f:
            json.dump(asdict(mystery), f, indent=2)
        print(f"  Saved: {path}")
        return path

    def load(self, mystery_id: str) -> Optional[Dict]:
        path = os.path.join(self.storage_path, f"{mystery_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)


# ============================================================
# PIPELINE RUNNER
# ============================================================

def run_pipeline(raw_text: str, metadata: Dict, use_real_api: bool = False) -> PlayableMystery:
    """
    Full pipeline: Extract → Calculate → Save → Report

    Args:
        raw_text: Source mystery text
        metadata: Dict with at least 'title' and 'id'
        use_real_api: If True, calls Claude. If False, uses mock data.

    Returns:
        Populated and scored PlayableMystery
    """
    print(f"\n{'='*60}")
    print(f"CAUSAL CHAIN EXTRACTION — {'REAL API' if use_real_api else 'DEMO MODE'}")
    print(f"{'='*60}")
    print(f"Source: {metadata.get('title', 'Unknown')}\n")

    # Step 1: Extract
    if use_real_api:
        extractor = CausalChainExtractor()
    else:
        extractor = MockCausalChainExtractor()

    mystery = extractor.extract(raw_text, metadata)

    # Step 2: Calculate playability
    print("\nCalculating playability metrics...")
    calculator = PlayabilityCalculator()
    mystery = calculator.calculate(mystery)

    # Step 3: Save
    db = CausalChainDatabase()
    db.save(mystery)

    # Step 4: Report
    _print_report(mystery)

    return mystery


def _print_report(mystery: PlayableMystery) -> None:
    """Human-readable summary of the PlayableMystery metrics."""
    print(f"\n{'='*60}")
    print("PLAYABILITY REPORT")
    print(f"{'='*60}")
    print(f"Mystery ID     : {mystery.mystery_id}")
    print(f"Crime type     : {mystery.crime_type}")
    print(f"Characters     : {len(mystery.characters)}")
    print(f"Clues in chain : {len(mystery.clue_chain)} "
          f"({sum(1 for c in mystery.clue_chain if c.is_red_herring)} red herrings)")
    print()
    print(f"Unique Solution Test (UST)  : {'PASS' if mystery.unique_solution_test else 'FAIL'}")
    print(f"Minimum Clue Depth (MCD)    : {mystery.minimum_clue_depth} clues")
    print(f"Red Herring Ratio (RHR)     : {mystery.red_herring_ratio:.0%}")
    print()
    print("Round-to-Solution Estimate (RSE):")
    for label, rounds in mystery.rounds_to_solve.items():
        status = "OK" if rounds <= 4 else "TOO SLOW"
        print(f"  {label:12s}: {rounds} rounds  [{status}]")
    print()
    print(f"PLAYABILITY SCORE  : {mystery.playability_score:.3f} / 1.000")
    if mystery.playability_score >= 0.8:
        verdict = "EXCELLENT — ready for game use"
    elif mystery.playability_score >= 0.6:
        verdict = "GOOD — minor tuning may help"
    elif mystery.playability_score >= 0.4:
        verdict = "MARGINAL — review clue chain"
    else:
        verdict = "POOR — rebuild recommended"
    print(f"VERDICT            : {verdict}")
    print(f"{'='*60}\n")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Causal Chain Pull Script")
    parser.add_argument("--real", action="store_true", help="Use Claude API (requires ANTHROPIC_API_KEY)")
    args = parser.parse_args()

    if args.real and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Run without --real for demo mode.")
        raise SystemExit(1)

    # Use the same sample mystery as demo_acquisition.py for consistency
    SAMPLE_TEXT = """
THE LOCKED ROOM MYSTERY

The body of Lord Ashworth was discovered at 8:17 AM by his butler, Jenkins.
The study door was locked from the inside; windows sealed shut. Lord Ashworth
had been stabbed with his own letter opener — no fingerprints on the weapon.

Present: Lady Margaret Ashworth (wife), Dr. Richard Sterling (physician/guest),
Miss Elizabeth Hart (niece), Jenkins (butler).

Lady Ashworth revealed her husband had been paranoid, fearing poison, which was
why Dr. Sterling had been invited. Miss Hart had seen a legal document showing
the will was changed: the estate now funds medical research, cutting out family.

Inspector Morrison found the locked door trick: a string through the keyhole
could turn the key from outside — knowledge Dr. Sterling had from forensics.

Fibers from Sterling's jacket were caught in the keyhole. Chemical analysis
showed a sedative in Ashworth's system — administered before the stabbing.

Dr. Sterling murdered Lord Ashworth to prevent a foundation that would fund
his rival's research. He staged the locked room to mislead investigators.
"""

    SAMPLE_METADATA = {
        "id": "sample_locked_room",
        "title": "The Locked Room Mystery",
        "author": "A. Sample Author",
    }

    mystery = run_pipeline(SAMPLE_TEXT, SAMPLE_METADATA, use_real_api=args.real)
