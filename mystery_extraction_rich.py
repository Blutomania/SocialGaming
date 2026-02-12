"""
Choose Your Mystery - RICH Extraction Variant
===============================================

HYPOTHESIS: More pre-extracted detail = better gameplay and less runtime LLM cost.
If true, investing in deeper pipeline extraction pays off through faster, cheaper,
and more consistent game sessions.

This variant extracts MAXIMUM depth: everything the baseline extracts plus
dialogue mechanics (setting-agnostic patterns for how characters deliver info,
deceive, and crack), emotional states, character backstories, atmosphere cues,
multiple solution paths (partial credit), and a difficulty rating. Uses 8 LLM
calls per text to go deep on every dimension.

NOTE: We do NOT extract dialogue samples or canonical lines. Players choose
arbitrary settings ("An Art Theft in Ancient Athens") so source-specific dialogue
is irrelevant. Instead we extract dialogue MECHANICS -- how a character delivers
clues, deceives, deflects, and breaks under pressure. The game-time LLM handles
setting-appropriate speech naturally.

WHAT THIS TESTS:
- Does richer pre-extracted data measurably improve gameplay?
- Do dialogue mechanics help the game-time LLM run better interrogations?
- Do multiple solution paths make the game more forgiving/fun?
- Is the extra pipeline cost worth it?

COMPARE AGAINST:
- mystery_extraction_lean.py (1 LLM call, sparse seed)
- mystery_data_acquisition.py (baseline: 6 LLM calls, moderate detail)
- mystery_extraction_templates.py (pattern extraction, remixable components)

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
# DATA MODELS -- maximum depth
# ============================================================================

@dataclass
class RichCrimeIncident:
    """Extended crime incident with atmosphere and discovery details."""
    crime_type: str
    victim_name: str
    victim_description: str
    what_happened: str
    how_it_happened: str
    discovery_scenario: str
    surface_observations: List[str] = field(default_factory=list)
    hidden_details: List[str] = field(default_factory=list)
    # Rich additions
    atmosphere: str = ""  # mood, tension level, environmental details
    initial_red_flags: List[str] = field(default_factory=list)  # what should feel "off" to an attentive player
    forensic_details: str = ""  # technical/forensic aspects a procedural player would notice


@dataclass
class RichCharacter:
    """Deep character model with dialogue mechanics and emotional arc."""
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
    # Rich additions
    backstory: str = ""  # 2-3 sentences of background
    emotional_state: str = ""  # how they feel right now (grieving, panicked, calm, etc.)
    tells_when_lying: str = ""  # behavioral cue when this character is being deceptive
    pressure_points: List[str] = field(default_factory=list)  # topics that make them crack or slip up
    # Dialogue mechanics (setting-agnostic -- HOW they communicate, not specific lines)
    info_delivery_method: str = ""  # how they reveal clues: reluctant admission, accidental slip, bragging, embedded in anecdote
    deception_technique: str = ""  # how they lie: deflection, half-truths, confident denial, emotional manipulation, answering a different question
    evasion_pattern: str = ""  # how they dodge questions: changing subject, getting emotional, invoking privacy, turning it around
    cracking_pattern: str = ""  # how they break: gradual inconsistency, emotional outburst, overexplaining, Freudian slip
    verbal_tics_when_stressed: str = ""  # setting-agnostic behavioral cues: becomes terse, rambles, repeats themselves, gets formal


@dataclass
class RichClue:
    """Extended clue with investigation difficulty and connections."""
    description: str
    what_it_implies: str
    clue_type: str  # physical or testimonial
    source: str = ""  # location or character name
    is_red_herring: bool = False
    false_conclusion: str = ""
    why_misleading: str = ""
    what_disproves_it: str = ""
    # Rich additions
    discovery_difficulty: str = ""  # easy, moderate, hard -- how hard to find/extract
    connects_to: List[str] = field(default_factory=list)  # other clue descriptions this links to
    investigation_prompt: str = ""  # what action/question leads to discovering this


@dataclass
class SolutionPath:
    """One way to solve the mystery (there may be multiple valid paths)."""
    path_name: str  # e.g. "forensic path", "motive path", "timeline path"
    steps: List[Dict] = field(default_factory=list)  # [{step_number, clue_reference, reasoning}]
    difficulty: str = ""  # easy, moderate, hard
    completeness: str = ""  # full (proves culprit) or partial (narrows to 2 suspects)


@dataclass
class TimelineEvent:
    order: int
    time: str
    event: str
    actors: List[str] = field(default_factory=list)
    witnesses: List[str] = field(default_factory=list)


@dataclass
class RichMysteryScenario:
    """Maximum-depth extraction for the game engine."""
    # Identity
    scenario_id: str = ""
    title: str = ""

    # Core crime
    crime: RichCrimeIncident = None

    # Classification
    mystery_type: str = ""
    secondary_tags: List[str] = field(default_factory=list)

    # Characters
    characters: List[RichCharacter] = field(default_factory=list)

    # Clues (unified list with type field instead of separate lists)
    clues: List[RichClue] = field(default_factory=list)

    # Multiple solution paths
    solution_paths: List[SolutionPath] = field(default_factory=list)

    # Timeline
    timeline: List[TimelineEvent] = field(default_factory=list)

    # Game metadata
    estimated_difficulty: str = ""  # easy, moderate, hard, expert
    estimated_play_time_minutes: int = 0  # rough estimate
    recommended_player_count: str = ""  # e.g. "2-4"
    key_themes: List[str] = field(default_factory=list)  # jealousy, greed, revenge, etc.

    # Source metadata
    author: str = "Unknown"
    publication_year: Optional[int] = None
    source_url: str = ""
    source_type: str = ""
    license_type: str = "unknown"
    processed_date: str = ""

    # Extraction metadata
    extraction_variant: str = "rich"
    llm_calls_used: int = 0

    def __post_init__(self):
        if not self.scenario_id:
            self.scenario_id = uuid.uuid4().hex[:12]
        if not self.processed_date:
            self.processed_date = datetime.now().isoformat()


# ============================================================================
# HELPERS
# ============================================================================

def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    return text.strip()


def _call_claude(client, prompt, max_tokens=4000):
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def _parse_json(raw):
    return json.loads(_strip_markdown_fences(raw))


# ============================================================================
# SCRAPER (identical to baseline)
# ============================================================================

class GutenbergScraper:
    BASE_URL = "https://www.gutenberg.org"
    SEARCH_URL = f"{BASE_URL}/ebooks/search/"
    REQUEST_DELAY = 2

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ChooseYourMystery-DataAcquisition/1.0 (Research Project)'
        })

    def search_mysteries(self, query="detective mystery", limit=10):
        params = {'query': query, 'submit_search': 'Go!'}
        response = self.session.get(self.SEARCH_URL, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        books = []
        for item in soup.select('.booklink')[:limit]:
            book_id = item.get('href', '').split('/')[-1]
            title = item.get_text(strip=True)
            if book_id.isdigit():
                books.append({'id': book_id, 'title': title,
                              'url': f"{self.BASE_URL}/ebooks/{book_id}"})
        return books

    def download_book_text(self, book_id):
        time.sleep(self.REQUEST_DELAY)
        response = self.session.get(f"{self.BASE_URL}/ebooks/{book_id}")
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        metadata = {
            'id': book_id,
            'title': (soup.select_one('h1[itemprop="name"]') or type('', (), {'get_text': lambda s, **k: 'Unknown'})()).get_text(strip=True),
            'author': (soup.select_one('a[itemprop="creator"]') or type('', (), {'get_text': lambda s, **k: 'Unknown'})()).get_text(strip=True),
            'publication_year': None,
        }
        match = re.search(r'\b(1[789]\d{2}|20\d{2})\b', soup.get_text())
        if match:
            metadata['publication_year'] = int(match.group(1))

        time.sleep(self.REQUEST_DELAY)
        for url in [f"{self.BASE_URL}/files/{book_id}/{book_id}-0.txt",
                     f"{self.BASE_URL}/files/{book_id}/{book_id}.txt"]:
            try:
                r = self.session.get(url)
                r.raise_for_status()
                metadata['full_text'] = r.text
                metadata['source_url'] = url
                return metadata
            except requests.RequestException:
                continue
        return None


# ============================================================================
# PROCESSOR -- 8 LLM CALLS, MAXIMUM DEPTH
# ============================================================================

class RichProcessor:
    """Extract maximum detail from mystery text."""

    def __init__(self, api_key=None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def process_mystery(self, raw_text: str, metadata: Dict) -> RichMysteryScenario:
        sample = raw_text[:15000]
        llm_calls = 0

        print("    [1/8] Classifying mystery...")
        classification = self._classify(sample)
        llm_calls += 1

        print("    [2/8] Extracting crime with atmosphere...")
        crime = self._extract_crime(sample)
        llm_calls += 1

        print("    [3/8] Extracting deep character profiles...")
        characters = self._extract_characters(sample)
        llm_calls += 1

        print("    [4/8] Extracting dialogue mechanics...")
        characters = self._extract_dialogue_mechanics(sample, characters)
        llm_calls += 1

        print("    [5/8] Extracting clues with connections...")
        clues = self._extract_clues(sample)
        llm_calls += 1

        print("    [6/8] Reconstructing timeline...")
        timeline = self._extract_timeline(sample)
        llm_calls += 1

        print("    [7/8] Building multiple solution paths...")
        solution_paths = self._extract_solution_paths(sample)
        llm_calls += 1

        print("    [8/8] Assessing difficulty and game metadata...")
        game_meta = self._assess_game_metadata(sample, characters, clues)
        llm_calls += 1

        return RichMysteryScenario(
            title=metadata.get('title', 'Unknown'),
            crime=crime,
            mystery_type=classification.get('mystery_type', 'whodunit'),
            secondary_tags=classification.get('secondary_tags', []),
            characters=characters,
            clues=clues,
            solution_paths=solution_paths,
            timeline=timeline,
            estimated_difficulty=game_meta.get('estimated_difficulty', 'moderate'),
            estimated_play_time_minutes=game_meta.get('estimated_play_time_minutes', 30),
            recommended_player_count=game_meta.get('recommended_player_count', '2-4'),
            key_themes=game_meta.get('key_themes', []),
            author=metadata.get('author', 'Unknown'),
            publication_year=metadata.get('publication_year'),
            source_url=metadata.get('source_url', ''),
            source_type='novel',
            license_type='public_domain',
            llm_calls_used=llm_calls,
        )

    def _classify(self, text):
        prompt = f"""Classify this mystery text.

TEXT:
{text}

JSON response:
{{
  "mystery_type": "<whodunit | locked_room | cozy | procedural | espionage | heist>",
  "secondary_tags": ["<2-5 tags>"]
}}"""
        try:
            return _parse_json(_call_claude(self.client, prompt, 500))
        except (json.JSONDecodeError, KeyError):
            return {"mystery_type": "whodunit", "secondary_tags": []}

    def _extract_crime(self, text):
        prompt = f"""Extract the core crime with rich atmospheric detail.

TEXT:
{text}

JSON response:
{{
  "crime_type": "<murder | theft | fraud | kidnapping | disappearance | sabotage>",
  "victim_name": "<name>",
  "victim_description": "<who they are, their role and status>",
  "what_happened": "<1-3 sentence crime description>",
  "how_it_happened": "<ground truth method>",
  "discovery_scenario": "<how the crime was discovered>",
  "surface_observations": ["<3-5 immediately obvious details>"],
  "hidden_details": ["<3-5 details requiring careful investigation>"],
  "atmosphere": "<mood and environmental description -- tension, weather, time of day, sensory details>",
  "initial_red_flags": ["<2-3 things that should feel 'off' to an attentive investigator>"],
  "forensic_details": "<technical forensic aspects a procedural player would notice>"
}}"""
        try:
            data = _parse_json(_call_claude(self.client, prompt, 3000))
            return RichCrimeIncident(**{k: data.get(k, '' if isinstance(v, str) else [])
                                        for k, v in RichCrimeIncident.__dataclass_fields__.items()
                                        if k in data})
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: crime extraction failed ({e})")
            return RichCrimeIncident(crime_type='unknown', victim_name='Unknown',
                                     victim_description='', what_happened='',
                                     how_it_happened='', discovery_scenario='')

    def _extract_characters(self, text):
        prompt = f"""Extract 4-8 deep character profiles for a mystery interrogation game.

TEXT:
{text}

JSON array. Each character:
{{
  "name": "<full name>",
  "role": "<victim | suspect | witness | bystander>",
  "is_culprit": <true for exactly ONE>,
  "description": "<brief description>",
  "personality_traits": ["<3-5 traits>"],
  "speech_style": "<how they talk -- describe the PATTERN not the dialect, e.g. 'terse and guarded' not 'Victorian English'>",
  "motive": "<why they could be the culprit>",
  "relationship_to_victim": "<connection>",
  "relationship_to_others": ["<connections to other characters>"],
  "knowledge_about_crime": "<alibi, what they saw/heard>",
  "knowledge_that_helps_solve": "<specific solving info>",
  "what_they_hide": "<what they deflect on>",
  "interrogation_behavior": "<behavior under questioning>",
  "backstory": "<2-3 sentences of background>",
  "emotional_state": "<how they feel right now>",
  "tells_when_lying": "<behavioral cue when deceptive>",
  "pressure_points": ["<topics that make them crack>"]
}}

RULES: 1 victim, 1 culprit, 2+ suspects with motives, 1+ witness."""
        try:
            char_list = _parse_json(_call_claude(self.client, prompt, 8000))
            return [RichCharacter(
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
                backstory=c.get('backstory', ''),
                emotional_state=c.get('emotional_state', ''),
                tells_when_lying=c.get('tells_when_lying', ''),
                pressure_points=c.get('pressure_points', []),
            ) for c in char_list]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: character extraction failed ({e})")
            return []

    def _extract_dialogue_mechanics(self, text, characters):
        """
        Extract setting-agnostic dialogue MECHANICS for each character.

        These describe HOW a character communicates (delivers info, deceives,
        evades, cracks) -- not what they literally say. The game-time LLM uses
        these patterns to generate setting-appropriate dialogue on the fly.
        """
        if not characters:
            return characters

        char_descriptions = "\n".join(
            f"- {c.name} ({c.role}): Traits: {', '.join(c.personality_traits)}. "
            f"Hides: {c.what_they_hide}. Interrogation behavior: {c.interrogation_behavior}"
            for c in characters if c.role != 'victim'
        )

        prompt = f"""Analyze how each character in this mystery COMMUNICATES during
questioning. Do NOT write specific dialogue lines -- instead describe the abstract
MECHANICS of how each character handles conversation. These patterns must work
in ANY setting (Victorian London, Ancient Athens, a Mars colony, etc.)

TEXT EXCERPT:
{text[:5000]}

CHARACTERS:
{char_descriptions}

For each character, respond with a JSON object:
{{
  "<character name>": {{
    "info_delivery_method": "<how they reveal key information: reluctant admission, accidental slip, bragging, embedded in anecdote, matter-of-fact, trades info for sympathy>",
    "deception_technique": "<how they lie: deflection, half-truths, confident denial, emotional manipulation, answering a different question, mixing truth with fiction, feigning ignorance>",
    "evasion_pattern": "<how they dodge uncomfortable questions: changes subject, gets emotional, invokes privacy, turns it around on questioner, claims poor memory, appeals to authority>",
    "cracking_pattern": "<how they eventually break: gradual inconsistency, emotional outburst, overexplaining, Freudian slip, exhaustion from maintaining lies, confronted with undeniable evidence>",
    "verbal_tics_when_stressed": "<setting-agnostic behavioral cues: becomes terse, rambles, repeats themselves, gets overly formal, nervous laughter, long pauses, speaks faster>"
  }}
}}"""

        try:
            data = _parse_json(_call_claude(self.client, prompt, 4000))
            for char in characters:
                if char.name in data:
                    mechanics = data[char.name]
                    char.info_delivery_method = mechanics.get('info_delivery_method', '')
                    char.deception_technique = mechanics.get('deception_technique', '')
                    char.evasion_pattern = mechanics.get('evasion_pattern', '')
                    char.cracking_pattern = mechanics.get('cracking_pattern', '')
                    char.verbal_tics_when_stressed = mechanics.get('verbal_tics_when_stressed', '')
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: dialogue mechanics extraction failed ({e})")

        return characters

    def _extract_clues(self, text):
        prompt = f"""Extract all key clues from this mystery, including discovery
difficulty and connections between clues.

TEXT:
{text}

JSON array. Each clue:
{{
  "description": "<what the clue is>",
  "what_it_implies": "<what it suggests or proves>",
  "clue_type": "<physical | testimonial>",
  "source": "<where/who it comes from>",
  "is_red_herring": <true or false>,
  "false_conclusion": "<if red herring: wrong answer it points to>",
  "why_misleading": "<if red herring: why it's convincing>",
  "what_disproves_it": "<if red herring: what exposes it>",
  "discovery_difficulty": "<easy | moderate | hard>",
  "connects_to": ["<descriptions of other clues this links to>"],
  "investigation_prompt": "<what action/question leads to discovering this>"
}}

Include 8-15 clues total. At least 3 red herrings. Mix of physical and testimonial."""
        try:
            clue_list = _parse_json(_call_claude(self.client, prompt, 8000))
            return [RichClue(
                description=c.get('description', ''),
                what_it_implies=c.get('what_it_implies', ''),
                clue_type=c.get('clue_type', 'physical'),
                source=c.get('source', ''),
                is_red_herring=c.get('is_red_herring', False),
                false_conclusion=c.get('false_conclusion', ''),
                why_misleading=c.get('why_misleading', ''),
                what_disproves_it=c.get('what_disproves_it', ''),
                discovery_difficulty=c.get('discovery_difficulty', 'moderate'),
                connects_to=c.get('connects_to', []),
                investigation_prompt=c.get('investigation_prompt', ''),
            ) for c in clue_list]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: clue extraction failed ({e})")
            return []

    def _extract_timeline(self, text):
        prompt = f"""Reconstruct the ground-truth timeline for this mystery.

TEXT:
{text}

JSON array in chronological order:
[{{"order": 1, "time": "<when>", "event": "<what>", "actors": ["<who>"], "witnesses": ["<who saw>"]}}]

Include 5-10 events from before the crime through discovery."""
        try:
            events = _parse_json(_call_claude(self.client, prompt, 3000))
            return [TimelineEvent(
                order=e.get('order', i+1), time=e.get('time', ''),
                event=e.get('event', ''), actors=e.get('actors', []),
                witnesses=e.get('witnesses', []),
            ) for i, e in enumerate(events)]
        except (json.JSONDecodeError, KeyError):
            return []

    def _extract_solution_paths(self, text):
        prompt = f"""Define multiple solution paths for this mystery. A solution path
is a logical chain of clues and reasoning that identifies the culprit.

Different players may solve the mystery differently -- one might follow forensic
evidence, another might crack a suspect through interrogation, another might
reconstruct the timeline.

TEXT:
{text}

JSON array of 2-4 solution paths:
[
  {{
    "path_name": "<e.g. forensic path, motive path, timeline path, testimony path>",
    "steps": [
      {{
        "step_number": 1,
        "clue_reference": "<which clue this step uses>",
        "reasoning": "<how this connects to the next step>"
      }}
    ],
    "difficulty": "<easy | moderate | hard>",
    "completeness": "<full (proves culprit) | partial (narrows to 2 suspects)>"
  }}
]

At least one path must be "full" completeness. Include 1-2 partial paths that
narrow down suspects but don't fully prove the case."""
        try:
            paths = _parse_json(_call_claude(self.client, prompt, 6000))
            return [SolutionPath(
                path_name=p.get('path_name', ''),
                steps=p.get('steps', []),
                difficulty=p.get('difficulty', 'moderate'),
                completeness=p.get('completeness', 'full'),
            ) for p in paths]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: solution path extraction failed ({e})")
            return []

    def _assess_game_metadata(self, text, characters, clues):
        suspect_count = sum(1 for c in characters if c.role == 'suspect')
        clue_count = len(clues)
        herring_count = sum(1 for c in clues if c.is_red_herring)

        prompt = f"""Based on this mystery (with {suspect_count} suspects,
{clue_count} clues, and {herring_count} red herrings), assess the gameplay metadata.

TEXT EXCERPT:
{text[:3000]}

JSON response:
{{
  "estimated_difficulty": "<easy | moderate | hard | expert>",
  "estimated_play_time_minutes": <number, typically 15-60>,
  "recommended_player_count": "<e.g. 2-4 or 3-6>",
  "key_themes": ["<2-4 thematic elements: jealousy, greed, revenge, betrayal, secrets, etc.>"]
}}"""
        try:
            return _parse_json(_call_claude(self.client, prompt, 500))
        except (json.JSONDecodeError, KeyError):
            return {
                "estimated_difficulty": "moderate",
                "estimated_play_time_minutes": 30,
                "recommended_player_count": "2-4",
                "key_themes": []
            }


# ============================================================================
# STORAGE
# ============================================================================

class MysteryDatabase:
    def __init__(self, storage_path="./mystery_database_rich"):
        self.storage_path = storage_path
        os.makedirs(f"{storage_path}/scenarios", exist_ok=True)
        self.index_file = f"{storage_path}/index.json"
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)

    def save_scenario(self, scenario: RichMysteryScenario) -> str:
        path = f"{self.storage_path}/scenarios/{scenario.scenario_id}.json"
        with open(path, 'w') as f:
            json.dump(asdict(scenario), f, indent=2)
        self._update_index(scenario)
        print(f"  Saved: {scenario.scenario_id}")
        return scenario.scenario_id

    def _update_index(self, s: RichMysteryScenario):
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        entry = {
            'id': s.scenario_id, 'title': s.title,
            'mystery_type': s.mystery_type,
            'crime_type': s.crime.crime_type if s.crime else 'unknown',
            'author': s.author,
            'character_count': len(s.characters),
            'clue_count': len(s.clues),
            'solution_path_count': len(s.solution_paths),
            'estimated_difficulty': s.estimated_difficulty,
            'llm_calls_used': s.llm_calls_used,
            'extraction_variant': 'rich',
        }
        index = [e for e in index if e['id'] != s.scenario_id]
        index.append(entry)
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)


# ============================================================================
# PIPELINE
# ============================================================================

def run_rich_pipeline(num_books=3):
    print("=== RICH Extraction Pipeline (8 LLM calls per book) ===\n")

    scraper = GutenbergScraper()
    processor = RichProcessor()
    database = MysteryDatabase()

    books = scraper.search_mysteries(query="sherlock holmes", limit=num_books)
    print(f"Found {len(books)} books\n")

    for i, book in enumerate(books, 1):
        print(f"[{i}/{len(books)}] {book['title']}")

        book_data = scraper.download_book_text(book['id'])
        if not book_data or not book_data.get('full_text'):
            print("  Download failed, skipping\n")
            continue

        print("  Deep extraction (8 LLM calls)...")
        try:
            scenario = processor.process_mystery(book_data['full_text'], book_data)
            database.save_scenario(scenario)

            suspects = [c for c in scenario.characters if c.role == 'suspect']
            culprit = next((c for c in scenario.characters if c.is_culprit), None)
            herrings = sum(1 for c in scenario.clues if c.is_red_herring)

            print(f"  Complete! (ID: {scenario.scenario_id})")
            print(f"    Characters: {len(scenario.characters)} ({len(suspects)} suspects)")
            print(f"    Clues: {len(scenario.clues)} ({herrings} red herrings)")
            print(f"    Solution paths: {len(scenario.solution_paths)}")
            print(f"    Timeline events: {len(scenario.timeline)}")
            print(f"    Difficulty: {scenario.estimated_difficulty}, "
                  f"~{scenario.estimated_play_time_minutes} min")
            if culprit:
                print(f"    Culprit: {culprit.name}")
            print(f"    LLM calls: {scenario.llm_calls_used}")
            print()
        except Exception as e:
            print(f"  Failed: {e}\n")
            continue

    print("=== Rich Pipeline Complete ===")
    print(f"Output: ./mystery_database_rich/")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        exit(1)
    run_rich_pipeline(num_books=3)
