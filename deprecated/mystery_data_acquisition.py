"""
Choose Your Mystery - Data Extraction POC
==========================================

This script demonstrates the core pipeline for acquiring and processing mystery content.

Requirements:
    pip install requests beautifulsoup4 spacy anthropic psycopg2-binary python-dotenv
    python -m spacy download en_core_web_sm
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Character:
    """Represents a character extracted from a mystery"""
    name: str
    role: str  # victim, suspect, detective, witness, bystander
    description: str = ""
    archetype: Optional[str] = None  # butler, spouse, business_partner, etc.
    motive: Optional[str] = None
    key_quotes: List[str] = None
    
    def __post_init__(self):
        if self.key_quotes is None:
            self.key_quotes = []


@dataclass
class Evidence:
    """Represents a piece of evidence"""
    description: str
    evidence_type: str  # physical, testimonial, circumstantial
    relevance: str  # critical, supporting, red_herring
    discovery_context: str = ""


@dataclass
class MysteryScenario:
    """Complete mystery scenario structure"""
    title: str
    source_url: str
    source_type: str  # novel, screenplay, court_transcript
    full_text: str
    crime_type: str  # murder, theft, fraud, kidnapping, etc.
    setting_location: str
    setting_time_period: str
    setting_environment: str  # mansion, ship, space_station, etc.
    
    characters: List[Character] = None
    evidence: List[Evidence] = None
    plot_summary: str = ""
    solution: str = ""
    genre_tags: List[str] = None
    
    # Metadata
    author: str = "Unknown"
    publication_year: Optional[int] = None
    license_type: str = "unknown"
    processed_date: str = None
    
    def __post_init__(self):
        if self.characters is None:
            self.characters = []
        if self.evidence is None:
            self.evidence = []
        if self.genre_tags is None:
            self.genre_tags = []
        if self.processed_date is None:
            self.processed_date = datetime.now().isoformat()


# ============================================================================
# DATA ACQUISITION - PROJECT GUTENBERG
# ============================================================================

class GutenbergScraper:
    """Scrape public domain mysteries from Project Gutenberg"""
    
    BASE_URL = "https://www.gutenberg.org"
    SEARCH_URL = f"{BASE_URL}/ebooks/search/"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ChooseYourMystery-DataAcquisition/1.0 (Research Project)'
        })
    
    def search_mysteries(self, query: str = "detective mystery", limit: int = 10) -> List[Dict]:
        """
        Search for mystery books on Project Gutenberg
        
        Why separate search from download: Rate limiting and selective processing
        """
        params = {
            'query': query,
            'submit_search': 'Go!',
        }
        
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
        
        return books
    
    def download_book_text(self, book_id: str) -> Optional[Dict]:
        """
        Download full text and metadata for a book
        
        Why use plain text format: Easier to process, no formatting artifacts
        """
        # Get metadata page
        metadata_url = f"{self.BASE_URL}/ebooks/{book_id}"
        response = self.session.get(metadata_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract metadata
        metadata = {
            'id': book_id,
            'title': self._extract_title(soup),
            'author': self._extract_author(soup),
            'publication_year': self._extract_year(soup),
        }
        
        # Download plain text version
        text_url = f"{self.BASE_URL}/files/{book_id}/{book_id}-0.txt"
        try:
            text_response = self.session.get(text_url)
            text_response.raise_for_status()
            metadata['full_text'] = text_response.text
            metadata['source_url'] = text_url
            return metadata
        except requests.RequestException:
            # Try alternative format
            text_url = f"{self.BASE_URL}/files/{book_id}/{book_id}.txt"
            try:
                text_response = self.session.get(text_url)
                text_response.raise_for_status()
                metadata['full_text'] = text_response.text
                metadata['source_url'] = text_url
                return metadata
            except requests.RequestException as e:
                print(f"Failed to download book {book_id}: {e}")
                return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract book title from metadata page"""
        title_elem = soup.select_one('h1[itemprop="name"]')
        return title_elem.get_text(strip=True) if title_elem else "Unknown"
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author name"""
        author_elem = soup.select_one('a[itemprop="creator"]')
        return author_elem.get_text(strip=True) if author_elem else "Unknown"
    
    def _extract_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract publication year"""
        # This is simplified - actual extraction may vary
        year_pattern = r'\b(1[789]\d{2}|20\d{2})\b'
        text = soup.get_text()
        match = re.search(year_pattern, text)
        return int(match.group(1)) if match else None


# ============================================================================
# DATA PROCESSING - AI-POWERED EXTRACTION
# ============================================================================

class MysteryProcessor:
    """Process raw mystery text into structured data using Claude"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize with Anthropic API key
        
        Why Claude: Superior reasoning for complex literary analysis
        """
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
    
    def process_mystery(self, raw_text: str, metadata: Dict) -> MysteryScenario:
        """
        Convert raw text into structured MysteryScenario
        
        Why AI processing: Manual extraction is impractical at scale
        Why structured output: Enables programmatic mystery generation
        """
        
        # Step 1: Basic classification
        classification = self._classify_mystery(raw_text)
        
        # Step 2: Extract characters
        characters = self._extract_characters(raw_text)
        
        # Step 3: Extract evidence and clues
        evidence = self._extract_evidence(raw_text)
        
        # Step 4: Get plot summary and solution
        summary_data = self._extract_plot_summary(raw_text)
        
        # Combine into MysteryScenario
        scenario = MysteryScenario(
            title=metadata.get('title', 'Unknown'),
            source_url=metadata.get('source_url', ''),
            source_type='novel',
            full_text=raw_text[:10000],  # Store first 10k chars for reference
            crime_type=classification.get('crime_type', 'unknown'),
            setting_location=classification.get('location', 'unknown'),
            setting_time_period=classification.get('time_period', 'unknown'),
            setting_environment=classification.get('environment', 'unknown'),
            characters=characters,
            evidence=evidence,
            plot_summary=summary_data.get('summary', ''),
            solution=summary_data.get('solution', ''),
            genre_tags=classification.get('tags', []),
            author=metadata.get('author', 'Unknown'),
            publication_year=metadata.get('publication_year'),
            license_type='public_domain'
        )
        
        return scenario
    
    def _classify_mystery(self, text: str) -> Dict:
        """
        Use Claude to classify the mystery type and setting
        
        Why separate classification step: Enables early filtering/categorization
        """
        # Truncate text for API efficiency
        sample_text = text[:4000]
        
        prompt = f"""Analyze this mystery story excerpt and classify it:

{sample_text}

Provide a JSON response with:
- crime_type: (murder, theft, fraud, kidnapping, disappearance, etc.)
- location: Geographic/setting location
- time_period: (victorian, modern, future, etc.)
- environment: (mansion, ship, train, island, city, space_station, etc.)
- tags: Array of genre tags (locked_room, cozy, noir, procedural, etc.)

Respond ONLY with valid JSON, no other text."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            response_text = message.content[0].text
            # Clean up response if Claude adds markdown
            response_text = response_text.strip('```json\n').strip('```')
            return json.loads(response_text)
        except json.JSONDecodeError:
            print("Failed to parse classification JSON")
            return {
                'crime_type': 'unknown',
                'location': 'unknown',
                'time_period': 'unknown',
                'environment': 'unknown',
                'tags': []
            }
    
    def _extract_characters(self, text: str) -> List[Character]:
        """
        Extract key characters with their roles and motives
        
        Why character extraction: Core to mystery generation
        """
        sample_text = text[:6000]
        
        prompt = f"""Analyze this mystery and extract the key characters.

{sample_text}

For each character provide:
- name
- role: (victim, suspect, detective, witness, bystander)
- description: Brief character description
- archetype: (butler, spouse, business_partner, rival, etc.)
- motive: If they're a suspect, what's their motive?

Respond with a JSON array of characters. Keep to 5-8 main characters."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            response_text = message.content[0].text.strip('```json\n').strip('```')
            char_data = json.loads(response_text)
            return [
                Character(
                    name=c.get('name', 'Unknown'),
                    role=c.get('role', 'bystander'),
                    description=c.get('description', ''),
                    archetype=c.get('archetype'),
                    motive=c.get('motive')
                )
                for c in char_data
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to extract characters: {e}")
            return []
    
    def _extract_evidence(self, text: str) -> List[Evidence]:
        """Extract key pieces of evidence"""
        sample_text = text[:6000]
        
        prompt = f"""List the key pieces of evidence in this mystery:

{sample_text}

For each piece of evidence:
- description: What is it?
- evidence_type: (physical, testimonial, circumstantial)
- relevance: (critical, supporting, red_herring)
- discovery_context: How/when was it found?

Respond with JSON array of evidence. Focus on 5-10 key pieces."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            response_text = message.content[0].text.strip('```json\n').strip('```')
            evidence_data = json.loads(response_text)
            return [
                Evidence(
                    description=e.get('description', ''),
                    evidence_type=e.get('evidence_type', 'physical'),
                    relevance=e.get('relevance', 'supporting'),
                    discovery_context=e.get('discovery_context', '')
                )
                for e in evidence_data
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to extract evidence: {e}")
            return []
    
    def _extract_plot_summary(self, text: str) -> Dict:
        """Extract plot summary and solution"""
        # For longer texts, use more content
        sample_text = text[:8000]
        
        prompt = f"""Provide a plot summary and solution for this mystery:

{sample_text}

Respond with JSON containing:
- summary: 3-5 sentence plot summary
- solution: Who committed the crime and how (if revealed in excerpt)

If solution isn't in excerpt, say "solution_not_available"."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            response_text = message.content[0].text.strip('```json\n').strip('```')
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {
                'summary': '',
                'solution': 'solution_not_available'
            }


# ============================================================================
# DATA STORAGE
# ============================================================================

class MysteryDatabase:
    """
    Simple JSON-based storage for POC
    Production should use PostgreSQL with pgvector
    
    Why JSON for POC: No setup required, easy to inspect
    Why PostgreSQL for production: Relational queries + vector search
    """
    
    def __init__(self, storage_path: str = "./mystery_database"):
        """Initialize storage directory"""
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(f"{storage_path}/scenarios", exist_ok=True)
        os.makedirs(f"{storage_path}/raw_texts", exist_ok=True)
        
        # Initialize index file
        self.index_file = f"{storage_path}/index.json"
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)
    
    def save_scenario(self, scenario: MysteryScenario) -> str:
        """
        Save a processed mystery scenario
        
        Returns: scenario_id for reference
        """
        # Generate ID from title (in production, use UUID)
        scenario_id = re.sub(r'[^a-z0-9]+', '_', scenario.title.lower())
        
        # Save scenario data
        scenario_file = f"{self.storage_path}/scenarios/{scenario_id}.json"
        with open(scenario_file, 'w') as f:
            # Convert dataclass to dict, handling nested objects
            scenario_dict = asdict(scenario)
            json.dump(scenario_dict, f, indent=2)
        
        # Update index
        self._update_index(scenario_id, scenario)
        
        print(f"Saved scenario: {scenario_id}")
        return scenario_id
    
    def _update_index(self, scenario_id: str, scenario: MysteryScenario):
        """
        Update the searchable index
        
        Why maintain index: Enables fast lookup without loading all scenarios
        """
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        
        # Add or update entry
        entry = {
            'id': scenario_id,
            'title': scenario.title,
            'crime_type': scenario.crime_type,
            'setting': {
                'location': scenario.setting_location,
                'time_period': scenario.setting_time_period,
                'environment': scenario.setting_environment
            },
            'author': scenario.author,
            'genre_tags': scenario.genre_tags,
            'character_count': len(scenario.characters),
            'evidence_count': len(scenario.evidence)
        }
        
        # Remove old entry if exists
        index = [e for e in index if e['id'] != scenario_id]
        index.append(entry)
        
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)
    
    def search_scenarios(self, **criteria) -> List[Dict]:
        """
        Search for scenarios matching criteria
        
        Example: search_scenarios(crime_type='murder', setting_environment='mansion')
        """
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        
        results = []
        for entry in index:
            match = True
            for key, value in criteria.items():
                if key == 'crime_type' and entry.get('crime_type') != value:
                    match = False
                elif key == 'setting_environment' and entry['setting'].get('environment') != value:
                    match = False
                # Add more search criteria as needed
            
            if match:
                results.append(entry)
        
        return results
    
    def load_scenario(self, scenario_id: str) -> Optional[MysteryScenario]:
        """Load a full scenario by ID"""
        scenario_file = f"{self.storage_path}/scenarios/{scenario_id}.json"
        
        if not os.path.exists(scenario_file):
            return None
        
        with open(scenario_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct dataclass (simplified - production needs recursive reconstruction)
        return MysteryScenario(**data)


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_acquisition_pipeline(num_books: int = 5):
    """
    Complete pipeline: Acquire → Process → Store
    
    Why pipeline approach: Modular, testable, resumable if errors occur
    """
    
    print("=== Choose Your Mystery - Data Acquisition Pipeline ===\n")
    
    # Initialize components
    scraper = GutenbergScraper()
    processor = MysteryProcessor()
    database = MysteryDatabase()
    
    # Step 1: Search for mysteries
    print(f"Searching for {num_books} mystery books on Project Gutenberg...")
    books = scraper.search_mysteries(query="sherlock holmes", limit=num_books)
    print(f"Found {len(books)} books\n")
    
    # Step 2: Download and process each book
    for i, book in enumerate(books, 1):
        print(f"[{i}/{len(books)}] Processing: {book['title']}")
        
        # Download
        print("  - Downloading text...")
        book_data = scraper.download_book_text(book['id'])
        
        if not book_data or not book_data.get('full_text'):
            print("  - Download failed, skipping\n")
            continue
        
        # Process with AI
        print("  - Extracting structured data with Claude...")
        try:
            scenario = processor.process_mystery(
                book_data['full_text'],
                book_data
            )
            
            # Save
            print("  - Saving to database...")
            scenario_id = database.save_scenario(scenario)
            
            print(f"  - ✓ Complete! (ID: {scenario_id})")
            print(f"    Characters: {len(scenario.characters)}, Evidence: {len(scenario.evidence)}\n")
            
        except Exception as e:
            print(f"  - ✗ Processing failed: {e}\n")
            continue
    
    # Step 3: Show summary
    print("\n=== Pipeline Complete ===")
    print(f"Check ./mystery_database/ for results")
    print(f"Index file: ./mystery_database/index.json")


if __name__ == "__main__":
    """
    Usage:
    1. Set ANTHROPIC_API_KEY environment variable
    2. Run: python mystery_data_acquisition.py
    """
    
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        print("Get your API key at: https://console.anthropic.com/")
        exit(1)
    
    # Run pipeline
    run_acquisition_pipeline(num_books=3)  # Start small for testing
