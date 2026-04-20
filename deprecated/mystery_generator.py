"""
Choose Your Mystery - Mystery Generator
========================================

This demonstrates how to use the processed database to generate new mysteries
based on user prompts like "A murder on Mars"

"""

import json
import random
from typing import List, Dict
import anthropic
import os


class MysteryGenerator:
    """
    Generates new mystery scenarios by combining patterns from database
    with creative AI generation
    
    Architecture: RAG (Retrieval Augmented Generation)
    - Retrieves relevant examples from database
    - Uses Claude to generate new mystery using retrieved patterns
    """
    
    def __init__(self, database_path: str = "./mystery_database"):
        self.database_path = database_path
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.index = self._load_index()
    
    def _load_index(self) -> List[Dict]:
        """Load the database index"""
        index_file = f"{self.database_path}/index.json"
        try:
            with open(index_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("No database found. Run mystery_data_acquisition.py first.")
            return []
    
    def _load_scenario(self, scenario_id: str) -> Dict:
        """Load full scenario data"""
        scenario_file = f"{self.database_path}/scenarios/{scenario_id}.json"
        with open(scenario_file, 'r') as f:
            return json.load(f)
    
    def generate_mystery(self, user_prompt: str, num_players: int = 4) -> Dict:
        """
        Generate a new mystery scenario from user prompt
        
        Args:
            user_prompt: e.g., "A murder on a Mars colony"
            num_players: Number of players (affects suspect count)
        
        Returns:
            Complete mystery scenario ready for gameplay
        """
        
        print(f"\n=== Generating Mystery ===")
        print(f"Prompt: {user_prompt}")
        print(f"Players: {num_players}\n")
        
        # Step 1: Analyze prompt to extract themes
        print("Step 1: Analyzing prompt...")
        themes = self._extract_themes(user_prompt)
        print(f"  Themes: {themes}\n")
        
        # Step 2: Retrieve relevant examples from database
        print("Step 2: Retrieving similar mysteries from database...")
        examples = self._retrieve_relevant_scenarios(themes, limit=3)
        print(f"  Found {len(examples)} relevant scenarios\n")
        
        # Step 3: Extract patterns from examples
        print("Step 3: Analyzing patterns...")
        patterns = self._extract_patterns(examples)
        
        # Step 4: Generate new mystery using Claude
        print("Step 4: Generating mystery with Claude...\n")
        mystery = self._generate_with_claude(
            user_prompt=user_prompt,
            themes=themes,
            patterns=patterns,
            num_players=num_players
        )
        
        print("=== Mystery Generated Successfully! ===\n")
        return mystery
    
    def _extract_themes(self, prompt: str) -> Dict:
        """
        Extract key themes from user prompt
        
        Why extract themes first: Enables better database retrieval
        """
        
        analysis_prompt = f"""Analyze this mystery prompt and extract key themes:

"{prompt}"

Provide JSON with:
- setting_type: (space, historical, fantasy, modern, etc.)
- environment: (colony, mansion, ship, etc.)
- crime_type: (murder, theft, etc.)
- tone: (serious, comedic, noir, etc.)
- special_elements: [array of unique elements like "Mars", "animals", etc.]

Respond ONLY with JSON."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        
        try:
            response_text = message.content[0].text.strip('```json\n').strip('```')
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {
                'setting_type': 'unknown',
                'environment': 'unknown',
                'crime_type': 'murder',
                'tone': 'serious',
                'special_elements': []
            }
    
    def _retrieve_relevant_scenarios(self, themes: Dict, limit: int = 3) -> List[Dict]:
        """
        Retrieve relevant mystery scenarios from database
        
        Why retrieval: Real mystery patterns > pure AI generation
        Provides authentic structure and inspiration
        """
        
        # Simple relevance scoring (production would use vector embeddings)
        scored_scenarios = []
        
        for entry in self.index:
            score = 0
            
            # Match crime type
            if entry.get('crime_type') == themes.get('crime_type'):
                score += 5
            
            # Match setting type (simplified - would need better matching)
            setting_env = entry.get('setting', {}).get('environment', '')
            if setting_env and setting_env in themes.get('environment', ''):
                score += 3
            
            # Prefer scenarios with more structured data
            score += entry.get('character_count', 0) * 0.5
            score += entry.get('evidence_count', 0) * 0.5
            
            scored_scenarios.append((score, entry))
        
        # Sort by score and get top results
        scored_scenarios.sort(reverse=True, key=lambda x: x[0])
        top_scenarios = [s[1] for s in scored_scenarios[:limit]]
        
        # Load full scenario data
        return [self._load_scenario(s['id']) for s in top_scenarios]
    
    def _extract_patterns(self, scenarios: List[Dict]) -> Dict:
        """
        Extract reusable patterns from example scenarios
        
        Why extract patterns: Provides structure for generation
        These patterns are the "building blocks" of mysteries
        """
        
        patterns = {
            'character_archetypes': [],
            'motive_types': [],
            'evidence_types': [],
            'plot_structures': []
        }
        
        for scenario in scenarios:
            # Extract character archetypes
            for char in scenario.get('characters', []):
                if char.get('archetype'):
                    patterns['character_archetypes'].append({
                        'archetype': char['archetype'],
                        'role': char['role'],
                        'example_description': char.get('description', '')[:100]
                    })
                
                # Extract motives
                if char.get('motive'):
                    patterns['motive_types'].append(char['motive'])
            
            # Extract evidence types
            for evidence in scenario.get('evidence', []):
                patterns['evidence_types'].append({
                    'type': evidence['evidence_type'],
                    'relevance': evidence['relevance'],
                    'example': evidence['description'][:100]
                })
        
        # Deduplicate and limit
        patterns['character_archetypes'] = patterns['character_archetypes'][:10]
        patterns['motive_types'] = list(set(patterns['motive_types']))[:8]
        patterns['evidence_types'] = patterns['evidence_types'][:10]
        
        return patterns
    
    def _generate_with_claude(
        self,
        user_prompt: str,
        themes: Dict,
        patterns: Dict,
        num_players: int
    ) -> Dict:
        """
        Use Claude to generate the complete mystery scenario
        
        Why Claude: Superior creative writing + logical consistency
        Why provide patterns: Ensures mystery follows proven structures
        """
        
        generation_prompt = f"""You are creating a mystery game scenario for {num_players} players.

USER PROMPT: {user_prompt}

THEMES TO INCORPORATE:
{json.dumps(themes, indent=2)}

STRUCTURAL PATTERNS TO USE (from real mysteries):
Character Archetypes: {json.dumps(patterns['character_archetypes'][:5], indent=2)}
Motive Types: {patterns['motive_types'][:5]}
Evidence Types: {json.dumps(patterns['evidence_types'][:5], indent=2)}

REQUIREMENTS:
1. Create a complete mystery with:
   - Crime scenario (what happened)
   - {num_players + 2} characters (1 victim, {num_players} suspects, 1+ witnesses)
   - 8-10 pieces of evidence (mix of critical, supporting, and red herrings)
   - Clear solution (who did it, how, why)

2. Character Requirements:
   - Each suspect needs a believable MOTIVE
   - Each suspect needs an ALIBI (some true, some false)
   - Each character needs a distinct PERSONALITY

3. Evidence Requirements:
   - 2-3 critical pieces that definitively point to culprit
   - 3-4 supporting pieces that build the case
   - 2-3 red herrings that point to wrong suspects

4. Social Gameplay:
   - Include interesting character relationships (rivalries, secrets, connections)
   - Create opportunities for players to share/withhold information strategically
   - Include plot twists or surprises

Respond with COMPLETE JSON following this structure:
{{
  "title": "Mystery title",
  "setting": {{
    "location": "Where it takes place",
    "time_period": "When",
    "environment": "Specific setting",
    "description": "Rich description of the setting"
  }},
  "crime": {{
    "type": "murder/theft/etc",
    "what_happened": "Detailed description of the crime",
    "when": "Timing of the crime",
    "initial_discovery": "How players learn about it"
  }},
  "characters": [
    {{
      "name": "Character name",
      "role": "victim/suspect/witness/detective",
      "age": 35,
      "occupation": "Job/role",
      "personality": "Personality description",
      "archetype": "butler/spouse/etc",
      "relationship_to_victim": "Connection",
      "motive": "Why they might have done it (if suspect)",
      "alibi": "Their alibi",
      "secrets": "Hidden information about them",
      "key_dialogue_style": "How they speak"
    }}
  ],
  "evidence": [
    {{
      "id": "evidence_001",
      "name": "Evidence name",
      "description": "What it is",
      "type": "physical/testimonial/circumstantial",
      "relevance": "critical/supporting/red_herring",
      "location": "Where it's found",
      "what_it_reveals": "What this evidence tells us",
      "requires_analysis": false
    }}
  ],
  "solution": {{
    "culprit": "Character name",
    "method": "How they did it",
    "motive": "Why they did it",
    "key_evidence": ["evidence_001", "evidence_003"],
    "timeline": "Step-by-step of what really happened",
    "how_to_deduce": "Logic path to solve the mystery"
  }},
  "investigation_locations": [
    {{
      "name": "Location name",
      "description": "What's here",
      "available_evidence": ["evidence_001"],
      "characters_present": ["Character name"]
    }}
  ],
  "gameplay_notes": {{
    "estimated_playtime": "30-60 minutes",
    "difficulty": "medium",
    "key_twists": ["Twist 1", "Twist 2"],
    "strategic_tips": "Tips for the game master"
  }}
}}

Make it engaging, logical, and fun to investigate!"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[{"role": "user", "content": generation_prompt}]
        )
        
        try:
            response_text = message.content[0].text.strip('```json\n').strip('```')
            mystery = json.loads(response_text)
            
            # Validate structure
            required_keys = ['title', 'setting', 'crime', 'characters', 'evidence', 'solution']
            for key in required_keys:
                if key not in mystery:
                    raise ValueError(f"Missing required key: {key}")
            
            return mystery
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing Claude response: {e}")
            print(f"Raw response: {message.content[0].text[:500]}")
            raise
    
    def save_generated_mystery(self, mystery: Dict, filename: str = None):
        """Save generated mystery to file"""
        if filename is None:
            # Generate filename from title
            title = mystery.get('title', 'mystery')
            filename = title.lower().replace(' ', '_') + '.json'
        
        output_path = f"{self.database_path}/generated/{filename}"
        os.makedirs(f"{self.database_path}/generated", exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(mystery, f, indent=2)
        
        print(f"Saved mystery to: {output_path}")
        return output_path


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def demo_mystery_generation():
    """Demonstrate mystery generation with different prompts"""
    
    generator = MysteryGenerator()
    
    # Example prompts
    prompts = [
        "A murder on a Mars colony",
        "An art theft in ancient Athens",
        "A robbery in a land of talking animals",
        "Sabotage on a submarine during WWII",
        "A disappearance in a haunted Victorian mansion"
    ]
    
    # Generate mystery for first prompt
    prompt = prompts[0]
    
    try:
        mystery = generator.generate_mystery(
            user_prompt=prompt,
            num_players=4
        )
        
        # Display summary
        print("\n" + "="*60)
        print("GENERATED MYSTERY SUMMARY")
        print("="*60)
        print(f"\nTitle: {mystery['title']}")
        print(f"\nSetting: {mystery['setting']['description']}")
        print(f"\nCrime: {mystery['crime']['what_happened'][:200]}...")
        print(f"\nCharacters ({len(mystery['characters'])}):")
        for char in mystery['characters']:
            print(f"  - {char['name']} ({char['role']}): {char.get('personality', '')[:60]}")
        print(f"\nEvidence Count: {len(mystery['evidence'])}")
        print(f"\nCulprit: {mystery['solution']['culprit']}")
        print(f"Method: {mystery['solution']['method'][:100]}...")
        
        # Save it
        generator.save_generated_mystery(mystery)
        
        print("\n" + "="*60)
        print("Full mystery JSON saved to ./mystery_database/generated/")
        print("="*60)
        
    except Exception as e:
        print(f"\nError generating mystery: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    """
    Usage:
    1. Make sure you've run mystery_data_acquisition.py first
    2. Set ANTHROPIC_API_KEY
    3. Run: python mystery_generator.py
    """
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        exit(1)
    
    demo_mystery_generation()
