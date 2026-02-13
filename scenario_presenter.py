"""
Choose Your Mystery - Scenario Presenter
==========================================

Two delivery modes for presenting a game scenario to players:

1. VISUAL MODE: Generates structured prompts for AI video/image generation.
   Each game phase gets a visual brief that can be fed to a generative video
   API (Runway, Sora, Pika, etc.). Expensive -- use in production only.

2. VERBAL MODE: Pure text narration delivered as spoken descriptions. No video,
   no image generation, no expensive API calls. Used during development and
   testing to validate gameplay without burning through tokens.

CRITICAL DESIGN RULES:
- The crime scene MUST be historically accurate for the setting.
- The crime scene MUST show the crime but NOT defining characteristics of
  suspects. Players discover those through interrogation, not the opening scene.
- Suspects, witnesses, and clues must be present at or near the scene.
- Visual prompts must never reveal who the culprit is.

Usage:
    # Verbal mode (dev/testing -- free)
    python scenario_presenter.py verbal ./active_games/abc123.json

    # Visual mode (production -- generates prompts for video API)
    python scenario_presenter.py visual ./active_games/abc123.json

    # Visual mode with actual video generation (requires API key)
    python scenario_presenter.py visual ./active_games/abc123.json --generate

Requirements:
    pip install anthropic python-dotenv
"""

import os
import re
import sys
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    import anthropic
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    anthropic = None


# ============================================================================
# PRESENTATION DATA MODELS
# ============================================================================

@dataclass
class VisualBrief:
    """A prompt package for one visual scene, ready for a video/image API."""
    phase: str                          # game phase: crime_scene, crime_board, etc.
    scene_label: str                    # human-readable label
    visual_prompt: str                  # the actual prompt for the video API
    camera_direction: str = ""          # camera movement/framing guidance
    mood_lighting: str = ""             # atmosphere/color palette
    duration_seconds: int = 10          # suggested clip length
    aspect_ratio: str = "16:9"
    style_reference: str = ""           # art style guidance
    negative_prompt: str = ""           # what NOT to show
    historical_notes: str = ""          # accuracy constraints


@dataclass
class VerbalNarration:
    """A spoken description for one game phase. Read aloud or displayed as text."""
    phase: str
    scene_label: str
    narration: str                      # the text to read/display
    stage_directions: str = ""          # non-spoken context (sound effects, mood)
    characters_present: List[str] = field(default_factory=list)
    clues_visible: List[str] = field(default_factory=list)


@dataclass
class PresentationPackage:
    """Complete presentation for a game, in either mode."""
    game_id: str
    mode: str  # "visual" or "verbal"
    setting: str
    phases: List[dict] = field(default_factory=list)  # VisualBrief or VerbalNarration as dicts
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat()


# ============================================================================
# GAME PHASES
# ============================================================================

# The presentation follows the game flow from the pitch deck:
# 1. CRIME SCENE - the opening: what happened, where, first impressions
# 2. CRIME BOARD - suspects and evidence overview (who's involved, what's known)
# 3. CHASE LEADS - investigation phase intro (available paths)
#
# Interrogation and info-sharing are interactive -- no pre-rendered content.

GAME_PHASES = [
    "crime_scene",      # The opening reveal
    "crime_board",      # Suspects and evidence layout
    "chase_leads",      # Investigation prompts
]


# ============================================================================
# VERBAL MODE (Dev/Testing - No API Costs)
# ============================================================================

def generate_verbal_crime_scene(scenario: Dict) -> VerbalNarration:
    """
    Generate a spoken narration for the crime scene opening.

    Rules:
    - Describe the setting with historical accuracy
    - Show the crime aftermath (what players see when they arrive)
    - Include surface observations (visible clues)
    - DO NOT describe suspect personalities or behaviors
    - DO NOT hint at who did it
    """
    setting = scenario.get('setting', 'Unknown')
    crime_desc = scenario.get('crime_description', '')
    discovery = scenario.get('discovery_scenario', '')
    surface = scenario.get('surface_observations', [])
    victim_name = scenario.get('victim_name', 'the victim')
    victim_desc = scenario.get('victim_description', '')

    # Build the observation list
    observations = "\n".join(f"  - {obs}" for obs in surface) if surface else "  - The scene awaits investigation."

    narration = f"""The scene unfolds in {setting}.

{discovery}

{crime_desc}

The victim: {victim_name} — {victim_desc}.

As you survey the scene, you observe:
{observations}

The area has been secured. Witnesses and persons of interest have been gathered nearby. The investigation begins now."""

    # Collect which characters are present at the scene
    characters = scenario.get('characters', [])
    present = []
    for c in characters:
        if isinstance(c, dict):
            name = c.get('name', 'Unknown')
            role = c.get('role', 'unknown')
            occupation = c.get('occupation', '')
        else:
            name = getattr(c, 'name', 'Unknown')
            role = getattr(c, 'role', 'unknown')
            occupation = getattr(c, 'occupation', '')
        present.append(f"{name} ({occupation}, {role})")

    # Physical clues visible at the scene
    clues = scenario.get('clues', [])
    visible_clues = []
    for clue in clues:
        if isinstance(clue, dict):
            ctype = clue.get('clue_type', '')
            desc = clue.get('description', '')
        else:
            ctype = getattr(clue, 'clue_type', '')
            desc = getattr(clue, 'description', '')
        if ctype == 'physical':
            visible_clues.append(desc)

    return VerbalNarration(
        phase="crime_scene",
        scene_label="Crime Scene — Opening",
        narration=narration.strip(),
        stage_directions=f"[Setting: {setting}. Mood: tense, investigative. "
                         f"Ambient sounds appropriate to the era and location.]",
        characters_present=present,
        clues_visible=visible_clues,
    )


def generate_verbal_crime_board(scenario: Dict) -> VerbalNarration:
    """
    Generate a spoken narration for the crime board — the suspect/evidence overview.

    Rules:
    - Introduce each suspect by name and occupation ONLY
    - State their apparent connection to the victim
    - DO NOT reveal personality, interrogation behavior, or motives
    - List known physical evidence
    """
    characters = scenario.get('characters', [])
    clues = scenario.get('clues', [])

    # Build suspect introductions (minimal -- no personality reveals)
    suspect_lines = []
    witness_lines = []
    for c in characters:
        if isinstance(c, dict):
            name = c.get('name', 'Unknown')
            role = c.get('role', '')
            occupation = c.get('occupation', '')
            rel = c.get('relationship_to_victim', '')
        else:
            name = getattr(c, 'name', 'Unknown')
            role = getattr(c, 'role', '')
            occupation = getattr(c, 'occupation', '')
            rel = getattr(c, 'relationship_to_victim', '')

        if role == 'suspect':
            line = f"  - {name}, {occupation}"
            if rel:
                line += f" — {rel}"
            suspect_lines.append(line)
        elif role == 'witness':
            line = f"  - {name}, {occupation}"
            if rel:
                line += f" — {rel}"
            witness_lines.append(line)

    suspects_block = "\n".join(suspect_lines) if suspect_lines else "  - No suspects identified yet."
    witnesses_block = "\n".join(witness_lines) if witness_lines else "  - No witnesses have come forward."

    # Evidence summary (physical only, no testimonials yet)
    evidence_lines = []
    for clue in clues:
        if isinstance(clue, dict):
            ctype = clue.get('clue_type', '')
            desc = clue.get('description', '')
            is_red = clue.get('is_red_herring', False)
        else:
            ctype = getattr(clue, 'clue_type', '')
            desc = getattr(clue, 'description', '')
            is_red = getattr(clue, 'is_red_herring', False)
        if ctype == 'physical':
            evidence_lines.append(f"  - {desc}")

    evidence_block = "\n".join(evidence_lines) if evidence_lines else "  - No physical evidence catalogued yet."

    narration = f"""The crime board has been assembled.

SUSPECTS:
{suspects_block}

WITNESSES:
{witnesses_block}

PHYSICAL EVIDENCE:
{evidence_block}

Each person of interest is available for questioning. Evidence can be examined more closely during the investigation phase."""

    return VerbalNarration(
        phase="crime_board",
        scene_label="Crime Board — Suspects & Evidence",
        narration=narration.strip(),
        stage_directions="[Display: crime board layout. Mood: analytical, methodical.]",
        characters_present=[],
        clues_visible=[d for d in evidence_lines] if evidence_lines else [],
    )


def generate_verbal_chase_leads(scenario: Dict) -> VerbalNarration:
    """
    Generate investigation prompts — what leads can players chase?

    Rules:
    - Present available investigation paths without giving away answers
    - Each path should feel like a genuine lead
    - Include both productive paths and red herrings (without labeling them)
    """
    characters = scenario.get('characters', [])
    clues = scenario.get('clues', [])
    setting = scenario.get('setting', 'Unknown')

    lead_lines = []

    # Interrogation leads
    for c in characters:
        if isinstance(c, dict):
            name = c.get('name', 'Unknown')
            role = c.get('role', '')
            occupation = c.get('occupation', '')
        else:
            name = getattr(c, 'name', 'Unknown')
            role = getattr(c, 'role', '')
            occupation = getattr(c, 'occupation', '')

        if role in ('suspect', 'witness'):
            lead_lines.append(f"  - Interrogate {name} ({occupation})")

    # Evidence examination leads
    for clue in clues:
        if isinstance(clue, dict):
            ctype = clue.get('clue_type', '')
            desc = clue.get('description', '')
        else:
            ctype = getattr(clue, 'clue_type', '')
            desc = getattr(clue, 'description', '')

        if ctype == 'physical':
            # Shorten to a lead prompt
            lead_lines.append(f"  - Examine: {desc[:80]}...")

    leads_block = "\n".join(lead_lines) if lead_lines else "  - Begin your investigation."

    narration = f"""The investigation is underway in {setting}.

Available leads:
{leads_block}

Choose where to focus your efforts. Question suspects, examine evidence, or compare notes with fellow investigators.

Remember: you may share most of what you discover with your fellow players — but you must hold something back. Choose wisely what to reveal and what to keep to yourself."""

    return VerbalNarration(
        phase="chase_leads",
        scene_label="Chase Leads — Investigation Phase",
        narration=narration.strip(),
        stage_directions="[Mood: anticipation, strategic. Players now make choices.]",
        characters_present=[],
        clues_visible=[],
    )


def present_verbal(scenario: Dict) -> PresentationPackage:
    """Generate a complete verbal-only presentation for dev/testing."""
    phases = [
        asdict(generate_verbal_crime_scene(scenario)),
        asdict(generate_verbal_crime_board(scenario)),
        asdict(generate_verbal_chase_leads(scenario)),
    ]

    return PresentationPackage(
        game_id=scenario.get('game_id', 'unknown'),
        mode="verbal",
        setting=scenario.get('setting', 'Unknown'),
        phases=phases,
    )


# ============================================================================
# VISUAL MODE (Production - Generates Video/Image Prompts)
# ============================================================================

# Historical accuracy reference for visual prompts
HISTORICAL_VISUAL_NOTES = {
    "ancient": {
        "architecture": "stone columns, marble, terracotta roofs, open courtyards, amphitheaters",
        "clothing": "chitons, togas, draped linen, sandals, bronze jewelry",
        "lighting": "oil lamps, torches, natural sunlight, fire braziers",
        "palette": "warm earth tones, terracotta, white marble, olive greens, aegean blue",
        "avoid": "glass windows, printed fabric patterns, modern materials, steel",
    },
    "medieval": {
        "architecture": "stone castles, timber frames, thatched roofs, cobblestone, gothic arches",
        "clothing": "tunics, cloaks, leather boots, chain mail, wool and linen",
        "lighting": "candles, hearth fires, torches, stained glass light",
        "palette": "dark earth tones, deep reds, forest greens, stone grays, gold accents",
        "avoid": "printed text, modern glass, plastic, bright synthetic colors",
    },
    "renaissance": {
        "architecture": "domed buildings, arched windows, ornate facades, piazzas, frescoed walls",
        "clothing": "doublets, ruffs, velvet cloaks, slashed sleeves, elaborate headwear",
        "lighting": "candelabras, oil paintings on walls, natural light through tall windows",
        "palette": "rich jewel tones, burgundy, gold leaf, deep blue, cream",
        "avoid": "industrial materials, modern furniture, electric lighting",
    },
    "victorian": {
        "architecture": "ornate woodwork, gas lamps, wallpaper, parlors, cobblestone streets",
        "clothing": "top hats, waistcoats, corsets, bustles, gloves, canes",
        "lighting": "gas lamps, candlelight, foggy atmosphere, dim interiors",
        "palette": "dark mahogany, deep greens, burgundy, sepia, fog gray",
        "avoid": "electric lights, cars, modern buildings, bright colors",
    },
    "modern": {
        "architecture": "contemporary buildings, glass and steel, urban environments",
        "clothing": "modern attire appropriate to the specific setting",
        "lighting": "electric lights, neon, screens, natural daylight",
        "palette": "varies by specific setting",
        "avoid": "anachronistic elements",
    },
    "future": {
        "architecture": "sleek surfaces, holographic displays, advanced materials",
        "clothing": "futuristic attire, smart fabrics, functional design",
        "lighting": "LED, holographic, bioluminescent, ambient panels",
        "palette": "cool blues, chrome, neon accents, deep space blacks",
        "avoid": "obviously dated technology, steampunk (unless specified)",
    },
}


def generate_visual_crime_scene(scenario: Dict) -> VisualBrief:
    """
    Generate a video/image prompt for the crime scene opening.

    CRITICAL RULES:
    - Show the crime aftermath, NOT the crime happening
    - Show the setting with full historical accuracy
    - Do NOT show identifiable suspect faces or defining features
    - The victim can be shown (obscured/tasteful) or implied
    - Surface clues should be subtly visible in the scene
    """
    setting = scenario.get('setting', 'Unknown')
    era = scenario.get('setting_era', 'modern')
    crime_desc = scenario.get('crime_description', '')
    discovery = scenario.get('discovery_scenario', '')
    surface_obs = scenario.get('surface_observations', [])
    victim_name = scenario.get('victim_name', '')
    crime_type = scenario.get('crime_type', 'crime')

    hist = HISTORICAL_VISUAL_NOTES.get(era, HISTORICAL_VISUAL_NOTES['modern'])

    # Build the visual prompt
    obs_details = "; ".join(surface_obs[:4]) if surface_obs else "signs of disturbance"

    visual_prompt = (
        f"Cinematic establishing shot of a crime scene in {setting}. "
        f"{hist['architecture']}. "
        f"The scene shows the aftermath of a {crime_type}: {obs_details}. "
        f"Atmospheric and moody. No people in focus — the scene itself tells the story. "
        f"Evidence of the crime is subtly visible. "
        f"Lighting: {hist['lighting']}. "
        f"Color palette: {hist['palette']}. "
        f"Photorealistic, cinematic composition, wide angle."
    )

    negative = (
        f"No modern objects. No anachronisms. {hist['avoid']}. "
        f"No identifiable faces. No gore or graphic violence. "
        f"No text overlays. No UI elements."
    )

    return VisualBrief(
        phase="crime_scene",
        scene_label="Crime Scene — Opening Reveal",
        visual_prompt=visual_prompt,
        camera_direction="Slow dolly forward into the scene. Start wide, gradually reveal details.",
        mood_lighting=f"Dramatic, investigative atmosphere. {hist['lighting']}.",
        duration_seconds=15,
        style_reference=f"Historical accuracy: {era} period. {hist['palette']}.",
        negative_prompt=negative,
        historical_notes=(
            f"Setting: {setting} ({era}). "
            f"Architecture: {hist['architecture']}. "
            f"Clothing visible on victim/background: {hist['clothing']}. "
            f"Must avoid: {hist['avoid']}."
        ),
    )


def generate_visual_crime_board(scenario: Dict) -> VisualBrief:
    """
    Generate a visual prompt for the crime board — a stylized evidence layout.

    This is more of a UI/graphic design prompt than a photorealistic scene.
    Shows suspect silhouettes (not identifiable), evidence items, and connections.
    """
    setting = scenario.get('setting', 'Unknown')
    era = scenario.get('setting_era', 'modern')
    characters = scenario.get('characters', [])
    clues = scenario.get('clues', [])

    hist = HISTORICAL_VISUAL_NOTES.get(era, HISTORICAL_VISUAL_NOTES['modern'])

    num_suspects = sum(
        1 for c in characters
        if (c.get('role') if isinstance(c, dict) else getattr(c, 'role', '')) == 'suspect'
    )
    num_witnesses = sum(
        1 for c in characters
        if (c.get('role') if isinstance(c, dict) else getattr(c, 'role', '')) == 'witness'
    )
    num_clues = len(clues)

    visual_prompt = (
        f"Stylized evidence board for a mystery set in {setting}. "
        f"Era-appropriate materials: {hist['palette']}. "
        f"{num_suspects} suspect silhouettes connected by lines to a central crime marker. "
        f"{num_witnesses} witness silhouettes in a separate cluster. "
        f"{num_clues} evidence items shown as small icons or sketches. "
        f"Red string connections between elements. "
        f"The board itself is made of era-appropriate materials "
        f"(e.g., parchment and wax for ancient, corkboard for modern). "
        f"Top-down camera angle. Dramatic lighting from above."
    )

    return VisualBrief(
        phase="crime_board",
        scene_label="Crime Board — Evidence Layout",
        visual_prompt=visual_prompt,
        camera_direction="Static top-down view, slight zoom into different sections.",
        mood_lighting="Focused spotlight on the board. Dark surroundings.",
        duration_seconds=10,
        style_reference=f"Graphic design meets {era} aesthetic. {hist['palette']}.",
        negative_prompt=(
            f"No identifiable faces on silhouettes. No readable text. "
            f"No modern UI unless era is modern/future. {hist['avoid']}."
        ),
        historical_notes=f"Board materials should match {era} period. {hist['architecture']}.",
    )


def generate_visual_chase_leads(scenario: Dict) -> VisualBrief:
    """
    Generate a visual prompt for the investigation phase introduction.

    Shows the setting from an investigator's perspective — the places and
    people available to investigate, without revealing information.
    """
    setting = scenario.get('setting', 'Unknown')
    era = scenario.get('setting_era', 'modern')

    hist = HISTORICAL_VISUAL_NOTES.get(era, HISTORICAL_VISUAL_NOTES['modern'])

    visual_prompt = (
        f"Atmospheric shot of {setting}, viewed from the perspective of an investigator. "
        f"Multiple paths and doorways lead to different locations. "
        f"Shadowy figures wait in the distance — suspects to be questioned. "
        f"The environment is richly detailed: {hist['architecture']}. "
        f"Clothing on background figures: {hist['clothing']}. "
        f"A sense of mystery and possibility. Multiple leads to follow. "
        f"Lighting: {hist['lighting']}, with shafts of light highlighting different paths. "
        f"Color palette: {hist['palette']}."
    )

    return VisualBrief(
        phase="chase_leads",
        scene_label="Chase Leads — Investigation Begins",
        visual_prompt=visual_prompt,
        camera_direction="Slow pan across the environment, pausing at each investigation path.",
        mood_lighting=f"Anticipatory, branching paths illuminated. {hist['lighting']}.",
        duration_seconds=12,
        style_reference=f"Cinematic, {era} period accuracy. {hist['palette']}.",
        negative_prompt=(
            f"No identifiable character faces. No spoilers. No text. "
            f"{hist['avoid']}."
        ),
        historical_notes=(
            f"Environment must be accurate for {setting} ({era}). "
            f"Architecture: {hist['architecture']}."
        ),
    )


def present_visual(scenario: Dict) -> PresentationPackage:
    """Generate a complete visual presentation with prompts for AI video/image generation."""
    phases = [
        asdict(generate_visual_crime_scene(scenario)),
        asdict(generate_visual_crime_board(scenario)),
        asdict(generate_visual_chase_leads(scenario)),
    ]

    return PresentationPackage(
        game_id=scenario.get('game_id', 'unknown'),
        mode="visual",
        setting=scenario.get('setting', 'Unknown'),
        phases=phases,
    )


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def print_verbal(package: PresentationPackage):
    """Print a verbal presentation to the console, ready to read aloud."""
    print(f"\n{'='*60}")
    print(f"  CHOOSE YOUR MYSTERY — VERBAL PRESENTATION")
    print(f"  Game: {package.game_id} | Setting: {package.setting}")
    print(f"{'='*60}\n")

    for phase_data in package.phases:
        print(f"--- {phase_data['scene_label']} ---")
        print(f"[{phase_data.get('stage_directions', '')}]\n")
        print(phase_data['narration'])

        if phase_data.get('characters_present'):
            print(f"\n  Characters present:")
            for c in phase_data['characters_present']:
                print(f"    • {c}")

        if phase_data.get('clues_visible'):
            print(f"\n  Visible evidence:")
            for c in phase_data['clues_visible']:
                clean = c.replace("  - ", "") if c.startswith("  - ") else c
                print(f"    • {clean}")

        print(f"\n{'─'*60}\n")


def print_visual(package: PresentationPackage):
    """Print visual briefs — the prompts that would go to a video/image API."""
    print(f"\n{'='*60}")
    print(f"  CHOOSE YOUR MYSTERY — VISUAL BRIEFS")
    print(f"  Game: {package.game_id} | Setting: {package.setting}")
    print(f"{'='*60}\n")

    for phase_data in package.phases:
        print(f"--- {phase_data['scene_label']} ---")
        print(f"Duration: {phase_data.get('duration_seconds', '?')}s "
              f"| Aspect: {phase_data.get('aspect_ratio', '16:9')}")
        print(f"\nPROMPT:")
        print(f"  {phase_data['visual_prompt']}")
        print(f"\nCAMERA: {phase_data.get('camera_direction', '')}")
        print(f"MOOD: {phase_data.get('mood_lighting', '')}")
        print(f"STYLE: {phase_data.get('style_reference', '')}")
        print(f"\nNEGATIVE PROMPT:")
        print(f"  {phase_data.get('negative_prompt', '')}")
        print(f"\nHISTORICAL NOTES:")
        print(f"  {phase_data.get('historical_notes', '')}")
        print(f"\n{'─'*60}\n")


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python scenario_presenter.py verbal <game_file.json>")
        print("  python scenario_presenter.py visual <game_file.json>")
        print("  python scenario_presenter.py visual <game_file.json> --generate")
        print()
        print("Modes:")
        print("  verbal  — Text narration only. No API costs. For dev/testing.")
        print("  visual  — Generate video/image prompts for AI generation.")
        print("           Add --generate to actually call the video API.")
        sys.exit(1)

    mode = sys.argv[1].lower()
    game_file = sys.argv[2]
    do_generate = "--generate" in sys.argv

    if mode not in ("verbal", "visual"):
        print(f"ERROR: Unknown mode '{mode}'. Use 'verbal' or 'visual'.")
        sys.exit(1)

    if not os.path.exists(game_file):
        print(f"ERROR: Game file not found: {game_file}")
        sys.exit(1)

    with open(game_file, 'r') as f:
        scenario = json.load(f)

    if mode == "verbal":
        package = present_verbal(scenario)
        print_verbal(package)
    else:
        package = present_visual(scenario)
        print_visual(package)

        if do_generate:
            print("\n[--generate flag detected]")
            print("Video generation API integration is a placeholder.")
            print("To connect a video API (Runway, Sora, Pika, etc.):")
            print("  1. Add API client to this file")
            print("  2. Feed each phase's visual_prompt to the API")
            print("  3. Save generated video/images to ./active_games/<game_id>/media/")

    # Save the presentation package
    output_dir = os.path.dirname(game_file) or "."
    game_id = scenario.get('game_id', 'unknown')
    output_file = os.path.join(output_dir, f"{game_id}_presentation_{mode}.json")
    with open(output_file, 'w') as f:
        json.dump(asdict(package), f, indent=2)
    print(f"\nPresentation saved to: {output_file}")


if __name__ == "__main__":
    main()
