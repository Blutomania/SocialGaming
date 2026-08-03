"""
craft_grounding.py — Retrieval layer over the craft-grounding companion docs.
==============================================================================

WHAT THIS IS FOR (read this before touching anything below)
-------------------------------------------------------------------------
`RESEARCH_FINDINGS.md`, `SCREEN_CRAFT_FINDINGS.md`, and `PARTY_CRAFT_FINDINGS.md`
(and, in the future, whatever additional `*_CRAFT_FINDINGS.md` docs get added per
`SOURCING_METHODOLOGY.md`) ground this project's mystery-writing taxonomy in real
craft sources — novelists, screenwriters, and party-game designers explaining, in
their own words, *how* to plant a fair clue, construct a red herring, or keep a
witness's dialogue consistent. Before this module existed, those documents were
just markdown that nothing in the running system ever read — real research,
sitting inert.

This module is the retrieval half of that: it turns those docs into a small,
queryable index and hands back a short, relevant slice of craft guidance for
whichever generation call is asking (see `CALL_SITE_TAGS` below for exactly
which tags each of the four call-sites in `server/main.py` requests).

DESIGN PRINCIPLES — these were explicit decisions, not defaults, so don't
"simplify" them away without re-reading why:

1. **The markdown is the only source of truth. The index is a disposable
   cache.** `build_index()` re-parses every `*_CRAFT_FINDINGS.md` /
   `RESEARCH_FINDINGS.md` file at the repo root and rebuilds
   `mystery_database/craft_grounding_index.json` automatically whenever a
   source doc's mtime is newer than the cached index. Nobody should ever
   hand-edit the JSON file directly — it will just be overwritten the next
   time a doc changes. This is what makes the system "not bounded, not set
   in stone": paste new full-text findings into an existing doc, or drop in
   a brand-new doc following the same table convention, and the very next
   generation call picks it up. No code change required for new *content* —
   only for a genuinely new *table shape* (see `_classify_columns` below).

2. **Retrieval is a local, zero-cost lookup — never an LLM call.** Adding
   craft grounding to a generation call must never turn one API call into
   two. All the "intelligence" here is a plain dict filter over pre-parsed
   entries; the only cost this adds to an existing call is a few hundred
   extra input tokens of injected guidance text.

3. **Confidence tiers gate what reaches a live prompt.** The companion docs
   already tag entries by sourcing confidence (see `_infer_confidence`) —
   `get_craft_guidance()` defaults to excluding the lowest tier
   (`secondary` — third-party analysis / unconfirmed attribution) so a
   shaky finding never silently governs what an NPC actually says. This is
   configurable per call, not hardcoded, in case a future call-site wants a
   looser or stricter bar.

4. **Every retrieval is auditable.** `guidance_provenance()` returns a
   structured citation list, not just prose, meant to travel alongside
   whatever it informed (see how `server/main.py` attaches it to
   `mystery_dict["_provenance"]["craft_guidance"]` and to
   `round_["_craft_guidance"]`). If a generated mystery or a witness's
   answer reads oddly, you should be able to trace it back to exactly which
   craft citation(s) were injected into that specific call. This matters
   most during early playtesting, when you're trying to figure out *why*
   something felt off.

RESOLVED CAVEAT (Session 23) — `part_registry.py`'s axis 8 was previously
named `"evidence_type"` despite holding alibi content (the extraction key
`"alibi"` mapped there). Renamed the axis itself to `"alibi"` in
`part_registry.py`, so `PART_TYPE_TO_TAXONOMY` below maps `"alibi"` -> M5
directly — no more name/content mismatch. See `SESSIONS.md` Session 23 for
the full before/after.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

# ============================================================================
# Data model
# ============================================================================

@dataclass
class GuidanceEntry:
    """One row of craft guidance, parsed from a companion doc's table.

    `taxonomy_tags` are P1-P4 codes (e.g. "M3", "F8") pulled out of a
    "Maps to taxonomy" column. `game_system_tags` are the fixed category
    names `PARTY_CRAFT_FINDINGS.md` uses instead (e.g. "Interrogation
    Phase") for mechanics that don't correspond to a taxonomy code at all.
    An entry can have either, both, or (rarely) neither.
    """
    doc: str                 # source filename, e.g. "SCREEN_CRAFT_FINDINGS.md"
    section: str             # nearest preceding heading, e.g. "Alfred Hitchcock"
    concept: str
    insight: str
    taxonomy_tags: list[str] = field(default_factory=list)
    game_system_tags: list[str] = field(default_factory=list)
    confidence: str = "primary"   # "canonical" | "verified" | "primary" | "secondary"
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# Parsing
# ============================================================================

_REPO_ROOT = Path(__file__).resolve().parent
_INDEX_PATH = _REPO_ROOT / "mystery_database" / "craft_grounding_index.json"
_SOURCE_DOC_GLOBS = ["RESEARCH_FINDINGS.md", "*_CRAFT_FINDINGS.md"]

# Fixed category names from PARTY_CRAFT_FINDINGS.md's "Mapping convention"
# section — mechanics-level tags for findings that map to a game system
# rather than a P1-P4 taxonomy code. Update this list if a companion doc
# introduces a new category name.
GAME_SYSTEM_CATEGORIES = [
    "75% Sharing Mechanic",
    "Interrogation Phase",
    "Investigation/Scene Phase",
    "Accusation/Reveal Phase",
    "Replayability/Generation",
    "Host/GM Function",
    "Social Dynamics",
    "Win Condition Design",
]

_TAXONOMY_CODE_RE = re.compile(r"\b([CMF]\d{1,2})\b")
_HEADING_RE = re.compile(r"^(#{2,3})\s+(.+)$")
_BOLD_TITLE_RE = re.compile(r"\*\*(.+?)\*\*")
# Confidence-tag markup that can appear inline in a Concept cell, e.g.
# "Minimize actual lies... **[full text verified]**" — stripped from the
# displayed concept text since the tier is already captured structurally
# in GuidanceEntry.confidence; leaving it in would read as noise in an
# injected prompt.
_CONFIDENCE_TAG_RE = re.compile(
    r"\*\*\s*\[[^\]]*\]\s*\*\*|\[full text verified\]|\[third-party analysis\]",
    re.IGNORECASE,
)


def _clean_concept(concept: str) -> str:
    return _CONFIDENCE_TAG_RE.sub("", concept).strip(" *")

_CONFIDENCE_RANK = {"canonical": 3, "verified": 3, "primary": 2, "secondary": 1}


def _split_row(line: str) -> list[str]:
    """Split one markdown table row into cell strings."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.match(r"^:?-{2,}:?$", c) for c in cells if c)


def _classify_columns(header: list[str]) -> Optional[dict]:
    """Figure out which column holds which field, from the header row text.

    Returns None for an unrecognized table shape (e.g. a plain reference
    table that isn't a findings table) — such tables are silently skipped,
    not treated as an error. If a future companion doc introduces a
    genuinely new header shape, add a case here.
    """
    lower = [h.lower() for h in header]

    # RESEARCH_FINDINGS.md's taxonomy-definition table: "# | Part | Who Names It"
    if lower == ["#", "part", "who names it"]:
        return {"kind": "taxonomy_def", "code": 0, "part": 1, "citation": 2}

    # SCREEN_CRAFT_FINDINGS.md / PARTY_CRAFT_FINDINGS.md's per-creator findings
    # tables: "Concept | Insight | Maps to taxonomy|game system | Source"
    if len(lower) == 4 and lower[0] == "concept" and lower[1] == "insight":
        maps_idx = next((i for i, h in enumerate(lower) if h.startswith("maps to")), None)
        source_idx = next((i for i, h in enumerate(lower) if h == "source"), None)
        if maps_idx is not None and source_idx is not None:
            return {"kind": "finding", "concept": 0, "insight": 1,
                    "maps_to": maps_idx, "source": source_idx}

    return None


def _infer_confidence(concept: str, insight: str, source: str) -> str:
    """Read the confidence tier straight from the sourcing tags the docs
    already use — see SOURCING_METHODOLOGY.md for the tier definitions.
    Tags like "[full text verified]" can appear in any of the three
    columns (Concept, Insight, or Source), so all three are checked."""
    combined = f"{concept} {insight} {source}".lower()
    if "full text verified" in combined:
        return "verified"
    if any(marker in combined for marker in (
        "third-party analysis", "secondary attribution", "per search snippet",
        "not independently confirmed", "search-attributed", "via search snippet",
    )):
        return "secondary"
    return "primary"


def _row_to_entry(cells: list[str], col_map: dict, doc_name: str, section: str) -> Optional[GuidanceEntry]:
    if col_map["kind"] == "taxonomy_def":
        code = cells[col_map["code"]].strip()
        part_text = cells[col_map["part"]]
        title_match = _BOLD_TITLE_RE.search(part_text)
        concept = title_match.group(1).strip() if title_match else part_text[:60]
        # part_text repeats the bold title inline (e.g. "**The Red Herring**
        # — deliberate misdirection..."); strip it so display doesn't
        # duplicate "concept: **concept** — description".
        insight = _BOLD_TITLE_RE.sub("", part_text, count=1).strip(" —-")
        if not code or not part_text:
            return None
        return GuidanceEntry(
            doc=doc_name, section=section,
            concept=concept, insight=insight or part_text,
            taxonomy_tags=[code],
            confidence="canonical",
            source=cells[col_map["citation"]],
        )

    concept = cells[col_map["concept"]]
    insight = cells[col_map["insight"]]
    maps_to = cells[col_map["maps_to"]]
    source = cells[col_map["source"]]
    if not concept or not insight:
        return None
    taxonomy_tags = sorted(set(_TAXONOMY_CODE_RE.findall(maps_to)))
    game_system_tags = [g for g in GAME_SYSTEM_CATEGORIES if g in maps_to]
    return GuidanceEntry(
        doc=doc_name, section=section,
        concept=_clean_concept(concept), insight=insight,
        taxonomy_tags=taxonomy_tags,
        game_system_tags=game_system_tags,
        confidence=_infer_confidence(concept, insight, source),
        source=source,
    )


_RECEPTION_SECTION_RE = re.compile(r"player experience|reception", re.IGNORECASE)


def _parse_doc(path: Path) -> list[GuidanceEntry]:
    """Parse one companion doc into entries.

    Tracks the nearest H2 (##) heading separately from the nearest heading
    of any level, because some docs (PARTY_CRAFT_FINDINGS.md today) split
    "design authority" findings (creators/designers explaining their own
    reasoning) from "reception evidence" findings (testimonials, reviews —
    explicitly *not* prescriptive, per that doc's own stated convention).
    A companion doc that wants this split honored should name its reception
    section's H2 heading with "Player Experience" or "Reception" in it —
    rows under such a heading are capped at "secondary" confidence
    regardless of their own inline tag, so they're excluded from a live
    prompt by default (min_confidence="primary") while still present in
    the index/audit trail for anyone who explicitly lowers the bar.
    """
    entries: list[GuidanceEntry] = []
    current_section = path.stem
    current_h2 = ""
    lines = path.read_text(encoding="utf-8").splitlines()

    i = 0
    while i < len(lines):
        heading_match = _HEADING_RE.match(lines[i])
        if heading_match:
            level, text = heading_match.group(1), heading_match.group(2).strip()
            current_section = text
            if level == "##":
                current_h2 = text
            i += 1
            continue

        if lines[i].strip().startswith("|"):
            header_cells = _split_row(lines[i])
            has_separator = i + 1 < len(lines) and _is_separator_row(_split_row(lines[i + 1]))
            col_map = _classify_columns(header_cells) if has_separator else None
            if col_map is not None:
                is_reception_section = bool(_RECEPTION_SECTION_RE.search(current_h2))
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    row_cells = _split_row(lines[j])
                    if len(row_cells) == len(header_cells):
                        entry = _row_to_entry(row_cells, col_map, path.name, current_section)
                        if entry:
                            if is_reception_section:
                                entry.confidence = "secondary"
                            entries.append(entry)
                    j += 1
                i = j
                continue

        i += 1

    return entries


def _source_docs(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in _SOURCE_DOC_GLOBS:
        paths.extend(sorted(root.glob(pattern)))
    # de-duplicate in case a filename matches more than one glob
    seen = set()
    unique = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


# ============================================================================
# Index build / cache
# ============================================================================

def build_index(force: bool = False) -> list[GuidanceEntry]:
    """Parse every craft-grounding doc into a flat list of entries, using a
    cached JSON index when none of the source docs have changed.

    Pass force=True to bypass the cache (e.g. after editing a doc in the
    same process where you're about to call get_craft_guidance()).
    """
    docs = _source_docs(_REPO_ROOT)
    newest_mtime = max((p.stat().st_mtime for p in docs), default=0.0)

    if not force and _INDEX_PATH.exists() and _INDEX_PATH.stat().st_mtime >= newest_mtime:
        try:
            cached = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
            return [GuidanceEntry(**e) for e in cached]
        except Exception:
            pass  # fall through and rebuild if the cache is somehow unreadable

    entries: list[GuidanceEntry] = []
    for doc in docs:
        entries.extend(_parse_doc(doc))

    _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    _INDEX_PATH.write_text(
        json.dumps([e.to_dict() for e in entries], indent=2),
        encoding="utf-8",
    )
    return entries


# ============================================================================
# Retrieval
# ============================================================================

def get_craft_guidance(
    taxonomy_tags: Optional[list[str]] = None,
    game_system_tags: Optional[list[str]] = None,
    min_confidence: str = "primary",
    max_items: int = 5,
) -> list[GuidanceEntry]:
    """Return up to max_items guidance entries matching any of the given
    tags, at or above min_confidence.

    Matching is OR across tags (an entry matching any requested taxonomy
    code or game-system category qualifies), then entries are ranked
    highest-confidence-first. This is a pure local filter — no API call.
    """
    if not taxonomy_tags and not game_system_tags:
        return []

    min_rank = _CONFIDENCE_RANK.get(min_confidence, 2)
    wanted_taxonomy = set(taxonomy_tags or [])
    wanted_game_system = set(game_system_tags or [])

    entries = build_index()
    matches = [
        e for e in entries
        if _CONFIDENCE_RANK.get(e.confidence, 0) >= min_rank
        and (
            bool(wanted_taxonomy & set(e.taxonomy_tags))
            or bool(wanted_game_system & set(e.game_system_tags))
        )
    ]
    # Highest confidence first; otherwise a stable, deterministic order so
    # the same call with the same index produces the same injected guidance.
    matches.sort(key=lambda e: (-_CONFIDENCE_RANK.get(e.confidence, 0), e.doc, e.section, e.concept))
    return matches[:max_items]


def format_guidance_block(entries: list[GuidanceEntry]) -> str:
    """Render guidance entries as a prompt-ready text block. Returns ""
    (not a header with no rows) when there's nothing to inject, so callers
    can safely concatenate this straight into a prompt."""
    if not entries:
        return ""
    lines = ["CRAFT GUIDANCE (grounded in mystery-writing/screen/party-design craft sources — use as technique, do not quote):"]
    for e in entries:
        lines.append(f"  - {e.concept}: {e.insight}")
    return "\n".join(lines)


def guidance_provenance(entries: list[GuidanceEntry]) -> list[dict]:
    """Structured citation list for a specific generation call, meant to be
    attached to whatever that call produced (see server/main.py's
    `mystery_dict["_provenance"]["craft_guidance"]` and
    `round_["_craft_guidance"]`)."""
    return [
        {
            "concept": e.concept,
            "doc": e.doc,
            "section": e.section,
            "confidence": e.confidence,
            "source": e.source,
        }
        for e in entries
    ]


# ============================================================================
# Call-site tag mapping
# ============================================================================

# Maps part_registry.py's PART_TYPE_NAMES (the 8-axis sampling system, older
# and coarser than the P1-P4 taxonomy) onto the taxonomy codes that actually
# describe that axis's content. Used by _generate_mystery_dict() in
# server/main.py to retrieve guidance matching whatever axes a given
# generated mystery actually drew from.
#
PART_TYPE_TO_TAXONOMY: dict[str, list[str]] = {
    "crime_type": ["C1"],
    "setting_element": ["C3"],
    "motive": ["C4"],
    "suspect_archetype": ["M1"],
    "red_herring": ["M2"],
    "reveal_mechanic": ["M6"],
    "social_dynamic": ["M4"],
    "alibi": ["M5"],
}

# Fixed tag sets for the three call-sites that don't sample from the part
# registry (witness dialogue, scene investigation, lead follow-up). These
# are curated by hand, not derived — each maps to the craft axes that
# actually govern what that call is generating. Documented at length in
# docs/WIRING.md under "Craft-grounding retrieval (RAG layer)".
CALL_SITE_TAGS: dict[str, dict[str, list[str]]] = {
    "witness_scene": {
        "taxonomy_tags": ["M2", "M3", "F3"],
        "game_system_tags": ["Interrogation Phase", "Social Dynamics"],
    },
    "investigate_area": {
        "taxonomy_tags": ["F4", "F5"],
        "game_system_tags": ["Investigation/Scene Phase"],
    },
    "follow_lead": {
        "taxonomy_tags": ["M2", "M5", "C4"],
        "game_system_tags": ["Investigation/Scene Phase"],
    },
}
