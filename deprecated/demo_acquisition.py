"""
DEMO: Mystery Database Acquisition Pipeline
============================================

This demonstrates the pipeline with SAMPLE DATA (no API calls needed).
Shows you the exact structure and output format.

When you run this on your local machine with:
- Network access
- ANTHROPIC_API_KEY set
You'll use the full mystery_data_acquisition.py instead.
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

# ============================================================================
# DATA MODELS (same as production)
# ============================================================================

@dataclass
class Character:
    name: str
    role: str
    description: str = ""
    archetype: Optional[str] = None
    motive: Optional[str] = None
    key_quotes: List[str] = None
    
    def __post_init__(self):
        if self.key_quotes is None:
            self.key_quotes = []

@dataclass
class Evidence:
    description: str
    evidence_type: str
    relevance: str
    discovery_context: str = ""

@dataclass
class MysteryScenario:
    title: str
    source_url: str
    source_type: str
    full_text: str
    crime_type: str
    setting_location: str
    setting_time_period: str
    setting_environment: str
    
    characters: List[Character] = None
    evidence: List[Evidence] = None
    plot_summary: str = ""
    solution: str = ""
    genre_tags: List[str] = None
    
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
# SAMPLE MYSTERY DATA
# ============================================================================

SAMPLE_MYSTERY_TEXT = """
THE LOCKED ROOM MYSTERY
By A. Sample Author (Public Domain)

Chapter I: The Discovery

The body of Lord Ashworth was discovered at precisely 8:17 AM by his butler, 
Jenkins, who had brought the morning tea. The door to the study was locked 
from the inside, and the windows were sealed shut. There was no possible way 
for anyone to have entered or exited the room.

Lord Ashworth had been stabbed through the heart with an ornate letter opener
that belonged to his own desk. The murder weapon bore no fingerprints.

Present in the house that evening were:
- Lady Margaret Ashworth (his wife), who had been in her chambers
- Dr. Richard Sterling (his physician and friend), staying as a weekend guest
- Miss Elizabeth Hart (his niece), visiting from London
- Jenkins (the butler), who heard nothing unusual

Chapter II: The Investigation

Inspector Morrison examined the scene carefully. The letter opener, he noted,
was an antique piece worth considerable value. Lord Ashworth had been known
to keep it locked in his desk drawer, yet here it was, the murder weapon.

Lady Ashworth revealed that her husband had been increasingly paranoid in 
recent weeks, convinced someone was trying to poison him. This was why 
Dr. Sterling had been invited to stay.

Miss Hart mentioned that her uncle had recently changed his will, leaving 
his considerable estate to establish a foundation for medical research, 
cutting out all family members. She had learned this by accident when she 
saw legal documents on his desk the previous afternoon.

Chapter III: The Solution

The clever twist was discovered when Inspector Morrison noticed that the 
"locked" door could be manipulated from outside using a piece of string 
through the keyhole - a trick Dr. Sterling would have known from his study 
of forensic science.

Dr. Sterling had murdered Lord Ashworth to prevent the will from being 
executed. As Lord Ashworth's physician, he knew about the planned foundation
and realized it would benefit his rival's research. He staged the locked room
to create an impossible crime, hoping suspicion would fall on family members
with more obvious motives.

The evidence that convicted him: fibers from his jacket sleeve were found 
caught on the keyhole, and chemical analysis showed traces of the sedative 
he had administered to Lord Ashworth before the stabbing.
"""

# ============================================================================
# MOCK AI PROCESSOR
# ============================================================================

class MockMysteryProcessor:
    """
    Simulates what Claude AI would extract from the mystery text.
    In production, this uses the Anthropic API.
    """
    
    def process_mystery(self, raw_text: str, metadata: Dict) -> MysteryScenario:
        """
        Extract structured data from raw text.
        
        In production: Claude AI does this extraction
        In demo: We provide pre-structured output to show the format
        """
        
        print("  📖 Analyzing text structure...")
        print("  🤖 [DEMO MODE] Using pre-structured sample data")
        print("      (In production, Claude AI would extract this from raw text)")
        
        # Simulate the extraction that Claude would do
        characters = [
            Character(
                name="Lord Ashworth",
                role="victim",
                description="Wealthy aristocrat, recently paranoid",
                archetype="aristocrat",
                key_quotes=["I know someone is trying to poison me!"]
            ),
            Character(
                name="Dr. Richard Sterling",
                role="suspect",
                description="Lord Ashworth's physician and weekend guest",
                archetype="professional_rival",
                motive="Prevent medical research foundation that would benefit his rival",
                key_quotes=["I've been treating Lord Ashworth's nerves for weeks."]
            ),
            Character(
                name="Lady Margaret Ashworth",
                role="suspect",
                description="Lord Ashworth's wife, in her chambers during the murder",
                archetype="spouse",
                motive="Disinherited by the new will",
                key_quotes=["My husband had become impossible to live with."]
            ),
            Character(
                name="Miss Elizabeth Hart",
                role="suspect",
                description="Lord Ashworth's niece from London",
                archetype="relative",
                motive="Discovered she was cut from the will",
                key_quotes=["I only learned about the will by accident!"]
            ),
            Character(
                name="Jenkins",
                role="witness",
                description="The butler who discovered the body",
                archetype="butler",
                key_quotes=["The door was locked from the inside, sir."]
            ),
            Character(
                name="Inspector Morrison",
                role="detective",
                description="Investigating detective",
                archetype="investigator"
            )
        ]
        
        evidence = [
            Evidence(
                description="Ornate letter opener with no fingerprints",
                evidence_type="physical",
                relevance="critical",
                discovery_context="Found in victim's chest, murder weapon"
            ),
            Evidence(
                description="Door locked from inside",
                evidence_type="physical",
                relevance="red_herring",
                discovery_context="Appeared to be impossible crime, but was staged"
            ),
            Evidence(
                description="Sealed windows",
                evidence_type="physical",
                relevance="red_herring",
                discovery_context="No escape route apparent"
            ),
            Evidence(
                description="Changed will cutting out family members",
                evidence_type="testimonial",
                relevance="supporting",
                discovery_context="Discovered by Miss Hart the previous day"
            ),
            Evidence(
                description="Fibers from jacket caught in keyhole",
                evidence_type="physical",
                relevance="critical",
                discovery_context="Found during forensic examination"
            ),
            Evidence(
                description="Traces of sedative in victim's system",
                evidence_type="physical",
                relevance="critical",
                discovery_context="Chemical analysis post-mortem"
            ),
            Evidence(
                description="String mechanism for manipulating lock",
                evidence_type="physical",
                relevance="critical",
                discovery_context="Demonstrated by Inspector Morrison"
            ),
            Evidence(
                description="Dr. Sterling's knowledge of forensic science",
                evidence_type="testimonial",
                relevance="supporting",
                discovery_context="Background research on suspect"
            ),
            Evidence(
                description="Lord Ashworth's paranoia about poisoning",
                evidence_type="testimonial",
                relevance="supporting",
                discovery_context="Lady Ashworth's testimony"
            )
        ]
        
        scenario = MysteryScenario(
            title=metadata.get('title', 'The Locked Room Mystery'),
            source_url=metadata.get('source_url', 'demo://sample-mystery'),
            source_type='novel',
            full_text=raw_text[:500] + "...",  # Store excerpt
            crime_type='murder',
            setting_location='English manor house',
            setting_time_period='victorian',
            setting_environment='mansion',
            characters=characters,
            evidence=evidence,
            plot_summary=(
                "Lord Ashworth is found stabbed in his locked study. The locked room "
                "mystery seems impossible until Inspector Morrison discovers the door "
                "lock can be manipulated from outside. Dr. Sterling, the victim's physician, "
                "committed the murder to prevent a will change that would fund his rival's "
                "medical research. Evidence includes fibers in the keyhole and sedatives "
                "in the victim's system."
            ),
            solution=(
                "Dr. Richard Sterling murdered Lord Ashworth using a string-through-keyhole "
                "trick to stage a locked room mystery. His motive: preventing the medical "
                "research foundation that would benefit his rival. He sedated the victim "
                "first, stabbed him with the letter opener, then locked the door from outside "
                "using the string method."
            ),
            genre_tags=['locked_room', 'cozy', 'victorian', 'manor_house'],
            author=metadata.get('author', 'A. Sample Author'),
            publication_year=1895,
            license_type='public_domain'
        )
        
        return scenario


# ============================================================================
# DATABASE (same as production)
# ============================================================================

class MysteryDatabase:
    """Simple JSON storage for mysteries"""
    
    def __init__(self, storage_path: str = "./mystery_database"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        os.makedirs(f"{storage_path}/scenarios", exist_ok=True)
        os.makedirs(f"{storage_path}/raw_texts", exist_ok=True)
        
        self.index_file = f"{storage_path}/index.json"
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'w') as f:
                json.dump([], f)
    
    def save_scenario(self, scenario: MysteryScenario) -> str:
        import re
        scenario_id = re.sub(r'[^a-z0-9]+', '_', scenario.title.lower())
        
        # Save full scenario
        scenario_file = f"{self.storage_path}/scenarios/{scenario_id}.json"
        with open(scenario_file, 'w') as f:
            scenario_dict = asdict(scenario)
            json.dump(scenario_dict, f, indent=2)
        
        # Update index
        self._update_index(scenario_id, scenario)
        
        return scenario_id
    
    def _update_index(self, scenario_id: str, scenario: MysteryScenario):
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        
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
        
        print(f"\n✅ Saved: {scenario_id}")
        print(f"   Characters: {len(scenario.characters)}")
        print(f"   Evidence: {len(scenario.evidence)}")
        print(f"   File: {self.storage_path}/scenarios/{scenario_id}.json")
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        
        if not index:
            return {'total': 0}
        
        return {
            'total_mysteries': len(index),
            'crime_types': list(set(m['crime_type'] for m in index)),
            'environments': list(set(m['setting']['environment'] for m in index)),
            'total_characters': sum(m['character_count'] for m in index),
            'total_evidence': sum(m['evidence_count'] for m in index),
        }


# ============================================================================
# DEMO PIPELINE
# ============================================================================

def run_demo_pipeline():
    """
    Demonstrate the complete acquisition pipeline with sample data
    """
    
    print("="*70)
    print("MYSTERY DATABASE ACQUISITION PIPELINE - DEMO MODE")
    print("="*70)
    print()
    print("This demo shows you the EXACT structure and output format.")
    print("No API calls or network access needed.")
    print()
    print("When ready to process real mysteries:")
    print("  1. Run this on your local machine")
    print("  2. Set ANTHROPIC_API_KEY environment variable")
    print("  3. Use mystery_data_acquisition.py (full version)")
    print()
    print("="*70)
    print()
    
    # Initialize components
    processor = MockMysteryProcessor()
    database = MysteryDatabase()
    
    # Sample mystery metadata (simulating what we'd get from Project Gutenberg)
    sample_metadata = {
        'title': 'The Locked Room Mystery',
        'author': 'A. Sample Author',
        'publication_year': 1895,
        'source_url': 'demo://sample-mystery'
    }
    
    print("📚 STEP 1: Source Text")
    print("-" * 70)
    print(f"Title: {sample_metadata['title']}")
    print(f"Author: {sample_metadata['author']}")
    print(f"Text length: {len(SAMPLE_MYSTERY_TEXT)} characters")
    print(f"\nFirst 200 characters:")
    print(SAMPLE_MYSTERY_TEXT[:200] + "...")
    print()
    
    print("\n🔍 STEP 2: AI Processing & Extraction")
    print("-" * 70)
    scenario = processor.process_mystery(SAMPLE_MYSTERY_TEXT, sample_metadata)
    print()
    
    print("\n💾 STEP 3: Save to Database")
    print("-" * 70)
    scenario_id = database.save_scenario(scenario)
    print()
    
    print("\n📊 STEP 4: Database Statistics")
    print("-" * 70)
    stats = database.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("\n🎯 STEP 5: Inspect Output")
    print("-" * 70)
    print(f"\nYour mystery database is in: ./mystery_database/")
    print(f"\nKey files:")
    print(f"  📄 index.json - Searchable index of all mysteries")
    print(f"  📁 scenarios/{scenario_id}.json - Full structured data")
    print()
    print("Let's look at the structured output...")
    print()
    
    # Show sample of structured data
    print("CHARACTER EXAMPLE:")
    print("-" * 70)
    char = scenario.characters[1]  # Dr. Sterling
    print(f"  Name: {char.name}")
    print(f"  Role: {char.role}")
    print(f"  Archetype: {char.archetype}")
    print(f"  Motive: {char.motive}")
    print(f"  Description: {char.description}")
    print()
    
    print("EVIDENCE EXAMPLE:")
    print("-" * 70)
    evid = scenario.evidence[4]  # Fibers in keyhole
    print(f"  Description: {evid.description}")
    print(f"  Type: {evid.evidence_type}")
    print(f"  Relevance: {evid.relevance}")
    print(f"  Context: {evid.discovery_context}")
    print()
    
    print("SOLUTION:")
    print("-" * 70)
    print(f"  {scenario.solution}")
    print()
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE!")
    print("="*70)
    print()
    print("Next Steps:")
    print("  1. Examine ./mystery_database/scenarios/*.json files")
    print("  2. Review the data structure")
    print("  3. When ready, run the real pipeline on your local machine")
    print()
    print("The real pipeline will:")
    print("  - Download mysteries from Project Gutenberg")
    print("  - Use Claude AI to extract this same structure")
    print("  - Build a database of 50-100+ mysteries")
    print("  - Enable mystery generation for your game")
    print()
    print("="*70)
    

if __name__ == "__main__":
    run_demo_pipeline()
