"""
Choose Your Mystery - Data Extraction Pipeline
================================================

Extracts structured mystery game data from public domain texts.
See MYSTERY_EXTRACTION_REQUIREMENTS.md for the full data specification.

The extracted data powers an AI party game where players investigate crime scenes,
interrogate AI-driven NPCs, and compete to name the culprit first. Locations are
chosen by the player at game time -- this pipeline extracts characters, crimes,
clues, and timelines that can be transplanted into any setting.

Requirements:
    pip install requests beautifulsoup4 anthropic python-dotenv
"""

import os
import re
import json
import uuid
import time
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
# ============================================================================

@dataclass
class CrimeIncident:
    """The core crime that drives the mystery."""
    crime_type: str  # murder, theft, fraud, kidnapping, disappearance, sabotage
    victim_name: str
    victim_description: str
    what_happened: str
    how_it_happened: str
    discovery_scenario: str
    surface_observations: List[str] = field(default_factory=list)
    hidden_details: List[str] = field(default_factory=list)


@dataclass
class Character:
    """An NPC that players can interrogate during the game."""
    name: str
    role: str  # victim, suspect, witness, bystander
    is_culprit: bool = False
    description: str = ""
    personality_traits: List[str] = field(default_factory=list)
    speech_style: str = ""
    motive: str = ""
    relationship_to_victim: str = ""
    relationship_to_others: List[str] = field(default_factory=list)
    knowledge_about_crime: str = ""
    knowledge_that_helps_solve: str = ""
    what_they_hide: str = ""
    interrogation_behavior: str = ""


@dataclass
class PhysicalClue:
    """A clue found through scene investigation."""
    description: str
    what_it_implies: str
    is_red_herring: bool = False
    # Red herring details (populated only when is_red_herring is True)
    false_conclusion: str = ""
    why_misleading: str = ""
    what_disproves_it: str = ""


@dataclass
class TestimonialRevelation:
    """A piece of information extracted from an NPC during interrogation."""
    description: str
    source_character: str
    what_it_implies: str
    is_red_herring: bool = False
    # Red herring details (populated only when is_red_herring is True)
    false_conclusion: str = ""
    why_misleading: str = ""
    what_disproves_it: str = ""


@dataclass
class SolutionStep:
    """One step in the logical chain that proves the culprit's guilt."""
    step_number: int
    clue_reference: str
    reasoning: str


@dataclass
class TimelineEvent:
    """A single event in the ground-truth chronology of the crime."""
    order: int
    time: str
    event: str
    actors: List[str] = field(default_factory=list)
    witnesses: List[str] = field(default_factory=list)


@dataclass
class MysteryScenario:
    """Complete extracted mystery scenario, ready for the game engine."""
    # Identity
    scenario_id: str = ""
    title: str = ""

    # Core crime
    crime: CrimeIncident = None

    # Mystery classification
    mystery_type: str = ""  # whodunit, locked_room, cozy, procedural, espionage, heist
    secondary_tags: List[str] = field(default_factory=list)

    # Characters
    characters: List[Character] = field(default_factory=list)

    # Clues and revelations
    physical_clues: List[PhysicalClue] = field(default_factory=list)
    testimonial_revelations: List[TestimonialRevelation] = field(default_factory=list)

    # Solution
    solution_chain: List[SolutionStep] = field(default_factory=list)

    # Timeline
    timeline: List[TimelineEvent] = field(default_factory=list)

    # Source metadata
    author: str = "Unknown"
    publication_year: Optional[int] = None
    source_url: str = ""
    source_type: str = ""  # novel, screenplay, true_crime
    license_type: str = "unknown"
    processed_date: str = ""

    def __post_init__(self):
        if not self.scenario_id:
            self.scenario_id = uuid.uuid4().hex[:12]
        if not self.processed_date:
            self.processed_date = datetime.now().isoformat()


# ============================================================================
# DATA ACQUISITION - PROJECT GUTENBERG
# ============================================================================

class GutenbergScraper:
    """Scrape public domain mysteries from Project Gutenberg."""

    BASE_URL = "https://www.gutenberg.org"
    SEARCH_URL = f"{BASE_URL}/ebooks/search/"
    REQUEST_DELAY = 2  # seconds between requests to respect rate limits

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ChooseYourMystery-DataAcquisition/1.0 (Research Project)'
        })

    def search_mysteries(self, query: str = "detective mystery", limit: int = 10) -> List[Dict]:
        """Search for mystery books on Project Gutenberg."""
        params = {
            'query': query,
            'submit_search': 'Go!',
        }

        response = self.session.get(self.SEARCH_URL, params=params)
        response.raise_for_status()
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

        return books

    def download_book_text(self, book_id: str) -> Optional[Dict]:
        """Download full text and metadata for a book."""
        time.sleep(self.REQUEST_DELAY)

        metadata_url = f"{self.BASE_URL}/ebooks/{book_id}"
        response = self.session.get(metadata_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        metadata = {
            'id': book_id,
            'title': self._extract_title(soup),
            'author': self._extract_author(soup),
            'publication_year': self._extract_year(soup),
        }

        time.sleep(self.REQUEST_DELAY)

        # Try primary text URL, then fallback
        for url_template in [
            f"{self.BASE_URL}/files/{book_id}/{book_id}-0.txt",
            f"{self.BASE_URL}/files/{book_id}/{book_id}.txt",
        ]:
            try:
                text_response = self.session.get(url_template)
                text_response.raise_for_status()
                metadata['full_text'] = text_response.text
                metadata['source_url'] = url_template
                return metadata
            except requests.RequestException:
                continue

        print(f"Failed to download book {book_id}: no valid text URL found")
        return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_elem = soup.select_one('h1[itemprop="name"]')
        return title_elem.get_text(strip=True) if title_elem else "Unknown"

    def _extract_author(self, soup: BeautifulSoup) -> str:
        author_elem = soup.select_one('a[itemprop="creator"]')
        return author_elem.get_text(strip=True) if author_elem else "Unknown"

    def _extract_year(self, soup: BeautifulSoup) -> Optional[int]:
        year_pattern = r'\b(1[789]\d{2}|20\d{2})\b'
        text = soup.get_text()
        match = re.search(year_pattern, text)
        return int(match.group(1)) if match else None


# ============================================================================
# HELPERS
# ============================================================================

def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM JSON responses."""
    text = text.strip()
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    return text.strip()


def _call_claude(client: anthropic.Anthropic, prompt: str, max_tokens: int = 4000) -> str:
    """Send a prompt to Claude and return the raw text response."""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def _parse_json_response(raw: str) -> any:
    """Parse a JSON response from Claude, stripping markdown fences."""
    cleaned = _strip_markdown_fences(raw)
    return json.loads(cleaned)


# ============================================================================
# DATA PROCESSING - AI-POWERED EXTRACTION
# ============================================================================

class MysteryProcessor:
    """Extract structured game data from raw mystery text using Claude."""

    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def process_mystery(self, raw_text: str, metadata: Dict) -> MysteryScenario:
        """
        Full extraction pipeline: classify, extract crime, characters,
        clues, timeline, and solution chain from raw text.
        """
        # Use a generous sample -- first ~15k chars covers most short stories
        # and the critical opening/middle of novels
        sample = raw_text[:15000]

        print("    [1/6] Classifying mystery type...")
        classification = self._classify_mystery(sample)

        print("    [2/6] Extracting core crime/incident...")
        crime = self._extract_crime(sample)

        print("    [3/6] Extracting characters...")
        characters = self._extract_characters(sample)

        print("    [4/6] Extracting clues and revelations...")
        clues_data = self._extract_clues(sample)

        print("    [5/6] Reconstructing timeline...")
        timeline = self._extract_timeline(sample)

        print("    [6/6] Building solution chain...")
        solution_chain = self._extract_solution_chain(sample)

        scenario = MysteryScenario(
            title=metadata.get('title', 'Unknown'),
            crime=crime,
            mystery_type=classification.get('mystery_type', 'whodunit'),
            secondary_tags=classification.get('secondary_tags', []),
            characters=characters,
            physical_clues=clues_data.get('physical_clues', []),
            testimonial_revelations=clues_data.get('testimonial_revelations', []),
            solution_chain=solution_chain,
            timeline=timeline,
            author=metadata.get('author', 'Unknown'),
            publication_year=metadata.get('publication_year'),
            source_url=metadata.get('source_url', ''),
            source_type='novel',
            license_type='public_domain',
        )

        return scenario

    # ------------------------------------------------------------------
    # Extraction step 1: Classify mystery type
    # ------------------------------------------------------------------

    def _classify_mystery(self, text: str) -> Dict:
        prompt = f"""Analyze this mystery text and classify it.

TEXT:
{text}

Respond with ONLY a JSON object:
{{
  "mystery_type": "<one of: whodunit, locked_room, cozy, procedural, espionage, heist>",
  "secondary_tags": ["<2-5 flavor tags, e.g. noir, historical, high_society, revenge, inheritance>"]
}}"""

        try:
            raw = _call_claude(self.client, prompt, max_tokens=500)
            return _parse_json_response(raw)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: classification parse failed ({e}), using defaults")
            return {"mystery_type": "whodunit", "secondary_tags": []}

    # ------------------------------------------------------------------
    # Extraction step 2: Core crime/incident
    # ------------------------------------------------------------------

    def _extract_crime(self, text: str) -> CrimeIncident:
        prompt = f"""Analyze this mystery text and extract the core crime/incident.

TEXT:
{text}

Respond with ONLY a JSON object:
{{
  "crime_type": "<murder, theft, fraud, kidnapping, disappearance, or sabotage>",
  "victim_name": "<name of the victim>",
  "victim_description": "<who the victim is -- role, status, key relationships>",
  "what_happened": "<1-3 sentence description of the crime>",
  "how_it_happened": "<the actual method/mechanism -- the ground truth of how the crime was committed>",
  "discovery_scenario": "<how and when the crime was discovered; what investigators initially walk into>",
  "surface_observations": ["<3-5 things immediately obvious at the scene>"],
  "hidden_details": ["<3-5 things only careful investigation or expertise would reveal>"]
}}"""

        try:
            raw = _call_claude(self.client, prompt, max_tokens=2000)
            data = _parse_json_response(raw)
            return CrimeIncident(
                crime_type=data.get('crime_type', 'unknown'),
                victim_name=data.get('victim_name', 'Unknown'),
                victim_description=data.get('victim_description', ''),
                what_happened=data.get('what_happened', ''),
                how_it_happened=data.get('how_it_happened', ''),
                discovery_scenario=data.get('discovery_scenario', ''),
                surface_observations=data.get('surface_observations', []),
                hidden_details=data.get('hidden_details', []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: crime extraction failed ({e})")
            return CrimeIncident(
                crime_type='unknown', victim_name='Unknown',
                victim_description='', what_happened='',
                how_it_happened='', discovery_scenario='',
            )

    # ------------------------------------------------------------------
    # Extraction step 3: Characters (NPCs for interrogation)
    # ------------------------------------------------------------------

    def _extract_characters(self, text: str) -> List[Character]:
        prompt = f"""Analyze this mystery text and extract 4-8 main characters.

These characters will be AI-driven NPCs in a mystery party game. Players will
interrogate them, so each character needs enough depth to sustain a conversation.

TEXT:
{text}

For EACH character, respond with a JSON array of objects. Each object must have:
{{
  "name": "<full name>",
  "role": "<victim | suspect | witness | bystander>",
  "is_culprit": <true for exactly ONE suspect, false for all others>,
  "description": "<brief physical/social description>",
  "personality_traits": ["<3-5 traits, e.g. evasive under pressure, charmingly deflective>"],
  "speech_style": "<how they talk: formal, colloquial, nervous, curt, verbose, etc.>",
  "motive": "<why this character could plausibly be the culprit -- required for all suspects>",
  "relationship_to_victim": "<their connection: spouse, business partner, rival, employee, etc.>",
  "relationship_to_others": ["<key connections to other characters, e.g. 'secretly dating Alice'>"],
  "knowledge_about_crime": "<what they know: alibi, what they saw/heard, their whereabouts>",
  "knowledge_that_helps_solve": "<specific info this character has that helps a player solve the mystery>",
  "what_they_hide": "<what they deflect on, lie about, or refuse to discuss>",
  "interrogation_behavior": "<how they behave under questioning: cooperative, hostile, tearful, evasive, etc.>"
}}

IMPORTANT:
- Exactly 1 character must be the victim (role=victim, is_culprit=false)
- Exactly 1 suspect must have is_culprit=true
- At least 2 suspects must have plausible motives (including the culprit)
- At least 1 witness
- Respond with ONLY the JSON array, no other text."""

        try:
            raw = _call_claude(self.client, prompt, max_tokens=6000)
            char_list = _parse_json_response(raw)
            return [
                Character(
                    name=c.get('name', 'Unknown'),
                    role=c.get('role', 'bystander'),
                    is_culprit=c.get('is_culprit', False),
                    description=c.get('description', ''),
                    personality_traits=c.get('personality_traits', []),
                    speech_style=c.get('speech_style', ''),
                    motive=c.get('motive', ''),
                    relationship_to_victim=c.get('relationship_to_victim', ''),
                    relationship_to_others=c.get('relationship_to_others', []),
                    knowledge_about_crime=c.get('knowledge_about_crime', ''),
                    knowledge_that_helps_solve=c.get('knowledge_that_helps_solve', ''),
                    what_they_hide=c.get('what_they_hide', ''),
                    interrogation_behavior=c.get('interrogation_behavior', ''),
                )
                for c in char_list
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: character extraction failed ({e})")
            return []

    # ------------------------------------------------------------------
    # Extraction step 4: Clues and revelations
    # ------------------------------------------------------------------

    def _extract_clues(self, text: str) -> Dict:
        prompt = f"""Analyze this mystery and extract the key clues and revelations.

These clues are the atomic units of information in a mystery party game. Players
discover them by investigating scenes or interrogating NPCs, then choose which
to share (75%) and which to withhold (25%) from other players.

TEXT:
{text}

Respond with ONLY a JSON object containing two arrays:

{{
  "physical_clues": [
    {{
      "description": "<what the clue is, e.g. 'a broken watch stopped at 2:15 AM'>",
      "what_it_implies": "<what this clue suggests or proves>",
      "is_red_herring": <true or false>,
      "false_conclusion": "<if red herring: what wrong answer it points toward>",
      "why_misleading": "<if red herring: why it seems convincing but is wrong>",
      "what_disproves_it": "<if red herring: what other clue exposes it>"
    }}
  ],
  "testimonial_revelations": [
    {{
      "description": "<the piece of information revealed>",
      "source_character": "<which character reveals this when questioned>",
      "what_it_implies": "<what this revelation suggests or proves>",
      "is_red_herring": <true or false>,
      "false_conclusion": "<if red herring: what wrong answer it points toward>",
      "why_misleading": "<if red herring: why it seems convincing but is wrong>",
      "what_disproves_it": "<if red herring: what other clue exposes it>"
    }}
  ]
}}

IMPORTANT:
- Include 4-8 physical clues and 4-8 testimonial revelations
- At least 2 total items should be red herrings
- For non-red-herring items, leave false_conclusion/why_misleading/what_disproves_it as empty strings
- Each clue must be self-contained (understandable on its own)"""

        try:
            raw = _call_claude(self.client, prompt, max_tokens=6000)
            data = _parse_json_response(raw)

            physical = [
                PhysicalClue(
                    description=c.get('description', ''),
                    what_it_implies=c.get('what_it_implies', ''),
                    is_red_herring=c.get('is_red_herring', False),
                    false_conclusion=c.get('false_conclusion', ''),
                    why_misleading=c.get('why_misleading', ''),
                    what_disproves_it=c.get('what_disproves_it', ''),
                )
                for c in data.get('physical_clues', [])
            ]

            testimonial = [
                TestimonialRevelation(
                    description=t.get('description', ''),
                    source_character=t.get('source_character', ''),
                    what_it_implies=t.get('what_it_implies', ''),
                    is_red_herring=t.get('is_red_herring', False),
                    false_conclusion=t.get('false_conclusion', ''),
                    why_misleading=t.get('why_misleading', ''),
                    what_disproves_it=t.get('what_disproves_it', ''),
                )
                for t in data.get('testimonial_revelations', [])
            ]

            return {'physical_clues': physical, 'testimonial_revelations': testimonial}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: clue extraction failed ({e})")
            return {'physical_clues': [], 'testimonial_revelations': []}

    # ------------------------------------------------------------------
    # Extraction step 5: Timeline
    # ------------------------------------------------------------------

    def _extract_timeline(self, text: str) -> List[TimelineEvent]:
        prompt = f"""Analyze this mystery and reconstruct the ground-truth timeline
of events -- what ACTUALLY happened in chronological order.

This timeline is the source of truth that the game engine uses to validate player
theories and drive NPC responses. It is NOT shown to the player.

TEXT:
{text}

Respond with ONLY a JSON array of events in chronological order:
[
  {{
    "order": 1,
    "time": "<when this occurred, e.g. '11:45 PM' or '2 hours before discovery'>",
    "event": "<what happened>",
    "actors": ["<who was involved>"],
    "witnesses": ["<who observed this, and what they actually saw -- empty if unwitnessed>"]
  }}
]

Include 5-10 events covering the key moments from before the crime through discovery."""

        try:
            raw = _call_claude(self.client, prompt, max_tokens=4000)
            events = _parse_json_response(raw)
            return [
                TimelineEvent(
                    order=e.get('order', i + 1),
                    time=e.get('time', ''),
                    event=e.get('event', ''),
                    actors=e.get('actors', []),
                    witnesses=e.get('witnesses', []),
                )
                for i, e in enumerate(events)
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: timeline extraction failed ({e})")
            return []

    # ------------------------------------------------------------------
    # Extraction step 6: Solution chain
    # ------------------------------------------------------------------

    def _extract_solution_chain(self, text: str) -> List[SolutionStep]:
        prompt = f"""Analyze this mystery and define the solution chain -- the ordered
logical sequence of clues and reasoning that proves who the culprit is and how
the crime was committed.

This is what the game engine checks against when a player "names the culprit."

TEXT:
{text}

Respond with ONLY a JSON array of 3-8 steps:
[
  {{
    "step_number": 1,
    "clue_reference": "<which physical clue or testimonial revelation this step uses>",
    "reasoning": "<how this step connects to the next, building the case>"
  }}
]

The chain should start with an initial suspicious observation and end with the
definitive proof of the culprit's identity and method."""

        try:
            raw = _call_claude(self.client, prompt, max_tokens=3000)
            steps = _parse_json_response(raw)
            return [
                SolutionStep(
                    step_number=s.get('step_number', i + 1),
                    clue_reference=s.get('clue_reference', ''),
                    reasoning=s.get('reasoning', ''),
                )
                for i, s in enumerate(steps)
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: solution chain extraction failed ({e})")
            return []


# ============================================================================
# DATA STORAGE
# ============================================================================

class MysteryDatabase:
    """
    JSON-based storage for extracted mystery scenarios.

    Production should use PostgreSQL with pgvector for vector search.
    """

    def __init__(self, storage_path: str = "./mystery_database"):
        self.storage_path = storage_path
        os.makedirs(f"{storage_path}/scenarios", exist_ok=True)

        self.index_file = f"{storage_path}/index.json"
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)

    def save_scenario(self, scenario: MysteryScenario) -> str:
        """Save a processed mystery scenario. Returns the scenario_id."""
        scenario_file = f"{self.storage_path}/scenarios/{scenario.scenario_id}.json"
        with open(scenario_file, 'w') as f:
            json.dump(asdict(scenario), f, indent=2)

        self._update_index(scenario)

        print(f"  Saved scenario: {scenario.scenario_id}")
        return scenario.scenario_id

    def _update_index(self, scenario: MysteryScenario):
        """Update the searchable index."""
        with open(self.index_file, 'r') as f:
            index = json.load(f)

        crime_type = scenario.crime.crime_type if scenario.crime else 'unknown'

        entry = {
            'id': scenario.scenario_id,
            'title': scenario.title,
            'mystery_type': scenario.mystery_type,
            'crime_type': crime_type,
            'secondary_tags': scenario.secondary_tags,
            'author': scenario.author,
            'character_count': len(scenario.characters),
            'physical_clue_count': len(scenario.physical_clues),
            'testimonial_count': len(scenario.testimonial_revelations),
            'has_solution_chain': len(scenario.solution_chain) > 0,
            'has_timeline': len(scenario.timeline) > 0,
        }

        index = [e for e in index if e['id'] != scenario.scenario_id]
        index.append(entry)

        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)

    def search_scenarios(self, **criteria) -> List[Dict]:
        """
        Search for scenarios matching criteria.

        Supported keys: mystery_type, crime_type, author.
        Any key not in the index entry is ignored.
        """
        with open(self.index_file, 'r') as f:
            index = json.load(f)

        results = []
        for entry in index:
            if all(entry.get(k) == v for k, v in criteria.items() if k in entry):
                results.append(entry)

        return results

    def load_scenario(self, scenario_id: str) -> Optional[MysteryScenario]:
        """Load a full scenario by ID, reconstructing nested dataclasses."""
        scenario_file = f"{self.storage_path}/scenarios/{scenario_id}.json"

        if not os.path.exists(scenario_file):
            return None

        with open(scenario_file, 'r') as f:
            data = json.load(f)

        # Reconstruct nested dataclasses from dicts
        crime_data = data.pop('crime', None)
        crime = CrimeIncident(**crime_data) if crime_data else None

        characters = [Character(**c) for c in data.pop('characters', [])]
        physical_clues = [PhysicalClue(**c) for c in data.pop('physical_clues', [])]
        testimonials = [TestimonialRevelation(**t) for t in data.pop('testimonial_revelations', [])]
        solution_chain = [SolutionStep(**s) for s in data.pop('solution_chain', [])]
        timeline = [TimelineEvent(**e) for e in data.pop('timeline', [])]

        return MysteryScenario(
            crime=crime,
            characters=characters,
            physical_clues=physical_clues,
            testimonial_revelations=testimonials,
            solution_chain=solution_chain,
            timeline=timeline,
            **data,
        )


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_acquisition_pipeline(num_books: int = 5):
    """Complete pipeline: Acquire -> Process -> Store."""

    print("=== Choose Your Mystery - Data Acquisition Pipeline ===\n")

    scraper = GutenbergScraper()
    processor = MysteryProcessor()
    database = MysteryDatabase()

    print(f"Searching for {num_books} mystery books on Project Gutenberg...")
    books = scraper.search_mysteries(query="sherlock holmes", limit=num_books)
    print(f"Found {len(books)} books\n")

    for i, book in enumerate(books, 1):
        print(f"[{i}/{len(books)}] Processing: {book['title']}")

        print("  Downloading text...")
        book_data = scraper.download_book_text(book['id'])

        if not book_data or not book_data.get('full_text'):
            print("  Download failed, skipping\n")
            continue

        print("  Extracting structured data with Claude...")
        try:
            scenario = processor.process_mystery(
                book_data['full_text'],
                book_data
            )

            print("  Saving to database...")
            scenario_id = database.save_scenario(scenario)

            suspects = [c for c in scenario.characters if c.role == 'suspect']
            culprit = next((c for c in scenario.characters if c.is_culprit), None)

            print(f"  Complete! (ID: {scenario_id})")
            print(f"    Characters: {len(scenario.characters)} "
                  f"({len(suspects)} suspects)")
            print(f"    Physical clues: {len(scenario.physical_clues)}, "
                  f"Testimonials: {len(scenario.testimonial_revelations)}")
            print(f"    Timeline events: {len(scenario.timeline)}, "
                  f"Solution steps: {len(scenario.solution_chain)}")
            if culprit:
                print(f"    Culprit: {culprit.name}")
            print()

        except Exception as e:
            print(f"  Processing failed: {e}\n")
            continue

    print("=== Pipeline Complete ===")
    print(f"Check ./mystery_database/ for results")
    print(f"Index file: ./mystery_database/index.json")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        print("Get your API key at: https://console.anthropic.com/")
        exit(1)

    run_acquisition_pipeline(num_books=3)
