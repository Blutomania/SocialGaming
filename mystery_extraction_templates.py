"""
Choose Your Mystery - TEMPLATE Extraction Variant
===================================================

HYPOTHESIS: Extracting reusable PATTERNS instead of literal mysteries produces
a more versatile dataset. The game engine remixes these building blocks into
new mysteries rather than replaying the source material directly.

Instead of "here's the mystery from The Hound of the Baskervilles", this variant
extracts "here's a deception pattern where the culprit uses a proxy to commit
the crime while establishing an alibi through a trusted accomplice."

This is a fundamentally different dataset. It doesn't preserve the specific
story -- it captures the underlying mechanics that made it work as a mystery.

WHAT THIS TESTS:
- Can pattern-based data generate better NEW mysteries than literal extraction?
- Does the game engine produce more variety from templates vs. literal scenarios?
- Are mystery mechanics (deception types, clue structures, motive frameworks)
  more reusable than specific character/plot extractions?

COMPARE AGAINST:
- mystery_extraction_lean.py (1 LLM call, literal but sparse)
- mystery_data_acquisition.py (baseline: 6 LLM calls, literal and moderate)
- mystery_extraction_rich.py (8 LLM calls, literal and deep)

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
# DATA MODELS -- patterns and templates, not literal stories
# ============================================================================

@dataclass
class DeceptionPattern:
    """
    How the culprit conceals their guilt. This is the core "engine" of a mystery.
    Reusable across any setting or character configuration.

    Example: "proxy crime" -- culprit uses another person or mechanism to commit
    the crime while establishing an alibi elsewhere.
    """
    pattern_name: str  # e.g. proxy_crime, staged_accident, frame_job, inside_job
    description: str  # how this deception works in general terms
    how_culprit_hides: str  # the specific concealment strategy
    what_breaks_it: str  # the logical flaw or evidence type that exposes the truth
    requires: List[str] = field(default_factory=list)  # what the scenario needs (e.g. "accomplice", "access to poison")
    works_best_with: List[str] = field(default_factory=list)  # mystery types this pairs well with


@dataclass
class MotiveFramework:
    """
    A reusable motive structure that can be assigned to any character.

    Example: "inheritance threat" -- a beneficiary stands to lose their
    inheritance and acts to prevent it.
    """
    motive_type: str  # greed, revenge, self_preservation, jealousy, ideology, cover_up
    motive_pattern: str  # specific pattern name
    description: str  # how this motive works
    typical_relationship_to_victim: str  # what relationship enables this motive
    behavioral_tells: List[str] = field(default_factory=list)  # how guilt manifests
    common_deflections: List[str] = field(default_factory=list)  # how they typically hide it


@dataclass
class CharacterArchetype:
    """
    A reusable character template. Not a specific character, but a pattern
    the game engine can instantiate with any name, setting, or appearance.
    """
    archetype_name: str  # e.g. the_charming_liar, the_reluctant_witness, the_grieving_spouse
    typical_role: str  # suspect, witness, bystander
    personality_template: List[str] = field(default_factory=list)  # trait patterns
    speech_pattern: str = ""  # how this archetype talks
    interrogation_pattern: str = ""  # how they behave under questioning
    typical_knowledge: str = ""  # what this archetype usually knows
    typical_secrets: str = ""  # what they typically hide
    dramatic_function: str = ""  # what role they play in the mystery's narrative


@dataclass
class ClueChainPattern:
    """
    A reusable structure for how clues connect to form a solution.
    Not specific clues, but the logical SHAPE of the investigation.

    Example: "alibi collapse" -- clue A establishes an alibi, clue B
    introduces a timing inconsistency, clue C proves the alibi is fabricated.
    """
    pattern_name: str  # e.g. alibi_collapse, physical_impossibility, witness_contradiction
    description: str
    steps: List[Dict] = field(default_factory=list)  # [{step_type, what_it_does, connects_to_next_via}]
    difficulty: str = ""  # easy, moderate, hard
    requires_clue_types: List[str] = field(default_factory=list)  # physical, testimonial, forensic, documentary


@dataclass
class RedHerringTechnique:
    """
    A reusable pattern for misdirection.

    Example: "suspicious behavior" -- an innocent character acts guilty
    because they're hiding something unrelated to the crime.
    """
    technique_name: str
    description: str
    why_it_works: str  # why players fall for it
    what_exposes_it: str  # what reveals it's a dead end
    pairs_well_with: List[str] = field(default_factory=list)  # deception patterns it complements


@dataclass
class RelationshipDynamic:
    """
    A reusable pattern for character relationships that create tension
    and dramatic interrogation moments.
    """
    dynamic_name: str  # e.g. secret_affair, business_rivalry, hidden_debt
    roles_involved: List[str]  # e.g. ["suspect", "victim"] or ["witness", "suspect"]
    creates_tension_because: str
    interrogation_potential: str  # what interesting moments it creates during questioning
    can_be_motive: bool = False


@dataclass
class MysteryTemplate:
    """
    A complete reusable mystery template assembled from patterns.
    The game engine instantiates this with specific characters, settings, and details.
    """
    # Identity
    template_id: str = ""

    # Source reference (what text this was extracted from)
    source_title: str = ""
    source_author: str = ""

    # Core patterns
    deception_pattern: DeceptionPattern = None
    primary_motive: MotiveFramework = None
    secondary_motives: List[MotiveFramework] = field(default_factory=list)

    # Character archetypes
    character_archetypes: List[CharacterArchetype] = field(default_factory=list)

    # Investigation structure
    clue_chain: ClueChainPattern = None
    red_herring_techniques: List[RedHerringTechnique] = field(default_factory=list)

    # Relationship dynamics
    relationship_dynamics: List[RelationshipDynamic] = field(default_factory=list)

    # Classification
    mystery_type: str = ""  # whodunit, locked_room, cozy, procedural, espionage, heist
    complexity: str = ""  # simple, moderate, complex
    tone: str = ""  # dark, light, suspenseful, comedic
    themes: List[str] = field(default_factory=list)

    # Metadata
    source_url: str = ""
    source_type: str = ""
    license_type: str = "unknown"
    processed_date: str = ""
    extraction_variant: str = "template"
    llm_calls_used: int = 0

    def __post_init__(self):
        if not self.template_id:
            self.template_id = uuid.uuid4().hex[:12]
        if not self.processed_date:
            self.processed_date = datetime.now().isoformat()


# ============================================================================
# HELPERS
# ============================================================================

def _strip_markdown_fences(text):
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
# PROCESSOR -- PATTERN EXTRACTION (6 LLM calls)
# ============================================================================

class TemplateProcessor:
    """Extract reusable mystery patterns instead of literal story data."""

    def __init__(self, api_key=None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def process_mystery(self, raw_text: str, metadata: Dict) -> MysteryTemplate:
        sample = raw_text[:15000]
        llm_calls = 0

        print("    [1/6] Extracting deception pattern...")
        deception = self._extract_deception_pattern(sample)
        llm_calls += 1

        print("    [2/6] Extracting motive frameworks...")
        motives = self._extract_motives(sample)
        llm_calls += 1

        print("    [3/6] Extracting character archetypes...")
        archetypes = self._extract_archetypes(sample)
        llm_calls += 1

        print("    [4/6] Extracting clue chain pattern...")
        clue_chain = self._extract_clue_chain(sample)
        llm_calls += 1

        print("    [5/6] Extracting red herring techniques...")
        red_herrings = self._extract_red_herring_techniques(sample)
        llm_calls += 1

        print("    [6/6] Extracting relationship dynamics and metadata...")
        dynamics_and_meta = self._extract_dynamics_and_meta(sample)
        llm_calls += 1

        primary_motive = motives[0] if motives else None
        secondary_motives = motives[1:] if len(motives) > 1 else []

        return MysteryTemplate(
            source_title=metadata.get('title', 'Unknown'),
            source_author=metadata.get('author', 'Unknown'),
            deception_pattern=deception,
            primary_motive=primary_motive,
            secondary_motives=secondary_motives,
            character_archetypes=archetypes,
            clue_chain=clue_chain,
            red_herring_techniques=red_herrings,
            relationship_dynamics=dynamics_and_meta.get('dynamics', []),
            mystery_type=dynamics_and_meta.get('mystery_type', 'whodunit'),
            complexity=dynamics_and_meta.get('complexity', 'moderate'),
            tone=dynamics_and_meta.get('tone', 'suspenseful'),
            themes=dynamics_and_meta.get('themes', []),
            source_url=metadata.get('source_url', ''),
            source_type='novel',
            license_type='public_domain',
            llm_calls_used=llm_calls,
        )

    def _extract_deception_pattern(self, text):
        prompt = f"""Analyze this mystery and extract the DECEPTION PATTERN -- the
abstract strategy the culprit uses to conceal their guilt. Don't describe the
specific plot; describe the reusable PATTERN that could work in any setting.

For example: "proxy crime" = culprit uses another person/mechanism to commit
the act while establishing an alibi. "Staged accident" = crime disguised as
natural event or accident. "Frame job" = evidence planted to implicate someone else.

TEXT:
{text}

JSON response:
{{
  "pattern_name": "<short name for this deception pattern>",
  "description": "<how this deception pattern works in general, setting-agnostic terms>",
  "how_culprit_hides": "<the specific concealment strategy, abstracted from the story>",
  "what_breaks_it": "<what type of evidence or reasoning exposes the deception>",
  "requires": ["<what the scenario needs for this to work, e.g. 'access to victim's schedule'>"],
  "works_best_with": ["<mystery types: whodunit, locked_room, procedural, etc.>"]
}}"""
        try:
            data = _parse_json(_call_claude(self.client, prompt, 2000))
            return DeceptionPattern(
                pattern_name=data.get('pattern_name', ''),
                description=data.get('description', ''),
                how_culprit_hides=data.get('how_culprit_hides', ''),
                what_breaks_it=data.get('what_breaks_it', ''),
                requires=data.get('requires', []),
                works_best_with=data.get('works_best_with', []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: deception pattern extraction failed ({e})")
            return DeceptionPattern(pattern_name='unknown', description='',
                                     how_culprit_hides='', what_breaks_it='')

    def _extract_motives(self, text):
        prompt = f"""Analyze this mystery and extract the MOTIVE FRAMEWORKS -- the
abstract motive patterns at work. Don't name specific characters; describe the
reusable motive structures that could apply to characters in any setting.

TEXT:
{text}

JSON array of 2-4 motive frameworks (first one = the actual culprit's motive):
[
  {{
    "motive_type": "<greed | revenge | self_preservation | jealousy | ideology | cover_up>",
    "motive_pattern": "<short name, e.g. 'inheritance_threat' or 'silencing_a_witness'>",
    "description": "<how this motive works in general terms>",
    "typical_relationship_to_victim": "<what relationship enables this motive>",
    "behavioral_tells": ["<how guilt from this motive manifests in behavior>"],
    "common_deflections": ["<how someone with this motive typically hides it>"]
  }}
]

First entry = the actual culprit's motive. Others = plausible motives held by
innocent suspects (these create the whodunit tension)."""
        try:
            data = _parse_json(_call_claude(self.client, prompt, 3000))
            return [MotiveFramework(
                motive_type=m.get('motive_type', ''),
                motive_pattern=m.get('motive_pattern', ''),
                description=m.get('description', ''),
                typical_relationship_to_victim=m.get('typical_relationship_to_victim', ''),
                behavioral_tells=m.get('behavioral_tells', []),
                common_deflections=m.get('common_deflections', []),
            ) for m in data]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: motive extraction failed ({e})")
            return []

    def _extract_archetypes(self, text):
        prompt = f"""Analyze this mystery and extract the CHARACTER ARCHETYPES --
not the specific characters, but the reusable character PATTERNS that the game
engine can instantiate with any name or appearance.

TEXT:
{text}

JSON array of 4-7 archetypes:
[
  {{
    "archetype_name": "<e.g. the_charming_liar, the_reluctant_witness, the_grieving_spouse>",
    "typical_role": "<suspect | witness | bystander>",
    "personality_template": ["<3-5 defining traits>"],
    "speech_pattern": "<how this archetype talks>",
    "interrogation_pattern": "<how they behave under questioning>",
    "typical_knowledge": "<what this archetype usually knows>",
    "typical_secrets": "<what they typically hide -- unrelated to the crime>",
    "dramatic_function": "<what role they play in the mystery's narrative tension>"
  }}
]"""
        try:
            data = _parse_json(_call_claude(self.client, prompt, 5000))
            return [CharacterArchetype(
                archetype_name=a.get('archetype_name', ''),
                typical_role=a.get('typical_role', 'suspect'),
                personality_template=a.get('personality_template', []),
                speech_pattern=a.get('speech_pattern', ''),
                interrogation_pattern=a.get('interrogation_pattern', ''),
                typical_knowledge=a.get('typical_knowledge', ''),
                typical_secrets=a.get('typical_secrets', ''),
                dramatic_function=a.get('dramatic_function', ''),
            ) for a in data]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: archetype extraction failed ({e})")
            return []

    def _extract_clue_chain(self, text):
        prompt = f"""Analyze how this mystery's solution is constructed and extract
the CLUE CHAIN PATTERN -- the abstract logical SHAPE of the investigation, not
the specific clues.

For example: "alibi_collapse" = Step 1 (establish alibi) -> Step 2 (find timing
inconsistency) -> Step 3 (prove alibi is fabricated). This pattern works whether
the alibi is "I was at the opera" or "I was on Mars."

TEXT:
{text}

JSON response:
{{
  "pattern_name": "<short name for the investigation shape>",
  "description": "<how this clue chain pattern works in general terms>",
  "steps": [
    {{
      "step_type": "<e.g. establish_alibi, find_inconsistency, physical_evidence, testimony_contradiction>",
      "what_it_does": "<what this step accomplishes in the investigation>",
      "connects_to_next_via": "<what logical link leads to the next step>"
    }}
  ],
  "difficulty": "<easy | moderate | hard>",
  "requires_clue_types": ["<physical | testimonial | forensic | documentary>"]
}}"""
        try:
            data = _parse_json(_call_claude(self.client, prompt, 3000))
            return ClueChainPattern(
                pattern_name=data.get('pattern_name', ''),
                description=data.get('description', ''),
                steps=data.get('steps', []),
                difficulty=data.get('difficulty', 'moderate'),
                requires_clue_types=data.get('requires_clue_types', []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: clue chain extraction failed ({e})")
            return ClueChainPattern(pattern_name='unknown', description='')

    def _extract_red_herring_techniques(self, text):
        prompt = f"""Analyze this mystery's misdirection and extract the RED HERRING
TECHNIQUES -- the abstract patterns of misdirection, not the specific red herrings.

For example: "suspicious_innocence" = an innocent character acts guilty because
they're hiding something unrelated to the crime (an affair, a debt, etc.)

TEXT:
{text}

JSON array of 1-3 techniques:
[
  {{
    "technique_name": "<short name>",
    "description": "<how this misdirection technique works in general>",
    "why_it_works": "<why players fall for it>",
    "what_exposes_it": "<what reveals it's a dead end>",
    "pairs_well_with": ["<deception patterns it complements>"]
  }}
]"""
        try:
            data = _parse_json(_call_claude(self.client, prompt, 2000))
            return [RedHerringTechnique(
                technique_name=t.get('technique_name', ''),
                description=t.get('description', ''),
                why_it_works=t.get('why_it_works', ''),
                what_exposes_it=t.get('what_exposes_it', ''),
                pairs_well_with=t.get('pairs_well_with', []),
            ) for t in data]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: red herring technique extraction failed ({e})")
            return []

    def _extract_dynamics_and_meta(self, text):
        prompt = f"""Analyze this mystery and extract:
1. The RELATIONSHIP DYNAMICS between characters (abstract patterns, not specific names)
2. Overall classification metadata

TEXT:
{text}

JSON response:
{{
  "dynamics": [
    {{
      "dynamic_name": "<e.g. secret_affair, business_rivalry, hidden_debt, family_resentment>",
      "roles_involved": ["<suspect>", "<victim>"],
      "creates_tension_because": "<why this dynamic makes interrogation interesting>",
      "interrogation_potential": "<what dramatic moments it creates>",
      "can_be_motive": <true or false>
    }}
  ],
  "mystery_type": "<whodunit | locked_room | cozy | procedural | espionage | heist>",
  "complexity": "<simple | moderate | complex>",
  "tone": "<dark | light | suspenseful | comedic>",
  "themes": ["<2-4 thematic elements>"]
}}

Include 2-4 relationship dynamics."""
        try:
            data = _parse_json(_call_claude(self.client, prompt, 3000))
            dynamics = [RelationshipDynamic(
                dynamic_name=d.get('dynamic_name', ''),
                roles_involved=d.get('roles_involved', []),
                creates_tension_because=d.get('creates_tension_because', ''),
                interrogation_potential=d.get('interrogation_potential', ''),
                can_be_motive=d.get('can_be_motive', False),
            ) for d in data.get('dynamics', [])]
            return {
                'dynamics': dynamics,
                'mystery_type': data.get('mystery_type', 'whodunit'),
                'complexity': data.get('complexity', 'moderate'),
                'tone': data.get('tone', 'suspenseful'),
                'themes': data.get('themes', []),
            }
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Warning: dynamics extraction failed ({e})")
            return {'dynamics': [], 'mystery_type': 'whodunit',
                    'complexity': 'moderate', 'tone': 'suspenseful', 'themes': []}


# ============================================================================
# STORAGE
# ============================================================================

class TemplateDatabase:
    def __init__(self, storage_path="./mystery_database_templates"):
        self.storage_path = storage_path
        os.makedirs(f"{storage_path}/templates", exist_ok=True)
        self.index_file = f"{storage_path}/index.json"
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)

    def save_template(self, template: MysteryTemplate) -> str:
        path = f"{self.storage_path}/templates/{template.template_id}.json"
        with open(path, 'w') as f:
            json.dump(asdict(template), f, indent=2)
        self._update_index(template)
        print(f"  Saved: {template.template_id}")
        return template.template_id

    def _update_index(self, t: MysteryTemplate):
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        deception_name = t.deception_pattern.pattern_name if t.deception_pattern else 'unknown'
        primary_motive = t.primary_motive.motive_pattern if t.primary_motive else 'unknown'
        entry = {
            'id': t.template_id,
            'source_title': t.source_title,
            'mystery_type': t.mystery_type,
            'deception_pattern': deception_name,
            'primary_motive': primary_motive,
            'archetype_count': len(t.character_archetypes),
            'red_herring_count': len(t.red_herring_techniques),
            'complexity': t.complexity,
            'tone': t.tone,
            'extraction_variant': 'template',
        }
        index = [e for e in index if e['id'] != t.template_id]
        index.append(entry)
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)


# ============================================================================
# PIPELINE
# ============================================================================

def run_template_pipeline(num_books=3):
    print("=== TEMPLATE Extraction Pipeline (reusable patterns) ===\n")

    scraper = GutenbergScraper()
    processor = TemplateProcessor()
    database = TemplateDatabase()

    books = scraper.search_mysteries(query="sherlock holmes", limit=num_books)
    print(f"Found {len(books)} books\n")

    for i, book in enumerate(books, 1):
        print(f"[{i}/{len(books)}] {book['title']}")

        book_data = scraper.download_book_text(book['id'])
        if not book_data or not book_data.get('full_text'):
            print("  Download failed, skipping\n")
            continue

        print("  Extracting patterns (6 LLM calls)...")
        try:
            template = processor.process_mystery(book_data['full_text'], book_data)
            database.save_template(template)

            dp = template.deception_pattern
            pm = template.primary_motive

            print(f"  Complete! (ID: {template.template_id})")
            print(f"    Deception: {dp.pattern_name if dp else 'N/A'}")
            print(f"    Primary motive: {pm.motive_pattern if pm else 'N/A'} ({pm.motive_type if pm else ''})")
            print(f"    Archetypes: {len(template.character_archetypes)}")
            print(f"    Clue chain: {template.clue_chain.pattern_name if template.clue_chain else 'N/A'}")
            print(f"    Red herring techniques: {len(template.red_herring_techniques)}")
            print(f"    Relationship dynamics: {len(template.relationship_dynamics)}")
            print(f"    Type: {template.mystery_type}, Complexity: {template.complexity}")
            print()
        except Exception as e:
            print(f"  Failed: {e}\n")
            continue

    print("=== Template Pipeline Complete ===")
    print(f"Output: ./mystery_database_templates/")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        exit(1)
    run_template_pipeline(num_books=3)
