"""
Choose Your Mystery - Mystery Generator
========================================

Generates complete mystery scenarios from user prompts using RAG.

Architecture:
  1. Extract themes from prompt (era, tech level, crime type, tone)
  2. Retrieve similar mysteries from database (scored by world/crime match)
  3. Extract structural patterns (archetypes, motives, clue structures)
  4. Generate complete mystery with Claude, grounded by patterns

Output follows the full MysteryScenario schema (see mystery_data_acquisition.py).

The Six Test Queries
--------------------
These are the canonical scenarios for testing the generator. Any schema change
must be validated against all six. See test_queries/ for structured versions.

  1. Murder on Mars
  2. Art Theft in Amazonia
  3. The Alchemical Forgery of the Abbasid Court
  4. The Ghost-Signal of the Victorian Deep
  5. A Steampunk Sabotage
  6. The Genetic Identity Heist of New Tokyo

Usage
-----
    python mystery_generator.py
    # Generates the first test query by default

    from mystery_generator import MysteryGenerator
    m = MysteryGenerator()
    mystery = m.generate_mystery("Murder on Mars", num_players=4)
    m.save_generated_mystery(mystery)
"""

import json
import os
import re
import uuid
from typing import List, Dict
import anthropic


TEST_QUERIES = [
    "Murder on Mars",
    "Art Theft in Amazonia",
    "The Alchemical Forgery of the Abbasid Court",
    "The Ghost-Signal of the Victorian Deep",
    "A Steampunk Sabotage",
    "The Genetic Identity Heist of New Tokyo",
]

VALID_CATEGORIES = {
    'pre_industrial': ['physical', 'chemical', 'documentary', 'testimonial', 'environmental'],
    'industrial':     ['physical', 'chemical', 'documentary', 'testimonial', 'environmental'],
    'contemporary':   ['physical', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'],
    'advanced':       ['physical', 'biological', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'],
    'sci_fi':         ['physical', 'biological', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'],
}


class MysteryGenerator:
    """
    Generates mystery scenarios from prompts using RAG.

    The schema is setting-aware: evidence categories, character archetypes,
    and interrogation mechanics all adapt to the world being generated.
    Exactly one character must have is_culprit=True.
    """

    def __init__(self, database_path: str = "./mystery_database"):
        self.database_path = database_path
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.index = self._load_index()

    def _load_index(self) -> List[Dict]:
        index_file = f"{self.database_path}/index.json"
        try:
            with open(index_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("No database found. Run mystery_data_acquisition.py first.")
            return []

    def _load_scenario(self, scenario_id: str) -> Dict:
        scenario_file = f"{self.database_path}/scenarios/{scenario_id}.json"
        with open(scenario_file, 'r') as f:
            return json.load(f)

    def generate_mystery(self, user_prompt: str, num_players: int = 4) -> Dict:
        """
        Generate a complete mystery from a user prompt.

        Args:
            user_prompt: e.g. "Murder on Mars", "Art Theft in Amazonia"
            num_players: Affects suspect count (num_players suspects generated)

        Returns:
            Complete mystery dict matching MysteryScenario schema
        """
        print(f"\n=== Generating Mystery: {user_prompt} ===\n")

        print("Step 1: Extracting themes...")
        themes = self._extract_themes(user_prompt)
        print(f"  Era: {themes.get('era')}, Tech: {themes.get('tech_level')}, "
              f"Crime: {themes.get('crime_type')}, Type: {themes.get('mystery_type')}")

        print("\nStep 2: Retrieving similar mysteries...")
        examples = self._retrieve_relevant_scenarios(themes, limit=3)
        print(f"  Found {len(examples)} relevant scenarios")

        print("\nStep 3: Extracting patterns...")
        patterns = self._extract_patterns(examples)

        print("\nStep 4: Generating with Claude...")
        mystery = self._generate_with_claude(user_prompt, themes, patterns, num_players)

        print("\n=== Mystery Generated ===\n")
        return mystery

    def _extract_themes(self, prompt: str) -> Dict:
        """Parse the prompt into structured themes for retrieval."""
        analysis_prompt = f"""Analyze this mystery prompt and extract its themes.

"{prompt}"

Respond with JSON only:
{{
  "era": "ancient|medieval|early_modern|victorian|modern|near_future|far_future|alternate_history",
  "specific_period": "e.g. Victorian 1888, Mars Colony 2157, Abbasid Caliphate 910 CE",
  "tech_level": "pre_industrial|industrial|contemporary|advanced|sci_fi",
  "environment": "specific environment: colony, mansion, court, vessel, jungle, megacity, etc.",
  "crime_type": "murder|theft|forgery|sabotage|identity_theft|kidnapping|espionage|fraud|disappearance",
  "mystery_type": "whodunit|locked_room|cozy|procedural|espionage|heist",
  "cultural_context": "Brief description of social/cultural setting",
  "tone": "serious|comedic|noir|gothic|adventure|political",
  "special_elements": ["unique elements: Mars, alchemy, genetics, steampunk, deep sea, etc."]
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            text = message.content[0].text.strip()
            text = re.sub(r'^```(?:json)?\s*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text).strip()
            return json.loads(text)
        except Exception:
            return {
                'era': 'unknown', 'specific_period': 'unknown',
                'tech_level': 'unknown', 'environment': 'unknown',
                'crime_type': 'murder', 'mystery_type': 'whodunit',
                'cultural_context': '', 'tone': 'serious', 'special_elements': []
            }

    def _retrieve_relevant_scenarios(self, themes: Dict, limit: int = 3) -> List[Dict]:
        """
        Score and retrieve the most relevant scenarios from the database.

        Scoring: crime_type +5, era +4, tech_level +3, environment +2,
                 +0.5 per character, +0.5 per physical clue
        """
        scored = []
        for entry in self.index:
            score = 0
            if entry.get('crime_type') == themes.get('crime_type'):
                score += 5
            if entry.get('world_era') == themes.get('era'):
                score += 4
            if entry.get('world_tech_level') == themes.get('tech_level'):
                score += 3
            score += entry.get('character_count', 0) * 0.5
            score += entry.get('physical_clue_count', 0) * 0.5
            scored.append((score, entry))

        scored.sort(reverse=True, key=lambda x: x[0])
        top = [s[1] for s in scored[:limit]]

        results = []
        for entry in top:
            sid = entry.get('scenario_id') or entry.get('id', '')
            try:
                results.append(self._load_scenario(sid))
            except (FileNotFoundError, KeyError):
                continue
        return results

    def _extract_patterns(self, scenarios: List[Dict]) -> Dict:
        """Extract reusable structural patterns from example scenarios."""
        patterns = {
            'character_archetypes': [],
            'motive_types': [],
            'clue_structures': [],
            'interrogation_patterns': []
        }

        for scenario in scenarios:
            for char in scenario.get('characters', []):
                if char.get('archetype'):
                    patterns['character_archetypes'].append({
                        'archetype': char['archetype'],
                        'role': char['role'],
                        'faction': char.get('faction', ''),
                        'interrogation_pattern': char.get('interrogation_behavior', '')[:100]
                    })
                if char.get('motive'):
                    patterns['motive_types'].append(char['motive'][:80])

            for clue in scenario.get('physical_clues', []):
                patterns['clue_structures'].append({
                    'category': clue.get('category', 'physical'),
                    'relevance': clue.get('relevance', 'supporting'),
                    'analysis_required': clue.get('analysis_required', False),
                    'example': clue.get('name', '')[:80]
                })

        patterns['character_archetypes'] = patterns['character_archetypes'][:8]
        patterns['motive_types'] = list(set(patterns['motive_types']))[:6]
        patterns['clue_structures'] = patterns['clue_structures'][:8]

        return patterns

    def _generate_with_claude(
        self,
        user_prompt: str,
        themes: Dict,
        patterns: Dict,
        num_players: int
    ) -> Dict:
        """Generate the complete mystery JSON using Claude."""

        tech_level = themes.get('tech_level', 'contemporary')
        valid_cats = VALID_CATEGORIES.get(tech_level, VALID_CATEGORIES['contemporary'])

        generation_prompt = f"""Create a mystery game scenario for {num_players} players.

PROMPT: {user_prompt}

THEMES:
{json.dumps(themes, indent=2)}

PATTERNS FROM SIMILAR MYSTERIES:
Archetypes: {json.dumps(patterns['character_archetypes'][:5], indent=2)}
Motives: {patterns['motive_types'][:5]}
Clue structures: {json.dumps(patterns['clue_structures'][:5], indent=2)}

REQUIREMENTS:

World:
- Internally consistent. Tech level '{tech_level}' determines what evidence is possible.
- Valid clue categories for this tech level: {valid_cats}
- world_physics_constraints must reflect real limits of this era/setting

Characters ({num_players + 2} total: 1 victim, {num_players} suspects, 1+ witness/investigator):
- EXACTLY ONE character must have is_culprit=true
- Every character must have interrogation_behavior (how they respond to questioning)
- Every character must have what_they_hide (everyone conceals something)
- Every suspect must have motive populated
- knowledge_that_helps_solve must be a list of clue atoms players can extract

Physical Clues (6-10 total, mix of critical/supporting/red_herring):
- All categories must be valid for tech_level '{tech_level}': {valid_cats}
- Minimum 2 critical clues
- Red herrings MUST have: false_conclusion, why_misleading, what_disproves_it
  (reference the clue_id that disproves each red herring)

Testimonial Revelations (4-6 total):
- At least 1 critical testimonial
- Every testimonial must have trigger_condition (what question unlocks it)
- Critical testimonials should not be freely volunteered — make players work for them

Surface observations: Visible immediately. Present at game start.
Hidden details: Require investigation. NOT presented at game start.

Solution:
- solution_steps must be an ORDERED list, each referencing real clue_IDs
- culprit_name must match exactly one character with is_culprit=true

Generate complete JSON:
{{
  "scenario_id": "GENERATE-UUID-HERE",
  "title": "Mystery title",

  "world_era": "...",
  "world_specific_period": "...",
  "world_tech_level": "...",
  "world_cultural_context": "...",
  "world_physics_constraints": ["..."],
  "world_flavor_tags": ["..."],

  "crime_type": "...",
  "mystery_type": "whodunit|locked_room|cozy|procedural|espionage|heist",
  "secondary_tags": ["..."],
  "victim_identity": "...",
  "what_happened": "...",
  "how_it_happened": "...",
  "discovery_scenario": "...",
  "surface_observations": ["..."],
  "hidden_details": ["..."],
  "stakes": "personal|political|corporate|existential",

  "characters": [{{
    "name": "...",
    "role": "victim|suspect|investigator|witness|bystander",
    "is_culprit": false,
    "occupation": "...",
    "personality_traits": ["..."],
    "speech_style": "...",
    "interrogation_behavior": "...",
    "what_they_hide": "...",
    "knowledge_about_crime": "...",
    "knowledge_that_helps_solve": ["..."],
    "relationship_to_victim": "...",
    "motive": "...",
    "alibi": "...",
    "faction": "...",
    "cultural_position": "...",
    "age": 40,
    "archetype": "..."
  }}],

  "physical_clues": [{{
    "id": "clue_001",
    "name": "...",
    "description": "...",
    "category": "must be valid for tech_level",
    "location": "...",
    "what_it_proves": "...",
    "relevance": "critical|supporting|red_herring",
    "analysis_required": false,
    "analysis_method": "...",
    "false_conclusion": "...",
    "why_misleading": "...",
    "what_disproves_it": "clue_id or testimony_id that disproves this"
  }}],

  "testimonial_revelations": [{{
    "id": "testimony_001",
    "providing_character": "...",
    "statement": "...",
    "what_it_reveals": "...",
    "relevance": "critical|supporting|red_herring",
    "trigger_condition": "...",
    "false_conclusion": null,
    "why_misleading": null,
    "what_disproves_it": null
  }}],

  "factions": [{{
    "name": "...",
    "description": "...",
    "goal": "...",
    "members": ["..."],
    "tension_with": ["..."]
  }}],

  "timeline": [{{
    "sequence": 1,
    "time": "...",
    "event": "...",
    "participant": "...",
    "visible_to_players": true
  }}],

  "solution_steps": [{{
    "step_number": 1,
    "clue_ids": ["clue_001"],
    "logical_inference": "...",
    "conclusion": "..."
  }}],

  "culprit_name": "...",
  "solution_method": "...",
  "solution_motive": "...",
  "how_to_deduce": "...",
  "plot_summary": "..."
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=10000,
                messages=[{"role": "user", "content": generation_prompt}]
            )
            text = message.content[0].text.strip()
            text = re.sub(r'^```(?:json)?\s*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text).strip()

            mystery = json.loads(text)

            # Assign a real UUID if placeholder
            if mystery.get('scenario_id', '').startswith('GENERATE'):
                mystery['scenario_id'] = str(uuid.uuid4())

            # Validate required keys
            required = ['title', 'world_era', 'crime_type', 'characters',
                        'physical_clues', 'testimonial_revelations', 'culprit_name']
            for key in required:
                if key not in mystery:
                    raise ValueError(f"Missing required key: {key}")

            # Validate exactly one culprit
            culprits = [c for c in mystery.get('characters', []) if c.get('is_culprit')]
            if len(culprits) != 1:
                raise ValueError(f"Expected exactly 1 culprit, got {len(culprits)}")

            return mystery

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing generated mystery: {e}")
            raise

    def save_generated_mystery(self, mystery: Dict, filename: str = None) -> str:
        """Save to mystery_database/generated/."""
        if filename is None:
            title = mystery.get('title', 'mystery')
            slug = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
            filename = f"{slug}.json"

        output_dir = f"{self.database_path}/generated"
        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/{filename}"

        with open(output_path, 'w') as f:
            json.dump(mystery, f, indent=2)

        print(f"Saved: {output_path}")
        return output_path


# ============================================================================
# DEMO
# ============================================================================

def demo_generate(prompt: str = None, num_players: int = 4):
    """Generate one mystery. Defaults to TEST_QUERIES[0]."""
    if prompt is None:
        prompt = TEST_QUERIES[0]

    generator = MysteryGenerator()

    try:
        mystery = generator.generate_mystery(prompt, num_players)

        print("=" * 60)
        print("GENERATED MYSTERY SUMMARY")
        print("=" * 60)
        print(f"Title:      {mystery['title']}")
        print(f"Period:     {mystery.get('world_specific_period', '?')}")
        print(f"Tech Level: {mystery.get('world_tech_level', '?')}")
        print(f"Crime:      {mystery.get('crime_type')} / {mystery.get('mystery_type')}")
        print(f"Stakes:     {mystery.get('stakes', '?')}")

        culprits = [c for c in mystery.get('characters', []) if c.get('is_culprit')]
        print(f"\nCulprit: {culprits[0]['name'] if culprits else '?'}")

        print(f"\nCharacters ({len(mystery.get('characters', []))}):")
        for c in mystery.get('characters', []):
            flag = " [CULPRIT]" if c.get('is_culprit') else ""
            print(f"  {c['name']} ({c['role']}){flag}")

        pc = mystery.get('physical_clues', [])
        tr = mystery.get('testimonial_revelations', [])
        print(f"\nPhysical clues: {len(pc)} | Testimonials: {len(tr)}")
        cats = {}
        for clue in pc:
            cats[clue.get('category', '?')] = cats.get(clue.get('category', '?'), 0) + 1
        for cat, n in cats.items():
            print(f"  {cat}: {n}")

        factions = mystery.get('factions', [])
        if factions:
            print(f"\nFactions ({len(factions)}):")
            for f in factions:
                print(f"  {f['name']}: {f.get('goal', '')[:60]}")

        path = generator.save_generated_mystery(mystery)
        print(f"\nSaved: {path}")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        exit(1)

    # Generate TEST_QUERIES[0] by default
    # Change index or pass prompt= to test others:
    #   demo_generate(prompt=TEST_QUERIES[2])  # Alchemical Forgery
    demo_generate(prompt=TEST_QUERIES[0])
