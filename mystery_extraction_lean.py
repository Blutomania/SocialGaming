"""
Choose Your Mystery - LEAN Extraction Variant
===============================================

HYPOTHESIS: The game-time LLM can generate rich gameplay from a sparse seed.
If true, the pipeline becomes cheap and fast, and runtime generation does the
heavy lifting.

This variant extracts a "mystery seed" in a SINGLE LLM call -- just enough
for the game engine to know the crime, who did it, why, and the minimum clue
structure needed to make it solvable. Everything else (character personality,
dialogue, scene descriptions, atmosphere) is generated at runtime by the
game engine's LLM.

WHAT THIS TESTS:
- Can one LLM call produce a usable game scenario?
- Does sparse extraction + rich runtime generation = good gameplay?
- What's the minimum viable dataset for the game engine?

COMPARE AGAINST:
- mystery_data_acquisition.py (baseline: 6 LLM calls, moderate detail)
- mystery_extraction_rich.py (max detail: 8+ LLM calls, deep extraction)
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
# DATA MODEL -- intentionally minimal
# ============================================================================

@dataclass
class LeantMysterySeed:
    """
    The minimum viable extraction for a mystery game scenario.

    Everything not in this seed is generated at runtime by the game engine.
    The seed answers: What happened? Who did it? Who else is involved?
    What proves it? What's misleading?
    """
    # Identity
    scenario_id: str = ""
    title: str = ""

    # The crime (2-3 sentences, not a full CrimeIncident)
    crime_summary: str = ""
    crime_type: str = ""  # murder, theft, fraud, kidnapping, disappearance, sabotage
    mystery_type: str = ""  # whodunit, locked_room, cozy, procedural, espionage, heist

    # Victim
    victim_name: str = ""
    victim_role: str = ""  # who they are in 1 sentence

    # The culprit and their method
    culprit_name: str = ""
    culprit_motive: str = ""
    culprit_method: str = ""  # how they did it

    # Other suspects (just names + motives -- game engine fleshes them out)
    suspects: List[Dict] = field(default_factory=list)  # [{name, motive}]

    # Witnesses (just names + what they know)
    witnesses: List[Dict] = field(default_factory=list)  # [{name, key_knowledge}]

    # Clues: just descriptions and solution-relevance
    real_clues: List[str] = field(default_factory=list)
    red_herrings: List[str] = field(default_factory=list)

    # The solution in one paragraph
    solution_summary: str = ""

    # Source metadata
    author: str = "Unknown"
    publication_year: Optional[int] = None
    source_url: str = ""
    source_type: str = ""
    license_type: str = "unknown"
    processed_date: str = ""

    # Extraction metadata
    extraction_variant: str = "lean"
    llm_calls_used: int = 1

    def __post_init__(self):
        if not self.scenario_id:
            self.scenario_id = uuid.uuid4().hex[:12]
        if not self.processed_date:
            self.processed_date = datetime.now().isoformat()


# ============================================================================
# HELPERS (shared pattern -- could be extracted to a common module)
# ============================================================================

def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    return text.strip()


# ============================================================================
# SCRAPER (identical to baseline -- import in production)
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

    def search_mysteries(self, query: str = "detective mystery", limit: int = 10) -> List[Dict]:
        params = {'query': query, 'submit_search': 'Go!'}
        response = self.session.get(self.SEARCH_URL, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        books = []
        for item in soup.select('.booklink')[:limit]:
            book_id = item.get('href', '').split('/')[-1]
            title = item.get_text(strip=True)
            if book_id.isdigit():
                books.append({
                    'id': book_id, 'title': title,
                    'url': f"{self.BASE_URL}/ebooks/{book_id}"
                })
        return books

    def download_book_text(self, book_id: str) -> Optional[Dict]:
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
        print(f"Failed to download book {book_id}")
        return None

    def _extract_title(self, soup):
        elem = soup.select_one('h1[itemprop="name"]')
        return elem.get_text(strip=True) if elem else "Unknown"

    def _extract_author(self, soup):
        elem = soup.select_one('a[itemprop="creator"]')
        return elem.get_text(strip=True) if elem else "Unknown"

    def _extract_year(self, soup):
        match = re.search(r'\b(1[789]\d{2}|20\d{2})\b', soup.get_text())
        return int(match.group(1)) if match else None


# ============================================================================
# PROCESSOR -- ONE LLM CALL
# ============================================================================

class LeanProcessor:
    """Extract a mystery seed in a single LLM call."""

    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def process_mystery(self, raw_text: str, metadata: Dict) -> LeantMysterySeed:
        sample = raw_text[:15000]

        prompt = f"""Analyze this mystery text and extract a concise game scenario seed.
This will power an AI mystery party game. Be precise and factual based on the text.

TEXT:
{sample}

Respond with ONLY a JSON object:
{{
  "crime_summary": "<2-3 sentence description of the crime>",
  "crime_type": "<murder | theft | fraud | kidnapping | disappearance | sabotage>",
  "mystery_type": "<whodunit | locked_room | cozy | procedural | espionage | heist>",
  "victim_name": "<name>",
  "victim_role": "<who they are in 1 sentence>",
  "culprit_name": "<who actually did it>",
  "culprit_motive": "<why they did it, 1-2 sentences>",
  "culprit_method": "<how they did it, 1-2 sentences>",
  "suspects": [
    {{"name": "<name>", "motive": "<plausible motive in 1 sentence>"}}
  ],
  "witnesses": [
    {{"name": "<name>", "key_knowledge": "<what they know that matters, 1 sentence>"}}
  ],
  "real_clues": ["<clue that actually helps solve the mystery>"],
  "red_herrings": ["<misleading clue or detail>"],
  "solution_summary": "<1 paragraph explaining who did it, how, why, and what proves it>"
}}

REQUIREMENTS:
- 2-4 suspects (including the culprit)
- 1-3 witnesses
- 3-6 real clues
- 1-3 red herrings
- Keep everything concise -- this is a seed, not a full scenario"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            cleaned = _strip_markdown_fences(message.content[0].text)
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"    Warning: JSON parse failed ({e}), returning empty seed")
            return LeantMysterySeed(
                title=metadata.get('title', 'Unknown'),
                author=metadata.get('author', 'Unknown'),
                source_url=metadata.get('source_url', ''),
                source_type='novel',
                license_type='public_domain',
            )

        return LeantMysterySeed(
            title=metadata.get('title', 'Unknown'),
            crime_summary=data.get('crime_summary', ''),
            crime_type=data.get('crime_type', 'unknown'),
            mystery_type=data.get('mystery_type', 'whodunit'),
            victim_name=data.get('victim_name', ''),
            victim_role=data.get('victim_role', ''),
            culprit_name=data.get('culprit_name', ''),
            culprit_motive=data.get('culprit_motive', ''),
            culprit_method=data.get('culprit_method', ''),
            suspects=data.get('suspects', []),
            witnesses=data.get('witnesses', []),
            real_clues=data.get('real_clues', []),
            red_herrings=data.get('red_herrings', []),
            solution_summary=data.get('solution_summary', ''),
            author=metadata.get('author', 'Unknown'),
            publication_year=metadata.get('publication_year'),
            source_url=metadata.get('source_url', ''),
            source_type='novel',
            license_type='public_domain',
        )


# ============================================================================
# STORAGE
# ============================================================================

class MysteryDatabase:
    def __init__(self, storage_path: str = "./mystery_database_lean"):
        self.storage_path = storage_path
        os.makedirs(f"{storage_path}/scenarios", exist_ok=True)
        self.index_file = f"{storage_path}/index.json"
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)

    def save_scenario(self, seed: LeantMysterySeed) -> str:
        scenario_file = f"{self.storage_path}/scenarios/{seed.scenario_id}.json"
        with open(scenario_file, 'w') as f:
            json.dump(asdict(seed), f, indent=2)

        self._update_index(seed)
        print(f"  Saved: {seed.scenario_id}")
        return seed.scenario_id

    def _update_index(self, seed: LeantMysterySeed):
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        entry = {
            'id': seed.scenario_id,
            'title': seed.title,
            'mystery_type': seed.mystery_type,
            'crime_type': seed.crime_type,
            'author': seed.author,
            'suspect_count': len(seed.suspects),
            'clue_count': len(seed.real_clues),
            'extraction_variant': 'lean',
        }
        index = [e for e in index if e['id'] != seed.scenario_id]
        index.append(entry)
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)


# ============================================================================
# PIPELINE
# ============================================================================

def run_lean_pipeline(num_books: int = 3):
    print("=== LEAN Extraction Pipeline (1 LLM call per book) ===\n")

    scraper = GutenbergScraper()
    processor = LeanProcessor()
    database = MysteryDatabase()

    books = scraper.search_mysteries(query="sherlock holmes", limit=num_books)
    print(f"Found {len(books)} books\n")

    for i, book in enumerate(books, 1):
        print(f"[{i}/{len(books)}] {book['title']}")

        book_data = scraper.download_book_text(book['id'])
        if not book_data or not book_data.get('full_text'):
            print("  Download failed, skipping\n")
            continue

        print("  Extracting seed (single LLM call)...")
        try:
            seed = processor.process_mystery(book_data['full_text'], book_data)
            database.save_scenario(seed)

            print(f"  Crime: {seed.crime_type} ({seed.mystery_type})")
            print(f"  Culprit: {seed.culprit_name}")
            print(f"  Suspects: {len(seed.suspects)}, "
                  f"Clues: {len(seed.real_clues)}, "
                  f"Red herrings: {len(seed.red_herrings)}")
            print()
        except Exception as e:
            print(f"  Failed: {e}\n")
            continue

    print("=== Lean Pipeline Complete ===")
    print(f"Output: ./mystery_database_lean/")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        exit(1)
    run_lean_pipeline(num_books=3)
