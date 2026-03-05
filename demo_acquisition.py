"""
DEMO: Mystery Database Acquisition Pipeline
============================================

Demonstrates the complete pipeline with pre-structured sample data.
No API key or network access required.

The sample mystery ("The Locked Room Mystery") is a Victorian mansion murder.
It uses only evidence categories valid for the 'industrial' tech level:
  physical, chemical, documentary, testimonial, environmental

This is intentional. The tech_level determines what evidence is possible.
For comparison, the six test queries require different tech levels:
  - Murder on Mars (sci_fi):            adds biological, digital
  - Alchemical Forgery (pre_industrial): chemical, documentary primary; no digital
  - Genetic Identity Heist (sci_fi):    biological, digital primary

Run this to create the sample scenario, then run gameplay_validator.py.

When you have an ANTHROPIC_API_KEY and network access, use:
    python mystery_data_acquisition.py
"""

import json
import os
import re
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict


# ============================================================================
# DATA MODELS — identical to mystery_data_acquisition.py
# ============================================================================

@dataclass
class PhysicalClue:
    id: str
    name: str
    description: str
    category: str
    location: str
    what_it_proves: str
    relevance: str
    analysis_required: bool = False
    analysis_method: Optional[str] = None
    false_conclusion: Optional[str] = None
    why_misleading: Optional[str] = None
    what_disproves_it: Optional[str] = None


@dataclass
class TestimonialRevelation:
    id: str
    providing_character: str
    statement: str
    what_it_reveals: str
    relevance: str
    trigger_condition: str
    false_conclusion: Optional[str] = None
    why_misleading: Optional[str] = None
    what_disproves_it: Optional[str] = None


@dataclass
class Character:
    name: str
    role: str
    is_culprit: bool
    occupation: str
    personality_traits: List[str]
    speech_style: str
    interrogation_behavior: str
    what_they_hide: str
    knowledge_about_crime: str
    knowledge_that_helps_solve: List[str] = field(default_factory=list)
    relationship_to_victim: Optional[str] = None
    motive: Optional[str] = None
    alibi: Optional[str] = None
    faction: Optional[str] = None
    cultural_position: Optional[str] = None
    age: Optional[int] = None
    archetype: Optional[str] = None


@dataclass
class TimelineEvent:
    sequence: int
    time: str
    event: str
    participant: str
    visible_to_players: bool


@dataclass
class SolutionStep:
    step_number: int
    clue_ids: List[str]
    logical_inference: str
    conclusion: str


@dataclass
class Faction:
    name: str
    description: str
    goal: str
    members: List[str] = field(default_factory=list)
    tension_with: List[str] = field(default_factory=list)


@dataclass
class MysteryScenario:
    scenario_id: str
    title: str
    source_url: str
    source_type: str
    world_era: str
    world_specific_period: str
    world_tech_level: str
    world_cultural_context: str
    world_physics_constraints: List[str] = field(default_factory=list)
    world_flavor_tags: List[str] = field(default_factory=list)
    crime_type: str = ""
    mystery_type: str = ""
    secondary_tags: List[str] = field(default_factory=list)
    victim_identity: str = ""
    what_happened: str = ""
    how_it_happened: str = ""
    discovery_scenario: str = ""
    surface_observations: List[str] = field(default_factory=list)
    hidden_details: List[str] = field(default_factory=list)
    stakes: str = "personal"
    characters: List[Character] = field(default_factory=list)
    physical_clues: List[PhysicalClue] = field(default_factory=list)
    testimonial_revelations: List[TestimonialRevelation] = field(default_factory=list)
    factions: List[Faction] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)
    solution_steps: List[SolutionStep] = field(default_factory=list)
    culprit_name: str = ""
    solution_method: str = ""
    solution_motive: str = ""
    how_to_deduce: str = ""
    full_text: str = ""
    plot_summary: str = ""
    author: str = "Unknown"
    publication_year: Optional[int] = None
    license_type: str = "unknown"
    processed_date: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# SAMPLE MYSTERY TEXT
# ============================================================================

SAMPLE_MYSTERY_TEXT = """
THE LOCKED ROOM MYSTERY
By A. Sample Author (Public Domain)

Lord Ashworth was found dead in his locked study at 8:17 AM by his butler
Jenkins. The door was locked from the inside; all windows were sealed.
He had been stabbed with his own letter opener — wiped clean of fingerprints.

Guests present that night:
- Dr. Richard Sterling (physician, weekend guest)
- Lady Margaret Ashworth (wife)
- Miss Elizabeth Hart (niece, from London)
- Jenkins (butler)

Lord Ashworth had recently changed his will, cutting all family to establish
a medical research foundation benefiting Dr. Sterling's rival.

Inspector Morrison discovered the lock could be manipulated from outside using
string through the keyhole. Fiber analysis matched Dr. Sterling's jacket.
Post-mortem toxicology revealed chloral hydrate sedation before the stabbing.
Jenkins, on second questioning, admitted seeing Dr. Sterling in the corridor
near the study at approximately 1 AM.
"""


# ============================================================================
# MOCK PROCESSOR
# ============================================================================

class MockMysteryProcessor:
    """
    Pre-structured output simulating what Claude would extract.
    Demonstrates the full schema including all interrogation-mechanics fields.
    """

    def process_mystery(self, raw_text: str, metadata: Dict) -> MysteryScenario:
        print("  [DEMO] Using pre-structured sample data")
        print("  (Production: Claude AI extracts this from raw text)")

        characters = [
            Character(
                name="Lord Ashworth",
                role="victim",
                is_culprit=False,
                occupation="Aristocrat and landowner",
                personality_traits=["paranoid", "generous", "private"],
                speech_style="Formal Victorian; short, declarative sentences",
                interrogation_behavior="N/A — victim",
                what_they_hide="The full extent of the foundation's beneficiaries",
                knowledge_about_crime="N/A — victim",
                relationship_to_victim=None,
                faction="Ashworth Household",
                cultural_position="Patriarch; his death destabilizes the household",
                age=67,
                archetype="aristocrat"
            ),
            Character(
                name="Dr. Richard Sterling",
                role="suspect",
                is_culprit=True,
                occupation="Physician and forensic science enthusiast",
                personality_traits=["methodical", "charming", "jealous"],
                speech_style="Precise and clinical; deflects with medical terminology when nervous",
                interrogation_behavior=(
                    "Cooperative and disarming initially; becomes evasive when asked "
                    "about his movements after 11 PM. Volunteers information about other "
                    "suspects to redirect attention."
                ),
                what_they_hide=(
                    "Was in the study corridor at 1 AM. Has been losing hospital patronage "
                    "to Lord Ashworth's favored rival. Had access to chloral hydrate."
                ),
                knowledge_about_crime="Claims he was in the guest bedroom all night",
                knowledge_that_helps_solve=[
                    "His forensic texts on lock manipulation are in the guest room",
                    "He prescribed chloral hydrate to Lord Ashworth previously"
                ],
                relationship_to_victim="Physician and long-time friend",
                motive=(
                    "Lord Ashworth's new will establishes a medical research foundation "
                    "benefiting Sterling's chief rival. Sterling's death prevents its execution."
                ),
                alibi="Claims he was in his guest bedroom from 10 PM onwards — unverifiable",
                faction="Medical Academy",
                cultural_position="Respected physician; outsider to the household",
                age=44,
                archetype="professional_rival"
            ),
            Character(
                name="Lady Margaret Ashworth",
                role="suspect",
                is_culprit=False,
                occupation="Aristocrat",
                personality_traits=["composed", "bitter", "calculating"],
                speech_style="Measured Victorian aristocratic; uses understatement",
                interrogation_behavior=(
                    "Answers questions but offers nothing voluntarily. "
                    "Subtly steers suspicion toward Miss Hart."
                ),
                what_they_hide=(
                    "Has known about the will change for two weeks and consulted "
                    "a solicitor about contesting it."
                ),
                knowledge_about_crime="Claims she was in her chambers all night",
                knowledge_that_helps_solve=[
                    "Lord Ashworth told her he was having nightcaps alone in the study",
                    "She heard movement in the corridor around 1 AM but dismissed it"
                ],
                relationship_to_victim="Wife of 30 years",
                motive="Disinherited by the new will; stood to lose her entire lifestyle",
                alibi="Claims she was in her chambers",
                faction="Ashworth Household",
                cultural_position="Lady of the house; outranks investigators socially",
                age=61,
                archetype="spouse"
            ),
            Character(
                name="Miss Elizabeth Hart",
                role="suspect",
                is_culprit=False,
                occupation="Artist, London",
                personality_traits=["impulsive", "honest", "anxious"],
                speech_style="Blurts information without guile; rambles when nervous",
                interrogation_behavior=(
                    "Immediately confesses everything she knows, including things "
                    "that make herself look suspicious. Volunteers the will information unprompted."
                ),
                what_they_hide="Owes significant debts in London; the inheritance was her only solution",
                knowledge_about_crime="Was in the library until midnight, then went to bed",
                knowledge_that_helps_solve=[
                    "Saw the will documents on Lord Ashworth's desk the afternoon before the murder",
                    "Noticed Dr. Sterling's medical bag was open on the sideboard at dinner"
                ],
                relationship_to_victim="Niece",
                motive="Discovered she was cut from the will; has pressing debts",
                alibi="Reading in the library until midnight",
                faction="Ashworth Household",
                cultural_position="Dependent niece; limited social standing",
                age=31,
                archetype="relative"
            ),
            Character(
                name="Jenkins",
                role="witness",
                is_culprit=False,
                occupation="Butler",
                personality_traits=["loyal", "observant", "deferential"],
                speech_style="Formal, economical; only answers what is asked",
                interrogation_behavior=(
                    "Cooperative but initially omits the corridor sighting from loyalty to "
                    "the household. Reveals it on direct second questioning once he understands "
                    "the seriousness."
                ),
                what_they_hide=(
                    "Saw Dr. Sterling in the study wing corridor at 1 AM but initially said "
                    "nothing, not wanting to implicate a guest."
                ),
                knowledge_about_crime="On duty in the household all night; discovered the body",
                knowledge_that_helps_solve=[
                    "Saw Dr. Sterling near the study at 1 AM (requires direct second questioning)",
                    "The letter opener was normally kept locked in Lord Ashworth's desk"
                ],
                relationship_to_victim="Loyal servant of 25 years",
                alibi="On duty throughout",
                faction="Ashworth Household",
                cultural_position="Head of domestic staff; privy to household secrets",
                age=62,
                archetype="butler"
            ),
            Character(
                name="Inspector Morrison",
                role="investigator",
                is_culprit=False,
                occupation="Scotland Yard Inspector",
                personality_traits=["methodical", "skeptical", "dry"],
                speech_style="Direct questions; long silences to make suspects uncomfortable",
                interrogation_behavior="N/A — investigator",
                what_they_hide="Nothing relevant",
                knowledge_about_crime="Arrived after discovery; leads the investigation",
                faction="Scotland Yard",
                cultural_position="Legal authority; must navigate class barriers",
                age=52,
                archetype="investigator"
            )
        ]

        physical_clues = [
            PhysicalClue(
                id="clue_001",
                name="Letter opener (murder weapon)",
                description="Ornate antique letter opener, wiped clean of fingerprints",
                category="physical",
                location="Victim's chest at discovery",
                what_it_proves="Premeditated murder — deliberate cleaning indicates planning",
                relevance="critical",
                analysis_required=False
            ),
            PhysicalClue(
                id="clue_002",
                name="Locked door",
                description="Study door locked from inside; no key found on victim",
                category="physical",
                location="Study entrance",
                what_it_proves="Appears to prove no one entered — actually staged",
                relevance="red_herring",
                analysis_required=True,
                analysis_method="Physical demonstration with string",
                false_conclusion="The room was sealed — no one could have entered or exited",
                why_misleading="The lock mechanism can be manipulated from outside using string through the keyhole",
                what_disproves_it="clue_004"
            ),
            PhysicalClue(
                id="clue_003",
                name="Sealed windows",
                description="All study windows latched from inside",
                category="physical",
                location="Study windows",
                what_it_proves="Eliminates window as exit route",
                relevance="red_herring",
                analysis_required=False,
                false_conclusion="No one could have escaped through the windows",
                why_misleading="The killer did not use the windows — they used the door via string trick",
                what_disproves_it="clue_004"
            ),
            PhysicalClue(
                id="clue_004",
                name="String in the keyhole",
                description="Fine thread threaded through the keyhole, barely visible without close examination",
                category="physical",
                location="Study door keyhole",
                what_it_proves="The locked room was staged — someone locked the door from outside",
                relevance="critical",
                analysis_required=True,
                analysis_method="Physical examination of keyhole with magnifying glass"
            ),
            PhysicalClue(
                id="clue_005",
                name="Jacket fibers in keyhole",
                description="Dark wool fibers caught in the keyhole mechanism",
                category="physical",
                location="Study door keyhole",
                what_it_proves="Someone used a tool through the keyhole; fibers match Dr. Sterling's jacket",
                relevance="critical",
                analysis_required=True,
                analysis_method="Fiber comparison with suspects' clothing at Scotland Yard laboratory"
            ),
            PhysicalClue(
                id="clue_006",
                name="Sedative traces (toxicology)",
                description="Chemical traces of chloral hydrate in Lord Ashworth's bloodstream",
                category="chemical",
                location="Victim (post-mortem toxicology)",
                what_it_proves=(
                    "Victim was sedated before being stabbed. Administering chloral hydrate "
                    "requires medical knowledge and access to the drug."
                ),
                relevance="critical",
                analysis_required=True,
                analysis_method="Toxicological analysis at Scotland Yard laboratory"
            ),
            PhysicalClue(
                id="clue_007",
                name="Forensic science texts (Sterling's room)",
                description="Books on forensic lock manipulation techniques in Dr. Sterling's guest room",
                category="documentary",
                location="Dr. Sterling's guest room",
                what_it_proves="Sterling had specific knowledge of the string-through-keyhole technique",
                relevance="supporting",
                analysis_required=False
            ),
            PhysicalClue(
                id="clue_008",
                name="Changed will document",
                description="Legal document cutting all family members; establishes the medical research foundation",
                category="documentary",
                location="Lord Ashworth's desk (within sealed study)",
                what_it_proves=(
                    "Motive for family members AND for Sterling, who benefits professionally "
                    "from preventing the foundation."
                ),
                relevance="supporting",
                analysis_required=False
            )
        ]

        testimonial_revelations = [
            TestimonialRevelation(
                id="testimony_001",
                providing_character="Jenkins",
                statement="I... did see Dr. Sterling in the corridor near the study. It was around 1 in the morning. I thought nothing of it at the time.",
                what_it_reveals="Directly contradicts Sterling's alibi of being in his room all night",
                relevance="critical",
                trigger_condition="Ask Jenkins directly on second questioning after other suspects have been interviewed"
            ),
            TestimonialRevelation(
                id="testimony_002",
                providing_character="Miss Elizabeth Hart",
                statement="Uncle's will — yes, I saw it on his desk yesterday afternoon. He was leaving everything to fund that dreadful research foundation. Nothing to family at all.",
                what_it_reveals="Establishes the will change and who knew about it",
                relevance="supporting",
                trigger_condition="Ask Miss Hart if she had any recent conversations with Lord Ashworth"
            ),
            TestimonialRevelation(
                id="testimony_003",
                providing_character="Lady Margaret Ashworth",
                statement="My husband had grown impossible. He had become utterly consumed by his charitable obsessions.",
                what_it_reveals="Lady Ashworth knew about the will change and resented it",
                relevance="red_herring",
                trigger_condition="Ask Lady Ashworth about her husband's recent behavior",
                false_conclusion="Lady Ashworth's bitterness gives her a strong motive for murder",
                why_misleading="Her statement sounds like a confession of resentment but she had no means or opportunity",
                what_disproves_it="clue_005"
            ),
            TestimonialRevelation(
                id="testimony_004",
                providing_character="Dr. Richard Sterling",
                statement="I prescribed Lord Ashworth a mild sedative some months ago for his nerves. Chloral hydrate, yes. I had some remaining in my medical bag.",
                what_it_reveals="Sterling had both knowledge of and access to the sedative found in the victim",
                relevance="critical",
                trigger_condition="Confront Sterling with the toxicology results showing chloral hydrate"
            ),
            TestimonialRevelation(
                id="testimony_005",
                providing_character="Miss Elizabeth Hart",
                statement="I noticed Dr. Sterling's medical bag was open on the sideboard at dinner. I thought it rather odd at the time.",
                what_it_reveals="Sterling's bag was accessible during the evening, consistent with him preparing the sedative",
                relevance="supporting",
                trigger_condition="Ask Miss Hart if she noticed anything unusual about the dinner"
            )
        ]

        factions = [
            Faction(
                name="Ashworth Household",
                description="The aristocratic family and domestic staff of Ashworth Manor",
                goal="Preserve the Ashworth estate and family standing",
                members=["Lord Ashworth", "Lady Margaret Ashworth", "Miss Elizabeth Hart", "Jenkins"],
                tension_with=["Medical Academy", "Scotland Yard"]
            ),
            Faction(
                name="Medical Academy",
                description="The London medical and research establishment",
                goal="Advance medical research; compete for patronage and funding",
                members=["Dr. Richard Sterling"],
                tension_with=["Ashworth Household"]
            ),
            Faction(
                name="Scotland Yard",
                description="Metropolitan Police investigative authority",
                goal="Solve the crime despite class barriers",
                members=["Inspector Morrison"],
                tension_with=["Ashworth Household"]
            )
        ]

        timeline = [
            TimelineEvent(sequence=1, time="3:00 PM (day before)", event="Miss Hart accidentally sees the will documents on Lord Ashworth's desk", participant="Miss Elizabeth Hart", visible_to_players=True),
            TimelineEvent(sequence=2, time="7:00 PM", event="Dr. Sterling observes Lord Ashworth's evening routine and accesses his medical bag on the sideboard", participant="Dr. Richard Sterling", visible_to_players=False),
            TimelineEvent(sequence=3, time="10:30 PM", event="Sterling slips chloral hydrate into Lord Ashworth's nightcap", participant="Dr. Richard Sterling", visible_to_players=False),
            TimelineEvent(sequence=4, time="11:15 PM", event="Lord Ashworth loses consciousness in his study", participant="Lord Ashworth", visible_to_players=False),
            TimelineEvent(sequence=5, time="~1:00 AM", event="Sterling enters the study corridor; observed by Jenkins", participant="Dr. Richard Sterling", visible_to_players=True),
            TimelineEvent(sequence=6, time="1:05 AM", event="Sterling stabs Lord Ashworth with the letter opener and wipes it clean", participant="Dr. Richard Sterling", visible_to_players=False),
            TimelineEvent(sequence=7, time="1:10 AM", event="Sterling exits, uses pre-threaded string to lock door from outside", participant="Dr. Richard Sterling", visible_to_players=False),
            TimelineEvent(sequence=8, time="8:17 AM", event="Jenkins discovers the body when delivering morning tea", participant="Jenkins", visible_to_players=True),
        ]

        solution_steps = [
            SolutionStep(
                step_number=1,
                clue_ids=["clue_004", "clue_005"],
                logical_inference="The string and fiber evidence prove the locked room was staged from outside",
                conclusion="The locked room is not an impossibility — someone locked it from outside"
            ),
            SolutionStep(
                step_number=2,
                clue_ids=["clue_006", "testimony_004"],
                logical_inference="Chloral hydrate was used; only Sterling had medical knowledge and drug access",
                conclusion="The killer had medical training and access to prescription sedatives"
            ),
            SolutionStep(
                step_number=3,
                clue_ids=["testimony_001", "clue_007"],
                logical_inference="Sterling was near the study at 1 AM (contradicting his alibi) and had knowledge of forensic lock techniques",
                conclusion="Sterling's alibi is broken and he possessed the specific knowledge required"
            ),
            SolutionStep(
                step_number=4,
                clue_ids=["clue_008"],
                logical_inference="Sterling's motive (preventing the medical foundation) is distinct from family motives — and more specific",
                conclusion="Sterling is the only character with means, opportunity, and specific motive"
            )
        ]

        return MysteryScenario(
            scenario_id=str(uuid.uuid4()),
            title=metadata.get('title', 'The Locked Room Mystery'),
            source_url=metadata.get('source_url', 'demo://sample-mystery'),
            source_type='novel',
            full_text=raw_text[:500] + "...",
            world_era="victorian",
            world_specific_period="Victorian England, 1890s",
            world_tech_level="industrial",
            world_cultural_context=(
                "Victorian class hierarchy. The butler defers to aristocracy. "
                "Physicians occupy a respected professional class. Women have limited "
                "investigative authority. Scotland Yard is the forensic authority."
            ),
            world_physics_constraints=[
                "No DNA analysis — fiber and chemical evidence only",
                "No electronic records or surveillance",
                "Forensic laboratory analysis requires sending samples to Scotland Yard"
            ],
            world_flavor_tags=["victorian", "locked_room", "cozy", "manor_house"],
            crime_type="murder",
            mystery_type="locked_room",
            secondary_tags=["cozy", "professional_rivalry"],
            victim_identity="Lord Ashworth, a wealthy Victorian aristocrat",
            what_happened=(
                "Lord Ashworth was sedated with chloral hydrate and stabbed with his own "
                "letter opener. The killer staged the room to appear locked from inside."
            ),
            how_it_happened=(
                "Sterling administered the sedative earlier in the evening, waited for "
                "Ashworth to lose consciousness, then committed the murder and staged the "
                "locked-room illusion using a string threaded through the keyhole."
            ),
            discovery_scenario=(
                "Butler Jenkins found the body at 8:17 AM when delivering morning tea. "
                "The study door was locked from inside with no apparent means of entry or exit."
            ),
            surface_observations=[
                "The study door is locked from the inside",
                "All windows are sealed from inside",
                "The victim was stabbed with his own letter opener",
                "The letter opener has been wiped clean of fingerprints"
            ],
            hidden_details=[
                "Chemical traces of sedative in the victim's bloodstream",
                "String thread in the keyhole mechanism",
                "Wool fibers on the keyhole matching a specific jacket",
                "Dr. Sterling was seen in the study corridor at 1 AM"
            ],
            stakes="personal",
            characters=characters,
            physical_clues=physical_clues,
            testimonial_revelations=testimonial_revelations,
            factions=factions,
            timeline=timeline,
            solution_steps=solution_steps,
            culprit_name="Dr. Richard Sterling",
            solution_method=(
                "Administered chloral hydrate in Lord Ashworth's nightcap, waited for unconsciousness, "
                "stabbed him with the letter opener, wiped it clean, then locked the door from outside "
                "using a string pre-threaded through the keyhole."
            ),
            solution_motive=(
                "Lord Ashworth's new will established a medical research foundation that would benefit "
                "Sterling's chief rival. Preventing the will's execution was the only way Sterling could "
                "stop his rival's ascendancy."
            ),
            how_to_deduce=(
                "Step 1: clue_004 and clue_005 (string and fibers) disprove the locked-room impossibility. "
                "Step 2: clue_006 and testimony_004 establish that only Sterling had means for the sedation. "
                "Step 3: testimony_001 breaks Sterling's alibi; clue_007 shows he had forensic knowledge. "
                "Step 4: clue_008 shows Sterling's motive is uniquely specific — not inheritance, but "
                "professional rivalry through the foundation."
            ),
            plot_summary=(
                "Lord Ashworth is found dead in his locked study. Inspector Morrison uncovers that the "
                "locked room was staged using a string through the keyhole. Dr. Sterling, Ashworth's "
                "physician, committed the murder to prevent a will change that would fund his professional "
                "rival's research. The case is cracked by fiber analysis, toxicology, and a reluctant "
                "butler's belated testimony."
            ),
            author=metadata.get('author', 'A. Sample Author'),
            publication_year=1895,
            license_type='public_domain'
        )


# ============================================================================
# DATABASE (simplified — mirrors production)
# ============================================================================

class MysteryDatabase:
    def __init__(self, storage_path: str = "./mystery_database"):
        self.storage_path = storage_path
        os.makedirs(f"{storage_path}/scenarios", exist_ok=True)
        os.makedirs(f"{storage_path}/generated", exist_ok=True)
        self.index_file = f"{storage_path}/index.json"
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)

    def save_scenario(self, scenario: MysteryScenario) -> str:
        scenario_file = f"{self.storage_path}/scenarios/{scenario.scenario_id}.json"
        with open(scenario_file, 'w') as f:
            json.dump(asdict(scenario), f, indent=2)
        self._update_index(scenario)
        # Also save with slug name for easy validator access
        slug = re.sub(r'[^a-z0-9]+', '_', scenario.title.lower()).strip('_')
        slug_file = f"{self.storage_path}/scenarios/{slug}.json"
        with open(slug_file, 'w') as f:
            json.dump(asdict(scenario), f, indent=2)
        return scenario.scenario_id

    def _update_index(self, scenario: MysteryScenario):
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        entry = {
            'scenario_id': scenario.scenario_id,
            'title': scenario.title,
            'crime_type': scenario.crime_type,
            'mystery_type': scenario.mystery_type,
            'stakes': scenario.stakes,
            'world_era': scenario.world_era,
            'world_tech_level': scenario.world_tech_level,
            'world_flavor_tags': scenario.world_flavor_tags,
            'author': scenario.author,
            'character_count': len(scenario.characters),
            'physical_clue_count': len(scenario.physical_clues),
            'testimonial_count': len(scenario.testimonial_revelations),
            'faction_count': len(scenario.factions)
        }
        index = [e for e in index if e.get('scenario_id') != scenario.scenario_id]
        index.append(entry)
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)
        print(f"\n  Saved: {scenario.title}")
        print(f"    Characters:   {len(scenario.characters)}")
        print(f"    Phys. clues:  {len(scenario.physical_clues)}")
        print(f"    Testimonials: {len(scenario.testimonial_revelations)}")
        print(f"    Factions:     {len(scenario.factions)}")


# ============================================================================
# DEMO PIPELINE
# ============================================================================

def run_demo_pipeline():
    print("=" * 70)
    print("MYSTERY DATABASE PIPELINE — DEMO MODE")
    print("=" * 70)
    print()
    print("Pre-structured sample data. No API key required.")
    print()

    processor = MockMysteryProcessor()
    database = MysteryDatabase()

    metadata = {
        'title': 'The Locked Room Mystery',
        'author': 'A. Sample Author',
        'publication_year': 1895,
        'source_url': 'demo://sample-mystery'
    }

    print("STEP 1: Source Text")
    print("-" * 70)
    print(f"Title:  {metadata['title']}  |  Period: Victorian England 1890s")
    print()

    print("STEP 2: Extraction")
    print("-" * 70)
    scenario = processor.process_mystery(SAMPLE_MYSTERY_TEXT, metadata)
    print()

    print("STEP 3: Save")
    print("-" * 70)
    scenario_id = database.save_scenario(scenario)
    print()

    print("STEP 4: Schema Walkthrough")
    print("-" * 70)

    print("\nWORLD CONTEXT:")
    print(f"  era:         {scenario.world_era}")
    print(f"  tech_level:  {scenario.world_tech_level}")
    print(f"  flavor:      {scenario.world_flavor_tags}")
    print(f"  constraints: {scenario.world_physics_constraints[0]}")

    print("\nCRIME:")
    print(f"  crime_type:   {scenario.crime_type}")
    print(f"  mystery_type: {scenario.mystery_type}")
    print(f"  stakes:       {scenario.stakes}")
    print(f"  surface obs:  {len(scenario.surface_observations)} (shown at game start)")
    print(f"  hidden:       {len(scenario.hidden_details)} (earned through play)")

    print("\nCHARACTER (Dr. Sterling — culprit):")
    sterling = next(c for c in scenario.characters if c.is_culprit)
    print(f"  is_culprit:            {sterling.is_culprit}")
    print(f"  interrogation_behavior: {sterling.interrogation_behavior[:80]}...")
    print(f"  what_they_hide:        {sterling.what_they_hide[:80]}...")
    print(f"  knowledge_about_crime: {sterling.knowledge_about_crime}")

    print("\nPHYSICAL CLUES:")
    for c in scenario.physical_clues:
        rh = " [RED HERRING]" if c.relevance == "red_herring" else ""
        print(f"  {c.id}: {c.name} ({c.category}, {c.relevance}){rh}")

    print("\nTESTIMONIAL REVELATIONS:")
    for t in scenario.testimonial_revelations:
        print(f"  {t.id}: {t.providing_character} — trigger: {t.trigger_condition[:60]}...")

    print("\nSOLUTION STEPS:")
    for s in scenario.solution_steps:
        print(f"  Step {s.step_number}: {s.clue_ids} → {s.conclusion[:60]}...")

    print()
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print()
    print("Files created:")
    print(f"  mystery_database/scenarios/{scenario_id}.json  (UUID)")
    print(f"  mystery_database/scenarios/the_locked_room_mystery.json  (slug)")
    print()
    print("Next steps:")
    print("  python gameplay_validator.py   — validate this mystery")
    print("  python mystery_generator.py    — generate from a test query")
    print("  cat test_queries/README.md     — see the six test scenarios")
    print()


if __name__ == "__main__":
    run_demo_pipeline()
