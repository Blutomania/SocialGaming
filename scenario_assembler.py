"""
Choose Your Mystery - Scenario Assembler
==========================================

The bridge between the extraction pipeline and the game. Takes a player's
prompt (e.g. "An Art Theft in Ancient Athens") and assembles a playable
mystery by:

1. MYSTERY SELECTION: Search the database for crime structures compatible
   with the player's setting. Randomly pick one.

2. CHARACTER ASSEMBLY: Pull characters from MULTIPLE source texts. The cast
   must be diverse in origin -- no single ur-text dominates. A game should
   not feel like "Agatha Christie's Death on the Nile repositioned in Athens."

3. CHARACTER REBUILDING: Transform each character into the player's setting
   using the game-time LLM. New names, occupations, relationships -- but
   the mystery function is preserved (motive, knowledge, dialogue mechanics).

The output is a GameScenario: a fully playable mystery ready for the
investigation and interrogation phases.

Requirements:
    pip install anthropic python-dotenv
"""

import os
import re
import json
import uuid
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# SETTING COMPATIBILITY
# ============================================================================

# Crime types that make sense in a given setting era. Used to filter the
# database during mystery selection. "universal" crimes work anywhere.
SETTING_CRIME_COMPATIBILITY = {
    "ancient": ["murder", "theft", "fraud", "kidnapping", "sabotage", "disappearance"],
    "medieval": ["murder", "theft", "fraud", "kidnapping", "sabotage", "disappearance"],
    "renaissance": ["murder", "theft", "fraud", "kidnapping", "sabotage", "disappearance"],
    "victorian": ["murder", "theft", "fraud", "kidnapping", "sabotage", "disappearance"],
    "modern": ["murder", "theft", "fraud", "kidnapping", "sabotage", "disappearance"],
    "future": ["murder", "theft", "fraud", "kidnapping", "sabotage", "disappearance"],
}

# Mystery types that work better in certain settings
SETTING_MYSTERY_AFFINITY = {
    "ancient": ["whodunit", "locked_room", "heist"],
    "medieval": ["whodunit", "locked_room", "espionage"],
    "renaissance": ["whodunit", "heist", "espionage"],
    "victorian": ["whodunit", "locked_room", "procedural", "cozy"],
    "modern": ["whodunit", "procedural", "espionage", "heist"],
    "future": ["whodunit", "locked_room", "procedural", "espionage"],
}


# ============================================================================
# GAME SCENARIO OUTPUT
# ============================================================================

@dataclass
class GameCharacter:
    """A character rebuilt for the player's chosen setting."""
    # Identity (generated for setting)
    name: str  # setting-appropriate name
    occupation: str  # setting-appropriate role
    description: str  # setting-appropriate description

    # Mystery function (preserved from source)
    role: str  # victim, suspect, witness, bystander
    is_culprit: bool = False
    motive: str = ""  # rewritten for setting but structurally identical
    relationship_to_victim: str = ""
    relationship_to_others: List[str] = field(default_factory=list)

    # Knowledge (preserved from source)
    knowledge_about_crime: str = ""
    knowledge_that_helps_solve: str = ""
    what_they_hide: str = ""

    # Interrogation behavior (preserved from source, setting-agnostic)
    personality_traits: List[str] = field(default_factory=list)
    interrogation_behavior: str = ""
    info_delivery_method: str = ""
    deception_technique: str = ""
    evasion_pattern: str = ""
    cracking_pattern: str = ""
    verbal_tics_when_stressed: str = ""
    pressure_points: List[str] = field(default_factory=list)

    # Provenance (for debugging/analytics -- never shown to player)
    source_title: str = ""
    source_character_name: str = ""


@dataclass
class GameClue:
    """A clue rebuilt for the player's chosen setting."""
    description: str  # setting-appropriate description
    what_it_implies: str
    clue_type: str  # physical or testimonial
    source_character: str = ""  # which NPC reveals this (for testimonial)
    is_red_herring: bool = False
    false_conclusion: str = ""
    why_misleading: str = ""
    what_disproves_it: str = ""


@dataclass
class GameScenario:
    """A fully assembled, playable mystery scenario."""
    # Game identity
    game_id: str = ""
    player_prompt: str = ""
    setting: str = ""
    setting_era: str = ""

    # Crime (rebuilt for setting)
    crime_type: str = ""
    mystery_type: str = ""
    crime_description: str = ""  # setting-appropriate
    victim_name: str = ""
    victim_description: str = ""
    discovery_scenario: str = ""
    surface_observations: List[str] = field(default_factory=list)
    hidden_details: List[str] = field(default_factory=list)

    # Cast
    characters: List[GameCharacter] = field(default_factory=list)

    # Clues
    clues: List[GameClue] = field(default_factory=list)

    # Solution
    solution_chain: List[Dict] = field(default_factory=list)

    # Timeline (ground truth, not shown to players)
    timeline: List[Dict] = field(default_factory=list)

    # Provenance (never shown to players)
    source_mystery_id: str = ""
    source_mystery_title: str = ""
    character_sources: List[str] = field(default_factory=list)  # titles of source texts

    def __post_init__(self):
        if not self.game_id:
            self.game_id = uuid.uuid4().hex[:12]


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
# STEP 1: PARSE THE PLAYER'S PROMPT
# ============================================================================

def parse_player_prompt(client: anthropic.Anthropic, prompt: str) -> Dict:
    """
    Extract structured setting info from the player's free-text prompt.

    Input: "An Art Theft in Ancient Athens"
    Output: {crime_type: "theft", setting: "Ancient Athens", era: "ancient", ...}
    """
    llm_prompt = f"""A player wants to play a mystery game. Parse their prompt
into structured data.

PLAYER PROMPT: "{prompt}"

JSON response:
{{
  "crime_type": "<murder | theft | fraud | kidnapping | disappearance | sabotage>",
  "setting_name": "<the specific setting, e.g. 'Ancient Athens'>",
  "setting_era": "<ancient | medieval | renaissance | victorian | modern | future>",
  "setting_culture": "<the cultural context, e.g. 'Greek'>",
  "tone_hint": "<any implied tone: serious, comedic, dark, lighthearted, or neutral>"
}}"""

    try:
        return _parse_json(_call_claude(client, llm_prompt, 500))
    except (json.JSONDecodeError, KeyError):
        # Fallback: extract what we can
        return {
            "crime_type": "murder",
            "setting_name": prompt,
            "setting_era": "modern",
            "setting_culture": "unknown",
            "tone_hint": "neutral",
        }


# ============================================================================
# STEP 2: SELECT A MYSTERY FROM THE DATABASE
# ============================================================================

def load_all_scenarios(database_dirs: List[str]) -> List[Dict]:
    """Load all extracted scenarios from one or more database directories."""
    all_scenarios = []

    for db_dir in database_dirs:
        scenario_dir = os.path.join(db_dir, "scenarios")
        if not os.path.exists(scenario_dir):
            continue

        for filename in os.listdir(scenario_dir):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(scenario_dir, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                data['_source_dir'] = db_dir
                data['_source_file'] = filename
                all_scenarios.append(data)

    return all_scenarios


def select_mystery(scenarios: List[Dict], parsed_prompt: Dict) -> Optional[Dict]:
    """
    Find mysteries whose crime structure is compatible with the player's
    setting, then randomly pick one.

    Compatibility rules:
    - Crime type must work in the setting era
    - Mystery type should have affinity with the era (preferred, not required)
    - Must have a solution chain (can't play an unsolvable mystery)
    """
    crime_type = parsed_prompt.get('crime_type', 'murder')
    era = parsed_prompt.get('setting_era', 'modern')

    compatible_crimes = SETTING_CRIME_COMPATIBILITY.get(era, SETTING_CRIME_COMPATIBILITY['modern'])
    preferred_types = SETTING_MYSTERY_AFFINITY.get(era, [])

    # Score each scenario
    candidates = []
    for scenario in scenarios:
        # Get the crime type from the scenario (handle both baseline and lean formats)
        s_crime_type = ''
        if isinstance(scenario.get('crime'), dict):
            s_crime_type = scenario['crime'].get('crime_type', '')
        elif scenario.get('crime_type'):
            s_crime_type = scenario['crime_type']

        # Must have a compatible crime type
        if s_crime_type not in compatible_crimes:
            continue

        # Must have characters
        chars = scenario.get('characters', [])
        if len(chars) < 3:
            continue

        # Must have some form of solution
        has_solution = (
            len(scenario.get('solution_chain', [])) > 0
            or len(scenario.get('solution_paths', [])) > 0
            or scenario.get('solution_summary', '')
        )
        if not has_solution:
            continue

        # Score: prefer matching crime type and mystery type affinity
        score = 0
        if s_crime_type == crime_type:
            score += 10  # exact crime type match

        s_mystery_type = scenario.get('mystery_type', '')
        if s_mystery_type in preferred_types:
            score += 5  # era affinity

        candidates.append((score, scenario))

    if not candidates:
        return None

    # Weight random selection toward higher scores
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Top-heavy random: pick from top 50% of candidates
    top_half = candidates[:max(1, len(candidates) // 2)]
    _, selected = random.choice(top_half)
    return selected


# ============================================================================
# STEP 3: ASSEMBLE A DIVERSE CHARACTER CAST
# ============================================================================

def collect_all_characters(scenarios: List[Dict]) -> List[Dict]:
    """
    Flatten all characters from all scenarios into a single pool,
    tagged with their source title.
    """
    pool = []
    for scenario in scenarios:
        title = scenario.get('title', scenario.get('source_title', 'Unknown'))
        for char in scenario.get('characters', []):
            char_entry = dict(char) if isinstance(char, dict) else asdict(char)
            char_entry['_source_title'] = title
            char_entry['_source_id'] = scenario.get('scenario_id',
                                                     scenario.get('template_id', ''))
            pool.append(char_entry)
    return pool


def assemble_cast(
    selected_mystery: Dict,
    all_characters: List[Dict],
    min_sources: int = 2,
) -> Tuple[List[Dict], Dict]:
    """
    Assemble a diverse cast for the game. Rules:

    1. The CULPRIT comes from the selected mystery (their motive must align
       with the crime structure).
    2. The VICTIM role is defined by the crime, not pulled from another text.
    3. SUSPECTS, WITNESSES, and BYSTANDERS are drawn from MULTIPLE source
       texts to prevent the game from feeling like a single re-skinned novel.
    4. No more than 50% of the non-culprit cast can come from one source.
    5. Each character's mystery function (motive, knowledge, dialogue mechanics)
       is preserved.

    Returns: (cast list, culprit dict)
    """
    mystery_title = selected_mystery.get('title',
                                          selected_mystery.get('source_title', ''))
    mystery_chars = selected_mystery.get('characters', [])

    # Find the culprit from the selected mystery
    culprit = None
    for c in mystery_chars:
        if c.get('is_culprit', False):
            culprit = dict(c) if isinstance(c, dict) else c
            culprit['_source_title'] = mystery_title
            break

    if not culprit:
        # No flagged culprit -- pick the first suspect
        for c in mystery_chars:
            if c.get('role') == 'suspect':
                culprit = dict(c) if isinstance(c, dict) else c
                culprit['_source_title'] = mystery_title
                culprit['is_culprit'] = True
                break

    if not culprit:
        return [], {}

    # Build the rest of the cast from the full character pool
    # Exclude characters from the same source as the culprit (initially)
    # to maximize diversity
    other_sources = [c for c in all_characters
                     if c.get('_source_title') != mystery_title
                     and c.get('role') != 'victim'
                     and not c.get('is_culprit', False)]

    same_source = [c for c in all_characters
                   if c.get('_source_title') == mystery_title
                   and c.get('name') != culprit.get('name')
                   and c.get('role') != 'victim'
                   and not c.get('is_culprit', False)]

    # We need: 1-2 more suspects, 1-2 witnesses, 0-1 bystanders
    cast = [culprit]
    source_counts = {mystery_title: 1}

    def _add_character(char):
        source = char.get('_source_title', 'Unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
        cast.append(char)

    def _pick_from_pool(pool, role, count):
        """Pick characters matching a role, preferring diverse sources."""
        matching = [c for c in pool if c.get('role') == role]
        random.shuffle(matching)

        picked = 0
        for candidate in matching:
            if picked >= count:
                break
            source = candidate.get('_source_title', 'Unknown')
            # Enforce: no single source > 50% of cast (excluding culprit)
            max_from_source = max(1, (len(cast) + count) // 2)
            if source_counts.get(source, 0) >= max_from_source:
                continue
            _add_character(candidate)
            picked += 1

        # If we couldn't fill from other sources, allow same-source
        if picked < count:
            for candidate in same_source:
                if picked >= count:
                    break
                if candidate.get('role') == role and candidate not in cast:
                    _add_character(candidate)
                    picked += 1

        return picked

    # Assemble: suspects first (most important for gameplay), then witnesses
    _pick_from_pool(other_sources, 'suspect', 2)
    _pick_from_pool(other_sources, 'witness', 2)
    _pick_from_pool(other_sources, 'bystander', 1)

    # If cast is too small, fill from same source as fallback
    if len(cast) < 4:
        for c in same_source:
            if len(cast) >= 6:
                break
            if c not in cast:
                _add_character(c)

    # Track which source texts contributed
    sources_used = list(set(source_counts.keys()))

    return cast, culprit


# ============================================================================
# STEP 4: REBUILD CHARACTERS FOR THE SETTING
# ============================================================================

def rebuild_for_setting(
    client: anthropic.Anthropic,
    cast: List[Dict],
    culprit: Dict,
    selected_mystery: Dict,
    parsed_prompt: Dict,
) -> GameScenario:
    """
    Use the game-time LLM to transform everything into the player's setting.

    This is the big generation step -- it takes the abstract mystery structure
    and the diverse character cast and rebuilds them as a cohesive scenario
    in (e.g.) Ancient Athens.
    """
    setting = parsed_prompt.get('setting_name', 'Unknown')
    era = parsed_prompt.get('setting_era', 'modern')
    culture = parsed_prompt.get('setting_culture', 'unknown')
    crime_type = parsed_prompt.get('crime_type', 'murder')
    tone = parsed_prompt.get('tone_hint', 'neutral')

    # Get the crime structure from the selected mystery
    crime_data = selected_mystery.get('crime', {})
    if isinstance(crime_data, dict):
        what_happened = crime_data.get('what_happened', '')
        how_it_happened = crime_data.get('how_it_happened', '')
        discovery = crime_data.get('discovery_scenario', '')
    else:
        what_happened = selected_mystery.get('crime_summary', '')
        how_it_happened = ''
        discovery = ''

    # Build the character summary for the prompt
    cast_summary = []
    for c in cast:
        entry = (
            f"- ROLE: {c.get('role', 'suspect')}"
            f"  | IS_CULPRIT: {c.get('is_culprit', False)}"
            f"  | MOTIVE: {c.get('motive', 'none')}"
            f"  | RELATIONSHIP_TO_VICTIM: {c.get('relationship_to_victim', '')}"
            f"  | KNOWLEDGE_ABOUT_CRIME: {c.get('knowledge_about_crime', '')}"
            f"  | KNOWLEDGE_THAT_HELPS_SOLVE: {c.get('knowledge_that_helps_solve', '')}"
            f"  | WHAT_THEY_HIDE: {c.get('what_they_hide', '')}"
            f"  | PERSONALITY_TRAITS: {c.get('personality_traits', [])}"
            f"  | INFO_DELIVERY_METHOD: {c.get('info_delivery_method', '')}"
            f"  | DECEPTION_TECHNIQUE: {c.get('deception_technique', '')}"
            f"  | EVASION_PATTERN: {c.get('evasion_pattern', '')}"
            f"  | CRACKING_PATTERN: {c.get('cracking_pattern', '')}"
            f"  | VERBAL_TICS_WHEN_STRESSED: {c.get('verbal_tics_when_stressed', '')}"
            f"  | PRESSURE_POINTS: {c.get('pressure_points', [])}"
        )
        cast_summary.append(entry)

    cast_block = "\n".join(cast_summary)

    prompt = f"""You are building a mystery game scenario. The player wants:
SETTING: {setting}
ERA: {era}
CULTURE: {culture}
CRIME TYPE: {crime_type}
TONE: {tone}

The underlying crime structure is:
WHAT HAPPENED: {what_happened}
HOW IT HAPPENED: {how_it_happened}
DISCOVERY: {discovery}

Here are the characters with their MYSTERY FUNCTIONS (motive, knowledge,
dialogue mechanics). You must PRESERVE these functions exactly but rebuild
each character for {setting}. Give them setting-appropriate names, occupations,
descriptions, and relationships.

CHARACTERS:
{cast_block}

Generate a complete game scenario as JSON:
{{
  "setting": "{setting}",
  "crime_description": "<2-3 sentences describing the crime in {setting}>",
  "victim_name": "<setting-appropriate name for the victim>",
  "victim_description": "<who the victim is in {setting}>",
  "discovery_scenario": "<how the crime is discovered in {setting}>",
  "surface_observations": ["<3-5 things immediately visible at the scene>"],
  "hidden_details": ["<3-5 things only careful investigation reveals>"],
  "characters": [
    {{
      "name": "<{culture}-appropriate name>",
      "occupation": "<setting-appropriate occupation>",
      "description": "<brief description fitting {setting}>",
      "role": "<preserve from source: victim/suspect/witness/bystander>",
      "is_culprit": "<preserve from source>",
      "motive": "<rewrite the source motive for {setting} -- same structure, new details>",
      "relationship_to_victim": "<rewrite for {setting}>",
      "relationship_to_others": ["<setting-appropriate connections>"],
      "knowledge_about_crime": "<preserve the knowledge structure, rewrite for {setting}>",
      "knowledge_that_helps_solve": "<preserve exactly, rewrite for {setting}>",
      "what_they_hide": "<preserve, rewrite for {setting}>"
    }}
  ],
  "clues": [
    {{
      "description": "<setting-appropriate clue>",
      "what_it_implies": "<what it means>",
      "clue_type": "<physical | testimonial>",
      "source_character": "<which character, for testimonial clues>",
      "is_red_herring": false
    }}
  ],
  "solution_chain": [
    {{
      "step_number": 1,
      "clue_reference": "<which clue>",
      "reasoning": "<how it proves the case>"
    }}
  ],
  "timeline": [
    {{
      "order": 1,
      "time": "<when>",
      "event": "<what happened>",
      "actors": ["<who>"]
    }}
  ]
}}

CRITICAL RULES:
- Every character's mystery FUNCTION must be preserved (motive structure,
  what they know, what they hide, how they behave in interrogation)
- Names and occupations must be culturally appropriate for {setting}
- The victim is a NEW character for this setting (not taken from source)
- Include 6-12 clues (mix of physical and testimonial, 2-3 red herrings)
- Solution chain must be logically sound (3-6 steps)
- Timeline must be chronologically consistent (5-8 events)
- The culprit's identity must be provable through the clues"""

    print("  Generating scenario for setting...")
    raw = _call_claude(client, prompt, max_tokens=8000)
    scenario_data = _parse_json(raw)

    # Assemble the GameScenario
    characters = []
    for i, char_data in enumerate(scenario_data.get('characters', [])):
        # Carry over the dialogue mechanics from the original cast
        source_char = cast[i] if i < len(cast) else {}
        characters.append(GameCharacter(
            name=char_data.get('name', ''),
            occupation=char_data.get('occupation', ''),
            description=char_data.get('description', ''),
            role=char_data.get('role', 'suspect'),
            is_culprit=char_data.get('is_culprit', False),
            motive=char_data.get('motive', ''),
            relationship_to_victim=char_data.get('relationship_to_victim', ''),
            relationship_to_others=char_data.get('relationship_to_others', []),
            knowledge_about_crime=char_data.get('knowledge_about_crime', ''),
            knowledge_that_helps_solve=char_data.get('knowledge_that_helps_solve', ''),
            what_they_hide=char_data.get('what_they_hide', ''),
            personality_traits=source_char.get('personality_traits', []),
            interrogation_behavior=source_char.get('interrogation_behavior', ''),
            info_delivery_method=source_char.get('info_delivery_method', ''),
            deception_technique=source_char.get('deception_technique', ''),
            evasion_pattern=source_char.get('evasion_pattern', ''),
            cracking_pattern=source_char.get('cracking_pattern', ''),
            verbal_tics_when_stressed=source_char.get('verbal_tics_when_stressed', ''),
            pressure_points=source_char.get('pressure_points', []),
            source_title=source_char.get('_source_title', ''),
            source_character_name=source_char.get('name', ''),
        ))

    clues = [
        GameClue(
            description=c.get('description', ''),
            what_it_implies=c.get('what_it_implies', ''),
            clue_type=c.get('clue_type', 'physical'),
            source_character=c.get('source_character', ''),
            is_red_herring=c.get('is_red_herring', False),
            false_conclusion=c.get('false_conclusion', ''),
            why_misleading=c.get('why_misleading', ''),
            what_disproves_it=c.get('what_disproves_it', ''),
        )
        for c in scenario_data.get('clues', [])
    ]

    source_titles = list(set(
        c.source_title for c in characters if c.source_title
    ))

    return GameScenario(
        player_prompt=f"{crime_type} in {setting}",
        setting=setting,
        setting_era=era,
        crime_type=crime_type,
        mystery_type=selected_mystery.get('mystery_type', 'whodunit'),
        crime_description=scenario_data.get('crime_description', ''),
        victim_name=scenario_data.get('victim_name', ''),
        victim_description=scenario_data.get('victim_description', ''),
        discovery_scenario=scenario_data.get('discovery_scenario', ''),
        surface_observations=scenario_data.get('surface_observations', []),
        hidden_details=scenario_data.get('hidden_details', []),
        characters=characters,
        clues=clues,
        solution_chain=scenario_data.get('solution_chain', []),
        timeline=scenario_data.get('timeline', []),
        source_mystery_id=selected_mystery.get('scenario_id', ''),
        source_mystery_title=selected_mystery.get('title',
                                                    selected_mystery.get('source_title', '')),
        character_sources=source_titles,
    )


# ============================================================================
# MAIN: FULL ASSEMBLY PIPELINE
# ============================================================================

def assemble_game(
    player_prompt: str,
    database_dirs: List[str] = None,
) -> GameScenario:
    """
    Full pipeline: prompt → mystery selection → cast assembly → setting rebuild.

    Args:
        player_prompt: Free text from the player, e.g. "An Art Theft in Ancient Athens"
        database_dirs: List of database directories to search. Defaults to all variants.
    """
    if database_dirs is None:
        database_dirs = [
            "./mystery_database",
            "./mystery_database_lean",
            "./mystery_database_rich",
        ]

    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    # Step 1: Parse the player's prompt
    print(f"Player prompt: \"{player_prompt}\"\n")
    print("[1/4] Parsing prompt...")
    parsed = parse_player_prompt(client, player_prompt)
    print(f"  Crime: {parsed.get('crime_type')}")
    print(f"  Setting: {parsed.get('setting_name')} ({parsed.get('setting_era')})")
    print(f"  Culture: {parsed.get('setting_culture')}")
    print(f"  Tone: {parsed.get('tone_hint')}\n")

    # Step 2: Load database and select a mystery
    print("[2/4] Selecting mystery from database...")
    all_scenarios = load_all_scenarios(database_dirs)
    print(f"  Loaded {len(all_scenarios)} scenarios from {len(database_dirs)} databases")

    if not all_scenarios:
        raise ValueError("No scenarios found in any database. Run the extraction pipeline first.")

    selected = select_mystery(all_scenarios, parsed)
    if not selected:
        raise ValueError(f"No compatible mystery found for: {parsed}")

    selected_title = selected.get('title', selected.get('source_title', 'Unknown'))
    print(f"  Selected: \"{selected_title}\"")
    print(f"  Type: {selected.get('mystery_type', 'unknown')}\n")

    # Step 3: Assemble diverse cast
    print("[3/4] Assembling character cast...")
    all_characters = collect_all_characters(all_scenarios)
    print(f"  Character pool: {len(all_characters)} characters from "
          f"{len(all_scenarios)} scenarios")

    cast, culprit = assemble_cast(selected, all_characters)
    if not cast:
        raise ValueError("Failed to assemble cast -- not enough characters in database")

    sources = set(c.get('_source_title', '') for c in cast)
    print(f"  Cast size: {len(cast)}")
    print(f"  Sources used: {len(sources)} different texts")
    for source in sources:
        count = sum(1 for c in cast if c.get('_source_title') == source)
        print(f"    - \"{source}\": {count} character(s)")
    print()

    # Step 4: Rebuild for setting
    print("[4/4] Rebuilding for setting...")
    game = rebuild_for_setting(client, cast, culprit, selected, parsed)

    print(f"\n{'='*50}")
    print(f"GAME READY: {game.game_id}")
    print(f"{'='*50}")
    print(f"Setting: {game.setting}")
    print(f"Crime: {game.crime_description[:100]}...")
    print(f"Victim: {game.victim_name} -- {game.victim_description[:80]}...")
    print(f"Characters: {len(game.characters)}")
    for c in game.characters:
        culprit_tag = " [CULPRIT]" if c.is_culprit else ""
        print(f"  - {c.name} ({c.occupation}) -- {c.role}{culprit_tag}")
        print(f"    from: \"{c.source_title}\" (was: {c.source_character_name})")
    print(f"Clues: {len(game.clues)} ({sum(1 for c in game.clues if c.is_red_herring)} red herrings)")
    print(f"Solution steps: {len(game.solution_chain)}")
    print(f"Timeline events: {len(game.timeline)}")

    # Save the game scenario
    os.makedirs("./active_games", exist_ok=True)
    game_file = f"./active_games/{game.game_id}.json"
    with open(game_file, 'w') as f:
        json.dump(asdict(game), f, indent=2)
    print(f"\nSaved to: {game_file}")

    return game


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "An Art Theft in Ancient Athens"
    assemble_game(prompt)
