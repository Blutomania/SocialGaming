"""
Mystery Extraction Protocols
==============================

Four graduated protocols for extracting structured parts from mystery source texts.
Grounded in craft criticism by Raymond Chandler, P.D. James, Agatha Christie,
Tana French, Ian Rankin, and Ronald Knox.

Protocol hierarchy (coarsest → finest):
    P1  SKELETON    — 6 load-bearing structural elements (always extract)
    P2  ARCHITECTURE — 8 tactical construction elements (standard extraction)
    P3  CRAFT        — 8 psychological / character-level elements (deep extraction)
    P4  TEXTURE      — 6 atmosphere / voice / inciting-image elements (optional)

Part notation: each part is labelled by protocol and position, e.g. P1.C3, P2.M6.
When a part is extracted from a specific test mystery, it inherits the mystery ID
from test_mysteries.py using the A(n) notation defined there.

Usage:
    from extraction_protocols import PROTOCOLS, get_protocol, extraction_prompt

    protocol = get_protocol("P2")
    prompt   = extraction_prompt("P2", source_text)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================================
# PART DEFINITION
# ============================================================================

@dataclass
class ProtocolPart:
    """
    A single extractable element within a mystery.

    Attributes:
        code         — unique identifier, e.g. "C3" within protocol P1
        name         — human-readable label
        description  — what this part captures
        json_key     — key used in the Claude extraction JSON output
        authority    — which writer/critic named this as structural (citation)
        examples     — brief concrete examples to guide extraction
    """
    code: str
    name: str
    description: str
    json_key: str
    authority: str
    examples: List[str] = field(default_factory=list)


# ============================================================================
# PROTOCOL DEFINITIONS
# ============================================================================

# ---------------------------------------------------------------------------
# P1: SKELETON  (6 parts)
# The load-bearing frame. Every mystery has these. If any is missing the
# mystery cannot function. Extraction at this level answers: "what is this
# story about at its most abstract?"
#
# Authority: P.D. James ("The Art of the Mystery Story"), Christie's
# backward-from-murder method, Chandler's detective archetype essay.
# ---------------------------------------------------------------------------

P1_SKELETON: List[ProtocolPart] = [
    ProtocolPart(
        code="C1",
        name="The Crime",
        description=(
            "Type of offence, method used, and the central question the crime "
            "poses to investigators. Christie always started here — method first, "
            "everything else second."
        ),
        json_key="crime",
        authority="Agatha Christie (Secret Notebooks); Knox Commandment 4",
        examples=[
            "Locked-room stabbing; question: how did the killer exit?",
            "Art theft during a storm; question: did the artifact leave the building?",
            "Staged disappearance; question: is the person actually dead?",
        ],
    ),
    ProtocolPart(
        code="C2",
        name="The Victim",
        description=(
            "Who was harmed and why they were 'killable' — what in their life, "
            "relationships, or secrets made them the target. P.D. James: "
            "'I like to show what makes the victim the victim.'"
        ),
        json_key="victim",
        authority="P.D. James (The Art of the Mystery Story, 1998 Salon interview)",
        examples=[
            "Senior engineer who discovered regulatory fraud",
            "Aristocrat who disinherited his family days before death",
            "Telegraph operator who knew someone's real identity",
        ],
    ),
    ProtocolPart(
        code="C3",
        name="The Closed World",
        description=(
            "The bounded physical or social space that limits who could have "
            "committed the crime. Chandler: the detective moves through a "
            "'closed circle.' French: location is the first decision."
        ),
        json_key="closed_world",
        authority=(
            "P.D. James ('closed circle of suspects'); "
            "Tana French (location as first creative decision)"
        ),
        examples=[
            "Sealed Martian colony dome, no departure for 72 hours",
            "Storm-isolated jungle research station",
            "Victorian deep-sea vessel mid-Atlantic",
        ],
    ),
    ProtocolPart(
        code="C4",
        name="The Culprit and Motive",
        description=(
            "Who committed the crime and why. Christie worked backward from this: "
            "identify murderer and motive first, then construct the rest. "
            "Must be established before suspect architecture is built."
        ),
        json_key="culprit_and_motive",
        authority=(
            "Agatha Christie (Secret Notebooks, Curran); "
            "P.D. James ('shift from who to why')"
        ),
        examples=[
            "Corporate saboteur silencing a whistleblower",
            "Physician preventing a will that funds his rival's research",
            "Trusted aide seizing identity for inheritance",
        ],
    ),
    ProtocolPart(
        code="C5",
        name="The Resolution",
        description=(
            "How order is restored, by whom, and through what mechanism. "
            "P.D. James: resolution must come 'not by luck or divine "
            "intervention — by human intelligence.' Chandler: the detective "
            "as the sole moral agent who can see the truth."
        ),
        json_key="resolution",
        authority=(
            "P.D. James (The Art of the Mystery Story); "
            "Raymond Chandler (The Simple Art of Murder, 1944)"
        ),
        examples=[
            "Technical data log proves alibi was fabricated",
            "Forensic fibers and chemical analysis convict the physician",
            "Genetic anomaly exposes the clone's identity",
        ],
    ),
    ProtocolPart(
        code="C6",
        name="The Investigator",
        description=(
            "The lens through which the reader experiences the mystery. "
            "May be a detective, a suspect, a victim, or an outsider. "
            "French: the detective's POV is not intrinsically heroic — "
            "consider whose perspective shapes the truth."
        ),
        json_key="investigator",
        authority=(
            "Raymond Chandler ('down these mean streets'); "
            "Tana French (rotating narrator; detective POV questioned)"
        ),
        examples=[
            "Official detective with institutional authority",
            "Suspect who is also a victim of another crime",
            "Outsider drawn in by proximity to the closed world",
        ],
    ),
]


# ---------------------------------------------------------------------------
# P2: ARCHITECTURE  (8 parts)
# Tactical construction decisions. These are the elements Christie plotted
# in her notebooks before writing a word. Knox's commandments live here.
# ---------------------------------------------------------------------------

P2_ARCHITECTURE: List[ProtocolPart] = [
    ProtocolPart(
        code="M1",
        name="Suspect Architecture",
        description=(
            "The full cast of suspects — how many, spread of means/motive/"
            "opportunity, and how they are differentiated. "
            "P.D. James: 'each with motive, means and opportunity.' "
            "Knox Commandment: criminal must appear early."
        ),
        json_key="suspect_architecture",
        authority=(
            "P.D. James; Knox (Detective Fiction commandments, 1929)"
        ),
        examples=[
            "Four suspects: spouse (motive: disinheritance), physician (rivalry), "
            "niece (will), butler (witness only)",
            "Three insider researchers, one local guide falsely implicated",
        ],
    ),
    ProtocolPart(
        code="M2",
        name="The Red Herring",
        description=(
            "Deliberate misdirection, planned before writing, not accidental. "
            "Christie's notebooks show she listed false trails explicitly. "
            "Must be logically consistent — never cheating the reader."
        ),
        json_key="red_herring",
        authority="Agatha Christie (Secret Notebooks); Knox Commandment 8",
        examples=[
            "Life-support malfunction staged to look accidental",
            "Anarchist pamphlets planted at an industrial sabotage scene",
            "Rival corporation framed via planted biometric data",
        ],
    ),
    ProtocolPart(
        code="M3",
        name="Clue Fairness",
        description=(
            "The principle that every clue available to the investigator must "
            "also be available to the reader when the investigator sees it. "
            "P.D. James: 'the detective can know nothing which the reader "
            "isn't also told.' Knox Commandment 8."
        ),
        json_key="clue_fairness",
        authority=(
            "P.D. James (The Art of the Mystery Story); Knox Commandment 8"
        ),
        examples=[
            "Morse log anomaly shown to reader before investigator interprets it",
            "Timestamp discrepancy on photograph described in scene text",
            "Engineering annotation visible in diagram shown during exposition scene",
        ],
    ),
    ProtocolPart(
        code="M4",
        name="The Social World",
        description=(
            "Power structures, hierarchies, patronage networks, and who owes "
            "whom. Rankin: Edinburgh class and institutional power are character. "
            "This determines who can plausibly have access, cover, and motive."
        ),
        json_key="social_world",
        authority=(
            "Ian Rankin (Rebus interviews; Edinburgh as character); "
            "P.D. James (patronage networks in court mysteries)"
        ),
        examples=[
            "Rigid Victorian naval hierarchy concealing officer complicity",
            "Academic vs. commercial interests at a jungle research station",
            "Investor pressure and financial desperation at an industrial exposition",
        ],
    ),
    ProtocolPart(
        code="M5",
        name="The Alibi",
        description=(
            "False or genuine account of suspect's whereabouts. Christie's "
            "notebooks treat alibi construction as an explicit planning step — "
            "some alibis are airtight (innocent suspects), some are fabricated "
            "(the culprit), some are partially true."
        ),
        json_key="alibi",
        authority="Agatha Christie (Secret Notebooks, Curran analysis)",
        examples=[
            "Physician claims he was in his room; string-through-keyhole disproves it",
            "Corporate aide's alibi collapses when microsecond gaps appear in logs",
            "Officer's past creates a motive that his stated alibi cannot cover",
        ],
    ),
    ProtocolPart(
        code="M6",
        name="The Reveal Mechanic",
        description=(
            "How the solution is demonstrated — not just stated — to the "
            "investigator and reader. Often a technical or psychological "
            "impossibility exposed. French: revelation timing matters; "
            "Christie: often a material or logical detail the culprit overlooked."
        ),
        json_key="reveal_mechanic",
        authority=(
            "Agatha Christie (method as reveal anchor); "
            "Tana French (revelation placed 2/3 through for maximum impact)"
        ),
        examples=[
            "Anachronistic ink composition in a forged manuscript",
            "Genetic anomaly in a clone's biometric signature",
            "Hidden message decoded from deliberate Morse errors",
        ],
    ),
    ProtocolPart(
        code="M7",
        name="Media and Audience",
        description=(
            "How the crime is perceived, packaged, and narrated by the world "
            "around it — press, institutions, public opinion. Chandler: corrupt "
            "institutions shape what counts as truth. Flynn: the media creates "
            "a narrative that investigators must fight against."
        ),
        json_key="media_and_audience",
        authority=(
            "Raymond Chandler (The Simple Art of Murder); "
            "Gillian Flynn (Gone Girl; packaging of tragedy)"
        ),
        examples=[
            "Supernatural folklore weaponised by the crew to explain a disappearance",
            "Inventor publicly blamed for sabotage he did not commit",
            "Rival corporation's reputation used to absorb suspicion",
        ],
    ),
    ProtocolPart(
        code="M8",
        name="The Investigator's Wound",
        description=(
            "The psychological vulnerability the case exploits in the investigator. "
            "French: 'the situation puts pressure on the character's weak spots.' "
            "Rankin: Rebus ages in real time; each case tests a different scar."
        ),
        json_key="investigator_wound",
        authority=(
            "Tana French (character wound as structural engine); "
            "Ian Rankin (Rebus's evolving demons across 25 novels)"
        ),
        examples=[
            "Detective whose previous case was unsolved by the same method",
            "Investigator whose institutional loyalty conflicts with the truth",
            "Outsider whose emotional connection to the closed world compromises judgment",
        ],
    ),
]


# ---------------------------------------------------------------------------
# P3: CRAFT  (8 parts)
# Psychological and character-level granularity. French, Flynn, and Rankin
# name these in interviews about specific books, not the genre in general.
# ---------------------------------------------------------------------------

P3_CRAFT: List[ProtocolPart] = [
    ProtocolPart(
        code="F1",
        name="Victim's Enemies",
        description=(
            "The specific web of people with grievance against the victim — "
            "not just motive but the texture of the relationship. "
            "P.D. James: 'someone who has made enemies; important to show why.'"
        ),
        json_key="victims_enemies",
        authority="P.D. James (multiple interviews on victim construction)",
        examples=[
            "Engineer who had already filed two internal complaints naming the culprit",
            "Aristocrat who publicly humiliated the physician at a dinner party",
            "Telegraph operator who was blackmailing the officer over a decade-old incident",
        ],
    ),
    ProtocolPart(
        code="F2",
        name="Suspect's Wound",
        description=(
            "Each suspect needs a plausible reason to look guilty — an internal "
            "vulnerability the crime activates. French: pressure on weak spots "
            "applies to suspects as much as to investigators. The false suspect "
            "looks guilty not because they are, but because the crime exposes "
            "something they were hiding anyway."
        ),
        json_key="suspect_wounds",
        authority=(
            "Tana French (pressure on weak spots; character as core mystery)"
        ),
        examples=[
            "Niece was hiding that she had seen the will — not a suspect, but acts like one",
            "Local guide has an unrelated criminal history that makes flight look like guilt",
            "Rival inventor's financial desperation makes sabotage plausible but wrong",
        ],
    ),
    ProtocolPart(
        code="F3",
        name="The Unreliable Frame",
        description=(
            "Whose account of events cannot be fully trusted, and why. "
            "Flynn: 'both narrators are consummate liars.' "
            "French: 'we are all unreliable narrators' — the mystery reader "
            "must learn to read the narrator's distortions as data."
        ),
        json_key="unreliable_frame",
        authority=(
            "Gillian Flynn (Gone Girl; unreliable narration as genre engine); "
            "Tana French (CrimeReads: 'We're All Unreliable Narrators')"
        ),
        examples=[
            "Lady Ashworth describes husband's paranoia but omits her own motive",
            "Ship officer's account of the night omits forty minutes he cannot explain",
            "Biotech aide's testimony is technically true but assembled to mislead",
        ],
    ),
    ProtocolPart(
        code="F4",
        name="Setting as Constraint",
        description=(
            "How the physical or social environment limits what actions are "
            "possible — and how the culprit used or exploited those limits. "
            "Rankin: the prison walls are 'partly the fun of it.' "
            "Christie: closed environments force specific solutions."
        ),
        json_key="setting_as_constraint",
        authority=(
            "Ian Rankin (Midnight and Blue; prison as structural constraint); "
            "Agatha Christie (island, train, ship as solution-shapers)"
        ),
        examples=[
            "Colony dome's life-support logs are the only clock — and the culprit controlled them",
            "Storm cut satellite communications, so the theft window is precisely bounded",
            "Royal library's access log is the only record of who held the manuscript",
        ],
    ),
    ProtocolPart(
        code="F5",
        name="Evidence Type",
        description=(
            "The specific category of evidence that cracks the case: physical, "
            "testimonial, forensic, documentary, or environmental. Christie "
            "classified evidence types as an explicit planning step in her notebooks."
        ),
        json_key="evidence_type",
        authority="Agatha Christie (Secret Notebooks); Knox Commandment 4",
        examples=[
            "Environmental data log (sensor readings as alibi-breaker)",
            "Ink composition / material analysis (anachronism in forgery)",
            "Biometric transaction log with microsecond gaps (timing impossibility)",
        ],
    ),
    ProtocolPart(
        code="F6",
        name="The False Suspect",
        description=(
            "One character who bears maximum suspicion but is innocent — planted "
            "by the narrative (and sometimes by the culprit) to protect the real "
            "culprit. Knox: the criminal must not be the character whose thoughts "
            "the reader has been given access to."
        ),
        json_key="false_suspect",
        authority=(
            "Agatha Christie (false suspect as shield for real culprit); "
            "Knox Commandment (no thought-access to the criminal)"
        ),
        examples=[
            "Local guide implicated by planted evidence at Amazon station",
            "Foreign envoy blamed in Abbasid court forgery",
            "Rival corporation framed by planted biometric data",
        ],
    ),
    ProtocolPart(
        code="F7",
        name="The Technical Detail",
        description=(
            "The specific domain knowledge that makes the method possible — "
            "and ultimately exposes the culprit. Knox Commandment 4: no "
            "unexplained science. The technical detail must be either "
            "pre-established as a character's expertise or demonstrated "
            "to the reader before it becomes the solution."
        ),
        json_key="technical_detail",
        authority=(
            "Knox Commandment 4 (plausible method, no unexplained science); "
            "Agatha Christie (expertise as alibi-builder and reveal-engine)"
        ),
        examples=[
            "String-through-keyhole technique known from forensic medicine",
            "Aether engine requires pre-event access with a specific calibration key",
            "Morse code deliberately corrupted in a pattern only a trained operator would set",
        ],
    ),
    ProtocolPart(
        code="F8",
        name="Moral Ambiguity",
        description=(
            "Why the culprit is understandable — not merely evil. Chandler: "
            "the detective's 'flexible conception of right and wrong' is what "
            "lets them perceive truth. A culprit with a comprehensible motivation "
            "deepens the mystery; a pure villain flattens it."
        ),
        json_key="moral_ambiguity",
        authority=(
            "Raymond Chandler (The Simple Art of Murder; moral complexity); "
            "P.D. James ('shift from who to why')"
        ),
        examples=[
            "Physician killed to protect his life's work, not from personal hatred",
            "Researcher stole artifact to return it to its people, not for profit",
            "Officer silenced the blackmailer to protect a family, not himself",
        ],
    ),
]


# ---------------------------------------------------------------------------
# P4: TEXTURE  (6 parts)
# Atmosphere, voice, and the inciting image. Writers name these when talking
# about specific books, not the genre. Optional enrichment layer.
# ---------------------------------------------------------------------------

P4_TEXTURE: List[ProtocolPart] = [
    ProtocolPart(
        code="F9",
        name="The Sidekick / Foil",
        description=(
            "The Watson function: a character slightly below reader intelligence "
            "whose transparent thinking helps the reader track the investigation. "
            "Knox Commandment 9. Chandler: the confidant who often perishes."
        ),
        json_key="sidekick",
        authority=(
            "Knox Commandment 9; "
            "Raymond Chandler ('close friend who generally perishes')"
        ),
        examples=[
            "The butler who notices the wrong things and says so aloud",
            "A junior researcher who voices the false hypothesis the reader considers",
        ],
    ),
    ProtocolPart(
        code="F10",
        name="Cascade of Deaths",
        description=(
            "Secondary crimes or deaths that follow the primary crime — "
            "escalation that raises stakes and often misdirects investigation. "
            "Chandler: 'deaths usually occur in a cascade.' "
            "Each new death narrows the suspect pool or opens a new branch."
        ),
        json_key="cascade_of_deaths",
        authority="Raymond Chandler (The Simple Art of Murder; formula analysis)",
        examples=[
            "Second engineer killed when she starts asking questions about the logs",
            "Local guide disappears after being questioned about the storm night",
        ],
    ),
    ProtocolPart(
        code="F11",
        name="The Public Spectacle Moment",
        description=(
            "When the crime enters a wider social stage — press coverage, "
            "public accusation, institutional response. Flynn: media as Greek "
            "chorus. Rankin: institutional exposure as the real drama. "
            "This moment often forces the investigator's hand."
        ),
        json_key="public_spectacle",
        authority=(
            "Gillian Flynn (Gone Girl; media packaging of tragedy); "
            "Ian Rankin (institutional exposure in Rebus novels)"
        ),
        examples=[
            "Inventor publicly accused at the exposition before investors",
            "Executive's death reported as natural; clone begins attending board meetings",
        ],
    ),
    ProtocolPart(
        code="F12",
        name="The Inciting Image",
        description=(
            "The single vivid sensory detail or image that the writer started "
            "from — the seed of the mystery. French: a battered suitcase in a "
            "skip. Flynn: a man coming home to find the door wide open. "
            "Not always in the final text, but locatable in development."
        ),
        json_key="inciting_image",
        authority=(
            "Tana French (suitcase-in-a-skip origin of Faithful Place); "
            "Gillian Flynn (open door image as Gone Girl genesis)"
        ),
        examples=[
            "An empty chair at the telegraph desk with the receiver still warm",
            "A manuscript whose ink smells wrong to the scholar who opens it",
            "A colony dome status board showing all life-support as nominal at 03:00",
        ],
    ),
    ProtocolPart(
        code="F13",
        name="Atmospheric Register",
        description=(
            "The dominant sensory and tonal atmosphere — the 'weather' of the "
            "mystery. Rankin: Edinburgh is character. French: setting is chosen "
            "before characters. This register shapes what the reader believes "
            "is possible and what feels sinister."
        ),
        json_key="atmospheric_register",
        authority=(
            "Ian Rankin (Edinburgh as character; music as mood); "
            "Tana French (dense atmospheric prose as genre signature)"
        ),
        examples=[
            "Cold sterile colony air, constant hum of life-support, artificial daylight",
            "Victorian gaslight and Atlantic fog, wood creaking, code tapping through the night",
            "Cyberpunk neon rain, genetic scan checkpoints, the smell of a city that never sleeps",
        ],
    ),
    ProtocolPart(
        code="F14",
        name="The Detective's Voice",
        description=(
            "The distinctive narrative register of the investigator — what they "
            "notice, what they name, how they speak to themselves. "
            "Chandler: the style IS the detective. French: the narrator's "
            "distortions are data. This is what makes a mystery a literary object "
            "rather than a puzzle."
        ),
        json_key="detective_voice",
        authority=(
            "Raymond Chandler (The Simple Art of Murder; style as character); "
            "Tana French (first-person narrator as unreliable and revelatory)"
        ),
        examples=[
            "Terse, sardonic; notices exits before he notices faces",
            "Overly formal; uses institutional language to suppress emotional response",
            "Academic; misreads people but reads material evidence precisely",
        ],
    ),
]


# ============================================================================
# PROTOCOL REGISTRY
# ============================================================================

@dataclass
class Protocol:
    """
    A complete extraction protocol — one of the four granularity levels.

    Attributes:
        id          — "P1", "P2", "P3", or "P4"
        name        — human-readable name
        description — what this protocol captures and when to use it
        parts       — ordered list of ProtocolPart definitions
    """
    id: str
    name: str
    description: str
    parts: List[ProtocolPart]

    def part_keys(self) -> List[str]:
        """Return the json_key for each part in order."""
        return [p.json_key for p in self.parts]

    def part_by_code(self, code: str) -> Optional[ProtocolPart]:
        """Look up a part by its code (e.g. 'C3', 'M6')."""
        for p in self.parts:
            if p.code == code:
                return p
        return None


PROTOCOLS: dict[str, Protocol] = {
    "P1": Protocol(
        id="P1",
        name="Skeleton",
        description=(
            "Six load-bearing structural elements. Every mystery has these. "
            "If any is missing the mystery cannot function as a coherent narrative. "
            "Use P1 for rapid triage: does this source contain a usable mystery?"
        ),
        parts=P1_SKELETON,
    ),
    "P2": Protocol(
        id="P2",
        name="Architecture",
        description=(
            "Eight tactical construction elements. The decisions Christie plotted "
            "in her notebooks before writing a word. Knox's commandments live here. "
            "Use P2 for standard database ingestion — enough to generate and validate."
        ),
        parts=P2_ARCHITECTURE,
    ),
    "P3": Protocol(
        id="P3",
        name="Craft",
        description=(
            "Eight psychological and character-level elements. French, Flynn, and "
            "Rankin name these when discussing specific books, not the genre in general. "
            "Use P3 for deep extraction of character-driven mysteries with literary ambitions."
        ),
        parts=P3_CRAFT,
    ),
    "P4": Protocol(
        id="P4",
        name="Texture",
        description=(
            "Six atmosphere, voice, and inciting-image elements. Optional enrichment "
            "layer. Use P4 when building a mystery whose tone, register, or narrative "
            "voice will be actively used in generation (not just structure)."
        ),
        parts=P4_TEXTURE,
    ),
}


# ============================================================================
# MAPPING: existing part_types → protocol codes
# ============================================================================
#
# The eight part_types used in test_mysteries.py map onto the protocol taxonomy
# as follows. This table is the bridge between the existing test corpus notation
# and the full protocol system.
#
# test_mysteries part_type   →  protocol code  →  protocol level
# ─────────────────────────────────────────────────────────────────
# "crime_type"               →  P1.C1           →  P1 Skeleton
# "setting_element"          →  P1.C3 + P3.F4   →  P1 + P3
# "motive"                   →  P1.C4           →  P1 Skeleton
# "suspect_archetype"        →  P2.M1           →  P2 Architecture
# "red_herring"              →  P2.M2           →  P2 Architecture
# "reveal_mechanic"          →  P2.M6           →  P2 Architecture
# "social_dynamic"           →  P2.M4           →  P2 Architecture
# "evidence_type"            →  P3.F5           →  P3 Craft
# ─────────────────────────────────────────────────────────────────
# The test corpus covers: all of P1, four of eight P2, one of eight P3.
# P2.M3 (clue fairness), P2.M5 (alibi), P2.M7 (media), P2.M8 (wound),
# and all of P3/P4 are not yet extracted for the six test mysteries.

PART_TYPE_TO_PROTOCOL: dict[str, list[str]] = {
    "crime_type":        ["P1.C1"],
    "setting_element":   ["P1.C3", "P3.F4"],
    "motive":            ["P1.C4"],
    "suspect_archetype": ["P2.M1"],
    "red_herring":       ["P2.M2"],
    "reveal_mechanic":   ["P2.M6"],
    "social_dynamic":    ["P2.M4"],
    "evidence_type":     ["P3.F5"],
}


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_protocol(protocol_id: str) -> Protocol:
    """
    Retrieve a Protocol by ID.

    Args:
        protocol_id: "P1", "P2", "P3", or "P4"

    Returns:
        Protocol dataclass

    Raises:
        KeyError if ID not found
    """
    key = protocol_id.upper()
    if key not in PROTOCOLS:
        raise KeyError(
            f"Protocol '{protocol_id}' not found. Valid IDs: {list(PROTOCOLS.keys())}"
        )
    return PROTOCOLS[key]


def extraction_prompt(
    protocol_id: str,
    source_text: str,
    max_text_chars: int = 6000,
) -> str:
    """
    Build a Claude extraction prompt for a given protocol and source text.

    The prompt requests a JSON object whose keys are the json_key fields of
    each ProtocolPart in the protocol. Each key maps to a dict with:
        - value     : the extracted content
        - confidence: "high" | "medium" | "low"
        - quote     : verbatim supporting quote from the source (max 120 chars)

    Args:
        protocol_id:     "P1", "P2", "P3", or "P4"
        source_text:     raw mystery text to extract from
        max_text_chars:  truncation limit for the source (API cost control)

    Returns:
        Formatted prompt string ready to send to Claude
    """
    protocol = get_protocol(protocol_id)
    truncated = source_text[:max_text_chars]

    parts_spec = "\n".join(
        f'  "{p.json_key}": {{\n'
        f'    // {p.name}: {p.description[:120]}\n'
        f'    // Examples: {"; ".join(p.examples[:2])}\n'
        f'    "value": <string>,\n'
        f'    "confidence": "high" | "medium" | "low",\n'
        f'    "quote": <verbatim supporting quote, max 120 chars or null>\n'
        f'  }}'
        for p in protocol.parts
    )

    return f"""You are extracting structured mystery data using Protocol {protocol.id} ({protocol.name}).

{protocol.description}

SOURCE TEXT (excerpt):
\"\"\"
{truncated}
\"\"\"

Extract the following {len(protocol.parts)} elements. Respond ONLY with valid JSON.
If an element is absent from the source, set "value" to null and "confidence" to "low".

{{
{parts_spec}
}}"""


def combined_prompt(
    protocol_ids: List[str],
    source_text: str,
    max_text_chars: int = 8000,
) -> str:
    """
    Build a single Claude prompt that extracts across multiple protocols at once.
    Use when source text is rich enough to support P1+P2 or P1+P2+P3 in one pass.

    Args:
        protocol_ids:    e.g. ["P1", "P2"]
        source_text:     raw mystery text
        max_text_chars:  truncation limit

    Returns:
        Formatted multi-protocol prompt string
    """
    all_parts: List[ProtocolPart] = []
    for pid in protocol_ids:
        all_parts.extend(get_protocol(pid).parts)

    truncated = source_text[:max_text_chars]
    protocol_label = " + ".join(
        f"{pid} ({PROTOCOLS[pid.upper()].name})" for pid in protocol_ids
    )

    parts_spec = "\n".join(
        f'  "{p.json_key}": {{\n'
        f'    "protocol": "{_find_protocol(p.code)}",\n'
        f'    "part": "{p.code} — {p.name}",\n'
        f'    "value": <string>,\n'
        f'    "confidence": "high" | "medium" | "low",\n'
        f'    "quote": <verbatim supporting quote, max 120 chars or null>\n'
        f'  }}'
        for p in all_parts
    )

    return f"""You are extracting structured mystery data using Protocols {protocol_label}.

SOURCE TEXT (excerpt):
\"\"\"
{truncated}
\"\"\"

Extract all {len(all_parts)} elements below. Respond ONLY with valid JSON.
If an element is absent, set "value" to null and "confidence" to "low".

{{
{parts_spec}
}}"""


def _find_protocol(part_code: str) -> str:
    """Return the protocol ID that owns a given part code."""
    for pid, protocol in PROTOCOLS.items():
        for part in protocol.parts:
            if part.code == part_code:
                return pid
    return "unknown"


def list_protocols() -> None:
    """Print a summary of all four protocols and their parts."""
    print("\n=== Mystery Extraction Protocols ===\n")
    for pid, protocol in PROTOCOLS.items():
        print(f"  [{pid}] {protocol.name}  ({len(protocol.parts)} parts)")
        for part in protocol.parts:
            print(f"        {part.code}  {part.name}")
            print(f"              → {part.description[:80]}...")
        print()


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    list_protocols()

    print("\n=== Part-type → Protocol mapping ===\n")
    print("  (How the existing test_mysteries.py part_types map to protocols)\n")
    for pt, codes in PART_TYPE_TO_PROTOCOL.items():
        print(f"  {pt:<25} →  {', '.join(codes)}")
    print()
