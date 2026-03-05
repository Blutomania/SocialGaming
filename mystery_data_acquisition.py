"""
Choose Your Mystery - Data Acquisition Pipeline
================================================

Acquires public domain mystery content from Project Gutenberg, uses Claude AI
to extract structured data, and stores mysteries in a searchable database.

For schema field documentation, see MYSTERY_EXTRACTION_REQUIREMENTS.md.

Usage
-----
    export ANTHROPIC_API_KEY=your-key
    python mystery_data_acquisition.py

Requirements
------------
    pip install requests beautifulsoup4 anthropic python-dotenv
"""

import os
import re
import json
import time
import uuid
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# DATA MODELS
# See MYSTERY_EXTRACTION_REQUIREMENTS.md for full field documentation.
# ============================================================================

@dataclass
class PhysicalClue:
    """
    Evidence discovered by examining a location.
    category must be valid for the world's tech_level.
    See MYSTERY_EXTRACTION_REQUIREMENTS.md for the tech_level→category matrix.
    """
    id: str                              # clue_001, clue_002, ...
    name: str
    description: str
    category: str                        # physical|biological|digital|chemical|documentary|environmental
    location: str
    what_it_proves: str
    relevance: str                       # critical|supporting|red_herring
    analysis_required: bool = False
    analysis_method: Optional[str] = None
    # Red herring fields (populate only when relevance == 'red_herring')
    false_conclusion: Optional[str] = None
    why_misleading: Optional[str] = None
    what_disproves_it: Optional[str] = None


@dataclass
class TestimonialRevelation:
    """
    Information extracted by interrogating an NPC.
    trigger_condition tells the game engine what question unlocks this.
    """
    id: str                              # testimony_001, testimony_002, ...
    providing_character: str
    statement: str
    what_it_reveals: str
    relevance: str                       # critical|supporting|red_herring
    trigger_condition: str
    # Red herring fields
    false_conclusion: Optional[str] = None
    why_misleading: Optional[str] = None
    what_disproves_it: Optional[str] = None


@dataclass
class Character:
    """
    Character designed for interrogation gameplay.
    Exactly one character per mystery has is_culprit=True.
    """
    name: str
    role: str                            # victim|suspect|investigator|witness|bystander
    is_culprit: bool
    occupation: str
    personality_traits: List[str]
    speech_style: str
    interrogation_behavior: str
    what_they_hide: str
    knowledge_about_crime: str           # Their account of their own movements
    knowledge_that_helps_solve: List[str] = field(default_factory=list)  # Clue atoms players can extract
    relationship_to_victim: Optional[str] = None
    motive: Optional[str] = None
    alibi: Optional[str] = None
    faction: Optional[str] = None
    cultural_position: Optional[str] = None
    age: Optional[int] = None
    archetype: Optional[str] = None


@dataclass
class TimelineEvent:
    """Ground-truth chronology. visible_to_players=False means hidden truth."""
    sequence: int
    time: str
    event: str
    participant: str
    visible_to_players: bool


@dataclass
class SolutionStep:
    """One step in the ordered logical chain from clues to culprit."""
    step_number: int
    clue_ids: List[str]                  # clue_XXX or testimony_XXX IDs
    logical_inference: str
    conclusion: str


@dataclass
class Faction:
    """Power structure or group. Critical for political/corporate mysteries."""
    name: str
    description: str
    goal: str
    members: List[str] = field(default_factory=list)
    tension_with: List[str] = field(default_factory=list)


@dataclass
class MysteryScenario:
    """
    Complete mystery scenario — the canonical unit of storage.

    World context fields (world_*) serve RAG retrieval and content validation.
    They are NOT presented to players — the world is established by the user prompt.
    """
    # Identity
    scenario_id: str                     # UUID
    title: str
    source_url: str
    source_type: str                     # novel|screenplay|court_transcript|generated

    # World context (for RAG retrieval and validation)
    world_era: str                       # ancient|medieval|early_modern|victorian|modern|near_future|far_future|alternate_history
    world_specific_period: str
    world_tech_level: str                # pre_industrial|industrial|contemporary|advanced|sci_fi
    world_cultural_context: str
    world_physics_constraints: List[str] = field(default_factory=list)
    world_flavor_tags: List[str] = field(default_factory=list)

    # Crime
    crime_type: str = ""                 # murder|theft|forgery|sabotage|identity_theft|kidnapping|espionage|fraud|disappearance
    mystery_type: str = ""              # whodunit|locked_room|cozy|procedural|espionage|heist
    secondary_tags: List[str] = field(default_factory=list)
    victim_identity: str = ""
    what_happened: str = ""
    how_it_happened: str = ""
    discovery_scenario: str = ""
    surface_observations: List[str] = field(default_factory=list)
    hidden_details: List[str] = field(default_factory=list)
    stakes: str = "personal"            # personal|political|corporate|existential

    # Content
    characters: List[Character] = field(default_factory=list)
    physical_clues: List[PhysicalClue] = field(default_factory=list)
    testimonial_revelations: List[TestimonialRevelation] = field(default_factory=list)
    factions: List[Faction] = field(default_factory=list)

    # Solution
    timeline: List[TimelineEvent] = field(default_factory=list)
    solution_steps: List[SolutionStep] = field(default_factory=list)
    culprit_name: str = ""
    solution_method: str = ""
    solution_motive: str = ""
    how_to_deduce: str = ""

    # Source metadata
    full_text: str = ""
    plot_summary: str = ""
    author: str = "Unknown"
    publication_year: Optional[int] = None
    license_type: str = "unknown"
    processed_date: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# TECH LEVEL → VALID EVIDENCE CATEGORIES
# ============================================================================

VALID_CATEGORIES = {
    'pre_industrial': {'physical', 'chemical', 'documentary', 'testimonial', 'environmental'},
    'industrial':     {'physical', 'chemical', 'documentary', 'testimonial', 'environmental'},
    'contemporary':   {'physical', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'},
    'advanced':       {'physical', 'biological', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'},
    'sci_fi':         {'physical', 'biological', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'},
}


# ============================================================================
# DATA ACQUISITION — PROJECT GUTENBERG
# ============================================================================

class GutenbergScraper:
    """Scrape public domain mysteries from Project Gutenberg."""

    BASE_URL = "https://www.gutenberg.org"
    SEARCH_URL = f"{BASE_URL}/ebooks/search/"
    REQUEST_DELAY = 2.0  # seconds between requests

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ChooseYourMystery-DataAcquisition/1.0 (Research Project)'
        })

    def search_mysteries(self, query: str = "detective mystery", limit: int = 10) -> List[Dict]:
        """Search for mystery books. Separate from download for rate limiting."""
        params = {'query': query, 'submit_search': 'Go!'}
        response = self.session.get(self.SEARCH_URL, params=params)
        soup = BeautifulSoup(response.content, 'html.parser')

        books = []
        for item in soup.select('.booklink')[:limit]:
            book_id = item.get('href', '').split('/')[-1]
            title = item.get_text(strip=True)
            if book_id.isdigit():
                books.append({
                    'id': book_id,
                    'title': title,
                    'url': f"{self.BASE_URL}/ebooks/{book_id}"
                })

        time.sleep(self.REQUEST_DELAY)
        return books

    def download_book_text(self, book_id: str) -> Optional[Dict]:
        """Download full text and metadata. Tries multiple plain text formats."""
        metadata_url = f"{self.BASE_URL}/ebooks/{book_id}"
        response = self.session.get(metadata_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        time.sleep(self.REQUEST_DELAY)

        metadata = {
            'id': book_id,
            'title': self._extract_title(soup),
            'author': self._extract_author(soup),
            'publication_year': self._extract_year(soup),
        }

        for text_url in [
            f"{self.BASE_URL}/files/{book_id}/{book_id}-0.txt",
            f"{self.BASE_URL}/files/{book_id}/{book_id}.txt",
        ]:
            try:
                text_response = self.session.get(text_url)
                text_response.raise_for_status()
                metadata['full_text'] = text_response.text
                metadata['source_url'] = text_url
                time.sleep(self.REQUEST_DELAY)
                return metadata
            except requests.RequestException:
                time.sleep(self.REQUEST_DELAY)
                continue

        print(f"  Failed to download book {book_id}")
        return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        elem = soup.select_one('h1[itemprop="name"]')
        return elem.get_text(strip=True) if elem else "Unknown"

    def _extract_author(self, soup: BeautifulSoup) -> str:
        elem = soup.select_one('a[itemprop="creator"]')
        return elem.get_text(strip=True) if elem else "Unknown"

    def _extract_year(self, soup: BeautifulSoup) -> Optional[int]:
        match = re.search(r'\b(1[789]\d{2}|20\d{2})\b', soup.get_text())
        return int(match.group(1)) if match else None


# ============================================================================
# DATA PROCESSING — AI-POWERED EXTRACTION
# ============================================================================

class MysteryProcessor:
    """Process raw mystery text into structured MysteryScenario using Claude."""

    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def process_mystery(self, raw_text: str, metadata: Dict) -> MysteryScenario:
        """
        Four-pass extraction:
          1. World context + crime classification
          2. Characters (with interrogation mechanics fields)
          3. Physical clues (scene investigation)
          4. Testimonials, timeline, solution
        """
        print("  Pass 1: World context and crime classification...")
        world_crime = self._extract_world_and_crime(raw_text)

        print("  Pass 2: Characters...")
        characters = self._extract_characters(raw_text, world_crime)

        print("  Pass 3: Physical clues...")
        physical_clues = self._extract_physical_clues(raw_text, world_crime)

        print("  Pass 4: Testimonials, timeline, solution...")
        solution_data = self._extract_solution_data(raw_text, characters, physical_clues)

        scenario = MysteryScenario(
            scenario_id=str(uuid.uuid4()),
            title=metadata.get('title', 'Unknown'),
            source_url=metadata.get('source_url', ''),
            source_type='novel',
            full_text=raw_text[:10000],
            # World
            world_era=world_crime.get('world_era', 'unknown'),
            world_specific_period=world_crime.get('world_specific_period', 'unknown'),
            world_tech_level=world_crime.get('world_tech_level', 'unknown'),
            world_cultural_context=world_crime.get('world_cultural_context', ''),
            world_physics_constraints=world_crime.get('world_physics_constraints', []),
            world_flavor_tags=world_crime.get('world_flavor_tags', []),
            # Crime
            crime_type=world_crime.get('crime_type', 'unknown'),
            mystery_type=world_crime.get('mystery_type', 'whodunit'),
            secondary_tags=world_crime.get('secondary_tags', []),
            victim_identity=world_crime.get('victim_identity', ''),
            what_happened=world_crime.get('what_happened', ''),
            how_it_happened=world_crime.get('how_it_happened', ''),
            discovery_scenario=world_crime.get('discovery_scenario', ''),
            surface_observations=world_crime.get('surface_observations', []),
            hidden_details=world_crime.get('hidden_details', []),
            stakes=world_crime.get('stakes', 'personal'),
            # Content
            characters=characters,
            physical_clues=physical_clues,
            testimonial_revelations=solution_data.get('testimonials', []),
            factions=solution_data.get('factions', []),
            # Solution
            timeline=solution_data.get('timeline', []),
            solution_steps=solution_data.get('solution_steps', []),
            culprit_name=solution_data.get('culprit_name', ''),
            solution_method=solution_data.get('method', ''),
            solution_motive=solution_data.get('motive', ''),
            how_to_deduce=solution_data.get('how_to_deduce', ''),
            plot_summary=solution_data.get('plot_summary', ''),
            # Metadata
            author=metadata.get('author', 'Unknown'),
            publication_year=metadata.get('publication_year'),
            license_type='public_domain'
        )

        return scenario

    def _extract_world_and_crime(self, text: str) -> Dict:
        prompt = f"""Analyze this mystery excerpt. Extract world context and crime details.

{text[:4000]}

Respond with JSON only:
{{
  "world_era": "ancient|medieval|early_modern|victorian|modern|near_future|far_future|alternate_history",
  "world_specific_period": "e.g. Victorian England 1890s",
  "world_tech_level": "pre_industrial|industrial|contemporary|advanced|sci_fi",
  "world_cultural_context": "Key social norms affecting the investigation",
  "world_physics_constraints": ["What is impossible in this setting"],
  "world_flavor_tags": ["locked_room","cozy","noir","gothic","sci-fi","steampunk","historical","etc."],
  "crime_type": "murder|theft|forgery|sabotage|identity_theft|kidnapping|espionage|fraud|disappearance",
  "mystery_type": "whodunit|locked_room|cozy|procedural|espionage|heist",
  "secondary_tags": ["additional flavor tags"],
  "victim_identity": "Who was victimized and their significance",
  "what_happened": "Complete description of the crime",
  "how_it_happened": "Method used",
  "discovery_scenario": "How and when discovered; what players are told at game start",
  "surface_observations": ["Visible immediately on arrival — no investigation needed"],
  "hidden_details": ["Require active investigation to uncover"],
  "stakes": "personal|political|corporate|existential"
}}"""

        return self._call_claude(prompt, max_tokens=1500, fallback={
            'world_era': 'unknown', 'world_specific_period': 'unknown',
            'world_tech_level': 'unknown', 'world_cultural_context': '',
            'world_physics_constraints': [], 'world_flavor_tags': [],
            'crime_type': 'unknown', 'mystery_type': 'whodunit',
            'secondary_tags': [], 'victim_identity': '',
            'what_happened': '', 'how_it_happened': '', 'discovery_scenario': '',
            'surface_observations': [], 'hidden_details': [], 'stakes': 'personal'
        })

    def _extract_characters(self, text: str, world_crime: Dict) -> List[Character]:
        tech_level = world_crime.get('world_tech_level', 'contemporary')

        prompt = f"""Extract 5-8 key characters from this mystery. World tech level: {tech_level}

{text[:6000]}

Exactly ONE character must have is_culprit=true.

Respond with a JSON array:
[{{
  "name": "Character name",
  "role": "victim|suspect|investigator|witness|bystander",
  "is_culprit": false,
  "occupation": "Setting-appropriate title",
  "personality_traits": ["trait1", "trait2"],
  "speech_style": "How they talk",
  "interrogation_behavior": "How they respond under questioning",
  "what_they_hide": "What they actively conceal (everyone hides something)",
  "relationship_to_victim": "Connection to victim",
  "motive": "Why they might be guilty (suspects only, null otherwise)",
  "alibi": "Their stated alibi",
  "knowledge_about_crime": "Their account of their own movements during the crime window",
  "knowledge_that_helps_solve": ["Clue atoms players can extract from this character"],
  "faction": "Which group they belong to",
  "cultural_position": "Their standing in this world",
  "age": 40,
  "archetype": "butler|spouse|rival|scientist|official|merchant|etc."
}}]"""

        data = self._call_claude(prompt, max_tokens=3000, fallback=[])
        if not isinstance(data, list):
            return []

        return [
            Character(
                name=c.get('name', 'Unknown'),
                role=c.get('role', 'bystander'),
                is_culprit=bool(c.get('is_culprit', False)),
                occupation=c.get('occupation', ''),
                personality_traits=c.get('personality_traits', []),
                speech_style=c.get('speech_style', ''),
                interrogation_behavior=c.get('interrogation_behavior', ''),
                what_they_hide=c.get('what_they_hide', ''),
                knowledge_about_crime=c.get('knowledge_about_crime', ''),
                knowledge_that_helps_solve=c.get('knowledge_that_helps_solve', []),
                relationship_to_victim=c.get('relationship_to_victim'),
                motive=c.get('motive'),
                alibi=c.get('alibi'),
                faction=c.get('faction'),
                cultural_position=c.get('cultural_position'),
                age=c.get('age'),
                archetype=c.get('archetype')
            )
            for c in data
        ]

    def _extract_physical_clues(self, text: str, world_crime: Dict) -> List[PhysicalClue]:
        tech_level = world_crime.get('world_tech_level', 'contemporary')
        valid_cats = list(VALID_CATEGORIES.get(tech_level, {'physical', 'testimonial', 'documentary'}))

        prompt = f"""Extract 5-8 physical clues from this mystery.
Tech level: {tech_level}
Valid categories for this tech level: {valid_cats}

{text[:6000]}

Respond with JSON array:
[{{
  "id": "clue_001",
  "name": "Short name",
  "description": "What it is",
  "category": "must be one of the valid categories above",
  "location": "Where found",
  "what_it_proves": "What investigators correctly conclude",
  "relevance": "critical|supporting|red_herring",
  "analysis_required": false,
  "analysis_method": "Tool/skill needed (null if self-evident)",
  "false_conclusion": "If red_herring: what it SEEMS to prove",
  "why_misleading": "If red_herring: why it points the wrong way",
  "what_disproves_it": "If red_herring: which other clue ID disproves it"
}}]"""

        data = self._call_claude(prompt, max_tokens=2500, fallback=[])
        if not isinstance(data, list):
            return []

        return [
            PhysicalClue(
                id=c.get('id', f'clue_{i:03d}'),
                name=c.get('name', ''),
                description=c.get('description', ''),
                category=c.get('category', 'physical'),
                location=c.get('location', ''),
                what_it_proves=c.get('what_it_proves', ''),
                relevance=c.get('relevance', 'supporting'),
                analysis_required=bool(c.get('analysis_required', False)),
                analysis_method=c.get('analysis_method'),
                false_conclusion=c.get('false_conclusion'),
                why_misleading=c.get('why_misleading'),
                what_disproves_it=c.get('what_disproves_it')
            )
            for i, c in enumerate(data)
        ]

    def _extract_solution_data(
        self,
        text: str,
        characters: List[Character],
        physical_clues: List[PhysicalClue]
    ) -> Dict:
        char_names = [c.name for c in characters]
        clue_ids = [c.id for c in physical_clues]

        prompt = f"""Extract testimonials, timeline, and solution from this mystery.

{text[:8000]}

Characters: {char_names}
Physical clue IDs already extracted: {clue_ids}

Respond with JSON:
{{
  "plot_summary": "3-5 sentence summary",
  "testimonials": [{{
    "id": "testimony_001",
    "providing_character": "Character name (must be in character list)",
    "statement": "What they say",
    "what_it_reveals": "What investigators conclude",
    "relevance": "critical|supporting|red_herring",
    "trigger_condition": "What question or action causes this revelation",
    "false_conclusion": "If red_herring: what it seems to prove",
    "why_misleading": "If red_herring: why misleading",
    "what_disproves_it": "If red_herring: which clue_ID or testimony_ID disproves it"
  }}],
  "factions": [{{
    "name": "Faction name",
    "description": "What this group is",
    "goal": "What they want",
    "members": ["character names"],
    "tension_with": ["other faction names"]
  }}],
  "timeline": [{{
    "sequence": 1,
    "time": "10:30 PM",
    "event": "What happened",
    "participant": "Who was involved",
    "visible_to_players": true
  }}],
  "solution_steps": [{{
    "step_number": 1,
    "clue_ids": ["clue_001", "testimony_001"],
    "logical_inference": "What the player must reason",
    "conclusion": "What this step proves"
  }}],
  "culprit_name": "Character name",
  "method": "How the crime was committed",
  "motive": "Why",
  "how_to_deduce": "Prose walkthrough of the full logical chain"
}}

If the solution is not in the excerpt, set culprit_name to "solution_not_available"."""

        data = self._call_claude(prompt, max_tokens=4000, fallback={
            'plot_summary': '', 'testimonials': [], 'factions': [],
            'timeline': [], 'solution_steps': [],
            'culprit_name': 'solution_not_available',
            'method': '', 'motive': '', 'how_to_deduce': ''
        })

        # Reconstruct nested dataclasses
        testimonials = [
            TestimonialRevelation(
                id=t.get('id', f'testimony_{i:03d}'),
                providing_character=t.get('providing_character', ''),
                statement=t.get('statement', ''),
                what_it_reveals=t.get('what_it_reveals', ''),
                relevance=t.get('relevance', 'supporting'),
                trigger_condition=t.get('trigger_condition', ''),
                false_conclusion=t.get('false_conclusion'),
                why_misleading=t.get('why_misleading'),
                what_disproves_it=t.get('what_disproves_it')
            )
            for i, t in enumerate(data.get('testimonials', []))
        ]

        factions = [
            Faction(
                name=f.get('name', ''),
                description=f.get('description', ''),
                goal=f.get('goal', ''),
                members=f.get('members', []),
                tension_with=f.get('tension_with', [])
            )
            for f in data.get('factions', [])
        ]

        timeline = [
            TimelineEvent(
                sequence=t.get('sequence', i + 1),
                time=t.get('time', ''),
                event=t.get('event', ''),
                participant=t.get('participant', ''),
                visible_to_players=bool(t.get('visible_to_players', True))
            )
            for i, t in enumerate(data.get('timeline', []))
        ]

        solution_steps = [
            SolutionStep(
                step_number=s.get('step_number', i + 1),
                clue_ids=s.get('clue_ids', []),
                logical_inference=s.get('logical_inference', ''),
                conclusion=s.get('conclusion', '')
            )
            for i, s in enumerate(data.get('solution_steps', []))
        ]

        return {
            'plot_summary': data.get('plot_summary', ''),
            'testimonials': testimonials,
            'factions': factions,
            'timeline': timeline,
            'solution_steps': solution_steps,
            'culprit_name': data.get('culprit_name', ''),
            'method': data.get('method', ''),
            'motive': data.get('motive', ''),
            'how_to_deduce': data.get('how_to_deduce', '')
        }

    def _call_claude(self, prompt: str, max_tokens: int, fallback):
        """Make a Claude API call and parse JSON response."""
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = message.content[0].text.strip()
            # Strip markdown code fences with regex (handles all variants)
            response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)
            response_text = re.sub(r'\n?```\s*$', '', response_text).strip()
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"  Warning: JSON parse error: {e}")
            return fallback
        except Exception as e:
            print(f"  Warning: Claude API error: {e}")
            return fallback


# ============================================================================
# DATA STORAGE
# ============================================================================

class MysteryDatabase:
    """
    JSON-based storage. Suitable for POC and up to ~1,000 mysteries.
    For production, migrate to PostgreSQL + pgvector (see mystery_database_plan.md).
    """

    def __init__(self, storage_path: str = "./mystery_database"):
        self.storage_path = storage_path
        os.makedirs(f"{storage_path}/scenarios", exist_ok=True)
        os.makedirs(f"{storage_path}/raw_texts", exist_ok=True)
        os.makedirs(f"{storage_path}/generated", exist_ok=True)

        self.index_file = f"{storage_path}/index.json"
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)

    def save_scenario(self, scenario: MysteryScenario) -> str:
        """Save scenario using UUID as filename. Returns scenario_id."""
        scenario_file = f"{self.storage_path}/scenarios/{scenario.scenario_id}.json"
        with open(scenario_file, 'w') as f:
            json.dump(asdict(scenario), f, indent=2)
        self._update_index(scenario)
        print(f"  Saved: {scenario.title} ({scenario.scenario_id})")
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

    def load_scenario(self, scenario_id: str) -> Optional[MysteryScenario]:
        """Load a full scenario, reconstructing all nested dataclasses."""
        scenario_file = f"{self.storage_path}/scenarios/{scenario_id}.json"
        if not os.path.exists(scenario_file):
            return None

        with open(scenario_file, 'r') as f:
            data = json.load(f)

        # Reconstruct nested dataclasses
        data['physical_clues'] = [PhysicalClue(**c) for c in data.get('physical_clues', [])]
        data['testimonial_revelations'] = [TestimonialRevelation(**t) for t in data.get('testimonial_revelations', [])]
        data['characters'] = [Character(**c) for c in data.get('characters', [])]
        data['factions'] = [Faction(**f) for f in data.get('factions', [])]
        data['timeline'] = [TimelineEvent(**t) for t in data.get('timeline', [])]
        data['solution_steps'] = [SolutionStep(**s) for s in data.get('solution_steps', [])]

        return MysteryScenario(**data)

    def search_scenarios(self, **criteria) -> List[Dict]:
        """
        Search the index. Criteria keys:
            crime_type, mystery_type, world_era, world_tech_level, stakes
        """
        with open(self.index_file, 'r') as f:
            index = json.load(f)

        results = []
        for entry in index:
            if all(entry.get(k) == v for k, v in criteria.items()):
                results.append(entry)
        return results

    def get_stats(self) -> Dict:
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        if not index:
            return {'total_mysteries': 0}
        return {
            'total_mysteries': len(index),
            'crime_types': list(set(m.get('crime_type', '?') for m in index)),
            'mystery_types': list(set(m.get('mystery_type', '?') for m in index)),
            'eras': list(set(m.get('world_era', '?') for m in index)),
            'total_characters': sum(m.get('character_count', 0) for m in index),
            'total_physical_clues': sum(m.get('physical_clue_count', 0) for m in index),
            'total_testimonials': sum(m.get('testimonial_count', 0) for m in index),
        }


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_acquisition_pipeline(num_books: int = 3, query: str = "sherlock holmes"):
    """
    Full pipeline: Acquire from Gutenberg → Process with Claude → Store.

    Args:
        num_books: How many books to process (start with 3-5)
        query:     Project Gutenberg search query
    """
    print("=== Choose Your Mystery — Data Acquisition Pipeline ===\n")

    scraper = GutenbergScraper()
    processor = MysteryProcessor()
    database = MysteryDatabase()

    print(f"Searching Gutenberg: '{query}' (limit {num_books})...")
    books = scraper.search_mysteries(query=query, limit=num_books)
    print(f"Found {len(books)} books\n")

    for i, book in enumerate(books, 1):
        print(f"[{i}/{len(books)}] {book['title']}")

        book_data = scraper.download_book_text(book['id'])
        if not book_data or not book_data.get('full_text'):
            print("  Download failed, skipping\n")
            continue

        try:
            scenario = processor.process_mystery(book_data['full_text'], book_data)
            database.save_scenario(scenario)
            print(f"  Characters: {len(scenario.characters)}, "
                  f"Physical clues: {len(scenario.physical_clues)}, "
                  f"Testimonials: {len(scenario.testimonial_revelations)}\n")
        except Exception as e:
            print(f"  Processing failed: {e}\n")
            continue

    print("=== Pipeline Complete ===")
    print(database.get_stats())


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("Get your key at: https://console.anthropic.com/")
        exit(1)

    run_acquisition_pipeline(num_books=3)
