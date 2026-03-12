"""
Choose Your Mystery - Part Registry
=====================================

A catalogue of pre-validated building blocks that the CLI samples from
before calling Claude.  Every part already passes check_parts(), so the
pre-generation gate is essentially free (no API calls needed).

Sampling strategy
-----------------
call sample_parts(n_suspects, n_witnesses) to get a ready-to-use dict of
  {crime, victim, suspects[], witnesses[]}

call resample_part(part_type, exclude_names) to swap out a single weak part
after the pre-generation gate fires.

The generation prompt builder (cli.py) injects the sampled parts as
concrete examples so Claude knows the depth of alibi/secret expected.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional


# ============================================================================
# CRIME TEMPLATES
# ============================================================================

_CRIMES: List[Dict] = [
    {
        "part_type": "crime",
        "type": "murder",
        "what_happened": (
            "The victim was found poisoned in a locked room, a trace of an exotic "
            "compound detected in the half-finished glass of wine on the desk."
        ),
        "when": "Between 9 pm and midnight",
        "initial_discovery": "A servant noticed the light still burning at dawn and raised the alarm.",
    },
    {
        "part_type": "crime",
        "type": "murder",
        "what_happened": (
            "The victim was struck from behind with a heavy instrument in the library; "
            "the body was discovered slumped over an open ledger, ink still wet."
        ),
        "when": "During the dinner hour, while guests were at table",
        "initial_discovery": "A guest who slipped away to retrieve a book found the body.",
    },
    {
        "part_type": "crime",
        "type": "theft",
        "what_happened": (
            "The priceless centrepiece jewel vanished from its display case overnight; "
            "the lock was picked cleanly and the alarm wire cut from inside the building."
        ),
        "when": "Sometime between midnight and six in the morning",
        "initial_discovery": "The curator arrived at opening and found the empty case.",
    },
    {
        "part_type": "crime",
        "type": "murder",
        "what_happened": (
            "The victim was pushed from the upper balcony and fell to the courtyard below; "
            "scuff marks on the railing and a torn button suggest a struggle preceded the fall."
        ),
        "when": "Just after the evening reception ended and most guests had retired",
        "initial_discovery": "A night-watchman heard the impact and found the body minutes later.",
    },
    {
        "part_type": "crime",
        "type": "sabotage",
        "what_happened": (
            "Critical machinery was deliberately disabled moments before a high-stakes "
            "demonstration; a component was removed and replaced with a near-identical "
            "but non-functional copy."
        ),
        "when": "In the hour before the scheduled demonstration",
        "initial_discovery": "The lead engineer noticed the failure as the demonstration began.",
    },
]


# ============================================================================
# VICTIM TEMPLATES
# ============================================================================

_VICTIMS: List[Dict] = [
    {
        "part_type": "victim",
        "role": "victim",
        "name": None,   # caller fills in from setting
        "occupation": "Wealthy industrialist",
        "personality": (
            "A calculating man who had quietly squeezed several business partners out of "
            "profitable ventures over the past decade, collecting enemies along the way."
        ),
        "secrets": (
            "He had been forging signatures on partnership agreements for years, "
            "diverting royalties into a private account his family knew nothing about."
        ),
    },
    {
        "part_type": "victim",
        "role": "victim",
        "name": None,
        "occupation": "Celebrated art dealer",
        "personality": (
            "Charming in public, she cultivated an air of impeccable taste while privately "
            "trafficking in stolen antiquities through a network of front galleries."
        ),
        "secrets": (
            "She had blackmailed at least two collectors into silence after they discovered "
            "the provenance of works they had purchased from her."
        ),
    },
    {
        "part_type": "victim",
        "role": "victim",
        "name": None,
        "occupation": "Senior government official",
        "personality": (
            "Publicly incorruptible and widely admired, he had in private accepted bribes "
            "from several contractors and used the funds to cover catastrophic gambling debts."
        ),
        "secrets": (
            "He had suppressed an internal inquiry three years ago that would have exposed "
            "a colleague — in exchange for a substantial payment routed through a solicitor."
        ),
    },
]


# ============================================================================
# SUSPECT TEMPLATES
# ============================================================================

_SUSPECTS: List[Dict] = [
    {
        "part_type": "suspect",
        "role": "suspect",
        "archetype": "estranged_heir",
        "occupation": "Idle heir",
        "personality": "Resentful and prone to dramatic outbursts when money is mentioned.",
        "motive": "Was written out of the will two months ago after a confrontation over debts; stands to regain everything if the new will is invalidated.",
        "alibi": "Claims to have been at his club until midnight; the doorman recalls him leaving at half past nine.",
        "secrets": (
            "He hired a private inquiry agent six weeks ago to locate a copy of the earlier "
            "will that would restore his inheritance — the agent found it."
        ),
    },
    {
        "part_type": "suspect",
        "role": "suspect",
        "archetype": "business_rival",
        "occupation": "Competing merchant",
        "personality": "Cool and methodical, hides fury behind elaborate courtesies.",
        "motive": "The victim had just secured a contract that would have driven her firm into bankruptcy within the year.",
        "alibi": "Says she was reviewing ledgers with her bookkeeper all evening; the bookkeeper's account is inconsistent on the timing.",
        "secrets": (
            "She had approached a foreign buyer willing to purchase the contract rights "
            "illegally — a deal that only works if the victim is no longer party to it."
        ),
    },
    {
        "part_type": "suspect",
        "role": "suspect",
        "archetype": "scorned_lover",
        "occupation": "Portrait artist",
        "personality": "Passionate and impulsive, oscillates between charm and cold silence.",
        "motive": "The victim ended a two-year affair abruptly and threatened to reveal it to ruin the suspect's reputation.",
        "alibi": "Claims to have been working alone in the studio; a neighbour reports seeing the studio light extinguished before nine.",
        "secrets": (
            "He had written a series of letters to the victim containing explicit threats "
            "that, if discovered, would confirm both motive and opportunity."
        ),
    },
    {
        "part_type": "suspect",
        "role": "suspect",
        "archetype": "corrupt_associate",
        "occupation": "Trusted solicitor",
        "personality": "Nervously deferential; sweats visibly when questioned directly.",
        "motive": "The victim had discovered the suspect had been embezzling from an estate account for three years and had given him one week to repay or face prosecution.",
        "alibi": "Insists he spent the evening at a dinner party; left early, citing illness, at a time that puts him near the scene.",
        "secrets": (
            "He had already transferred the stolen funds offshore and was preparing to flee "
            "the country before the victim's deadline expired."
        ),
    },
    {
        "part_type": "suspect",
        "role": "suspect",
        "archetype": "disgraced_scientist",
        "occupation": "Former research director",
        "personality": "Brilliant but bitter; speaks in precise, clipped sentences and rarely makes eye contact.",
        "motive": "The victim had stolen and published her research under his own name, ending her academic career.",
        "alibi": "Claims she was at a public lecture across town; no one who knows her recalls seeing her there.",
        "secrets": (
            "She had recently acquired the chemical compound used in the crime through a "
            "university contact, ostensibly for unrelated research purposes."
        ),
    },
    {
        "part_type": "suspect",
        "role": "suspect",
        "archetype": "desperate_spouse",
        "occupation": "Socialite",
        "personality": "Polished exterior concealing mounting panic; keeps checking the time.",
        "motive": "Discovered the victim was about to sign divorce papers that would have left her with almost nothing under the terms of the pre-nuptial agreement.",
        "alibi": "Says she retired early with a headache; her maid did not check on her after nine o'clock.",
        "secrets": (
            "She had consulted a lawyer three weeks ago about whether a spouse's death "
            "before divorce proceedings would void the pre-nuptial agreement — it would."
        ),
    },
]


# ============================================================================
# WITNESS TEMPLATES
# ============================================================================

_WITNESSES: List[Dict] = [
    {
        "part_type": "witness",
        "role": "witness",
        "archetype": "loyal_servant",
        "occupation": "Head butler",
        "personality": "Correct and discreet; volunteers nothing but answers questions precisely.",
        "alibi": "Was overseeing the clearing of the dining room from eight until half past ten, in full view of the kitchen staff.",
        "secrets": (
            "He witnessed an argument between the victim and a suspect earlier that "
            "afternoon but said nothing to the authorities out of misplaced loyalty."
        ),
    },
    {
        "part_type": "witness",
        "role": "witness",
        "archetype": "nervous_secretary",
        "occupation": "Personal secretary",
        "personality": "Eager to please, prone to over-explaining; clearly concealing anxiety.",
        "alibi": "Was typing correspondence in the outer office until at least ten-thirty; the typewritten pages are timestamped.",
        "secrets": (
            "She overheard a phone call in which the victim arranged a secret meeting "
            "for that evening, but fears implicating herself by revealing it."
        ),
    },
    {
        "part_type": "witness",
        "role": "witness",
        "archetype": "inquisitive_neighbour",
        "occupation": "Retired magistrate",
        "personality": "Sharp-eyed and blunt; makes neighbours uncomfortable with how much he notices.",
        "alibi": "Was walking his dog along the street between nine and ten; saw several people entering and leaving the property.",
        "secrets": (
            "He recognised one of the visitors from a court case he presided over years ago "
            "involving fraud — a detail he has not yet volunteered."
        ),
    },
    {
        "part_type": "witness",
        "role": "witness",
        "archetype": "frightened_staff",
        "occupation": "Kitchen maid",
        "personality": "Young, easily flustered; speaks quickly and trails off when nervous.",
        "alibi": "Was in the servants' hall all evening after finishing duties at eight; three colleagues can confirm.",
        "secrets": (
            "She was asked by a suspect to deliver a note to the victim's room at nine "
            "o'clock and did so without reading it — she kept the envelope she was given."
        ),
    },
]


# ============================================================================
# EVIDENCE TEMPLATES  (pre-validated: no testimonial red herrings)
# ============================================================================

_EVIDENCE: List[Dict] = [
    {
        "part_type": "evidence",
        "id": None,  # caller assigns
        "name": "Monogrammed handkerchief",
        "description": "A pressed linen handkerchief embroidered with initials, found beneath the victim's chair. The monogram does not match the victim.",
        "type": "physical",
        "relevance": "supporting",
        "what_it_reveals": "Someone else was in the room; the initials may identify them.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Torn letter fragment",
        "description": "Half a page torn from a letter, recovered from the fireplace grate before it fully burned. The legible portion contains a threat and a time.",
        "type": "documentary",
        "relevance": "critical",
        "what_it_reveals": "A prior threat was made against the victim; the handwriting may be identifiable.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Scuff marks on sill",
        "description": "Fresh scuff marks on the window sill consistent with someone climbing through, and a corresponding smear of mud on the interior floor.",
        "type": "physical",
        "relevance": "supporting",
        "what_it_reveals": "Entry or exit was made through the window, contradicting alibis relying on locked doors.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Coded ledger entry",
        "description": "A ledger page with an entry in a simple substitution cipher; decoded, it records a large payment made to an unnamed party on the day of the crime.",
        "type": "documentary",
        "relevance": "critical",
        "what_it_reveals": "The victim was making or receiving payments that someone wanted kept secret.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Broken cufflink",
        "description": "One half of a distinctive silver cufflink with an unusual heraldic design, found on the floor near the point of attack.",
        "type": "physical",
        "relevance": "critical",
        "what_it_reveals": "The owner of the matching cufflink was present during the crime.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Wrong coat on the hook",
        "description": "A gentleman's coat hanging in the victim's cloakroom that does not belong to the household; a theatre programme in the pocket dates to three nights ago.",
        "type": "physical",
        "relevance": "red_herring",
        "what_it_reveals": "Initially suggests an uninvited visitor, but the coat belonged to a guest who simply forgot it at an earlier gathering.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Appointment diary",
        "description": "The victim's desk diary, open to the day of the crime; the final entry for the evening reads only 'R.V. — 9 p.m.' with the page corner folded down.",
        "type": "documentary",
        "relevance": "supporting",
        "what_it_reveals": "The victim expected a visitor whose initials or alias is 'R.V.' at nine that night.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Smudged ink on blotter",
        "description": "The desk blotter shows a reversed mirror-image of partial text, still legible: 'destroy this before' — the rest is obscured by a later smear.",
        "type": "physical",
        "relevance": "supporting",
        "what_it_reveals": "The victim was in the process of writing or destroying something sensitive shortly before death.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Foreign coin",
        "description": "An unfamiliar copper coin, minted in a country none of the household has visited, lodged between the floorboards near the window.",
        "type": "physical",
        "relevance": "red_herring",
        "what_it_reveals": "Appears to suggest a foreign connection, but was in fact dropped by a visiting repairman the previous week.",
    },
    {
        "part_type": "evidence",
        "id": None,
        "name": "Prescription bottle",
        "description": "An amber glass bottle prescribed to a suspect, found in the victim's desk drawer rather than where the suspect claims to have left it.",
        "type": "physical",
        "relevance": "critical",
        "what_it_reveals": "The suspect was in the victim's private office at some point — directly contradicting their stated alibi.",
    },
]


# ============================================================================
# SAMPLING FUNCTIONS
# ============================================================================

def sample_parts(n_suspects: int = 3, n_witnesses: int = 1) -> Dict:
    """
    Draw a balanced set of parts without repetition.

    Returns:
        {
          "crime":     {...},
          "victim":    {...},
          "suspects":  [{...}, ...],
          "witnesses": [{...}, ...],
          "evidence":  [{...}, ...],
        }

    All returned parts already satisfy check_parts() — the pre-gen gate
    will pass them straight through on a normal run.
    """
    n_suspects  = max(1, min(n_suspects, len(_SUSPECTS)))
    n_witnesses = max(0, min(n_witnesses, len(_WITNESSES)))

    crime    = random.choice(_CRIMES).copy()
    victim   = random.choice(_VICTIMS).copy()
    suspects  = random.sample(_SUSPECTS, n_suspects)
    witnesses = random.sample(_WITNESSES, n_witnesses)

    # Guarantee evidence variety: at least 2 physical, 1 documentary, 1 red herring
    physical    = [e for e in _EVIDENCE if e["type"] == "physical"]
    documentary = [e for e in _EVIDENCE if e["type"] == "documentary"]
    red_herrings = [e for e in _EVIDENCE if e["relevance"] == "red_herring"
                    and e["type"] in ("physical", "documentary")]
    other       = [e for e in _EVIDENCE
                   if e not in physical[:2] and e not in documentary[:1]
                   and e not in red_herrings[:1]]

    chosen_evidence: List[Dict] = []
    chosen_evidence += random.sample(physical, min(2, len(physical)))
    chosen_evidence += random.sample(documentary, min(1, len(documentary)))
    chosen_evidence += random.sample(red_herrings, min(1, len(red_herrings)))

    # Top up to 5 total
    remaining_pool = [e for e in _EVIDENCE if e not in chosen_evidence]
    while len(chosen_evidence) < 5 and remaining_pool:
        pick = random.choice(remaining_pool)
        chosen_evidence.append(pick)
        remaining_pool.remove(pick)

    # Assign sequential IDs
    evidence_with_ids = []
    for idx, e in enumerate(chosen_evidence, start=1):
        item = e.copy()
        item["id"] = f"ev_{idx:03d}"
        evidence_with_ids.append(item)

    return {
        "crime":     crime,
        "victim":    victim,
        "suspects":  [s.copy() for s in suspects],
        "witnesses": [w.copy() for w in witnesses],
        "evidence":  evidence_with_ids,
    }


def resample_part(part_type: str, exclude_names: Optional[List[str]] = None) -> Optional[Dict]:
    """
    Return a fresh part of the given type, excluding any names already in use.
    Returns None if the pool is exhausted.

    Used by the CLI after check_parts() fires on a specific part.
    """
    exclude_names = exclude_names or []
    pools: Dict[str, List[Dict]] = {
        "crime":    _CRIMES,
        "victim":   _VICTIMS,
        "suspect":  _SUSPECTS,
        "witness":  _WITNESSES,
        "evidence": _EVIDENCE,
    }
    pool = pools.get(part_type, [])
    candidates = [p for p in pool if p.get("name") not in exclude_names]
    if not candidates:
        return None
    part = random.choice(candidates).copy()
    return part
