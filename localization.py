"""
localization.py — setting-aware character name / occupation localization

Called after mystery generation to replace anachronistic names, titles, and
occupations with era/culture-appropriate equivalents.

Design:
  - Compact mapping approach: Claude returns [{old, new, old_occ, new_occ}] only.
    Python does the string substitution. Cuts token cost ~28x vs. full-JSON rewrite.
  - Era ruleset cache: first call for a setting derives naming conventions and
    caches them to disk. Subsequent calls for the same era reuse the cache,
    making the prompt shorter and the output more consistent.
  - Modern-era skip: contemporary / near-future settings use modern names already.
    No API call is made.
"""

from __future__ import annotations
import json
import os
import re
from typing import Callable

_CACHE_DIR = os.path.join("mystery_database", "localization_cache")

# Time-period substrings that indicate a modern/near-future setting where
# English names are already appropriate — skip the localization call entirely.
_MODERN_MARKERS = [
    "present day", "present-day", "contemporary",
    "2020", "2021", "2022", "2023", "2024", "2025", "2026",
    "2030", "2040", "2050", "near future", "near-future",
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def localize_mystery(mystery_dict: dict, llm_fn: Callable[[str], str]) -> dict:
    """
    Localize character names, occupations, and titles to fit the mystery's
    time period and culture.

    Args:
        mystery_dict: full mystery dict (will not be mutated)
        llm_fn:       callable(prompt: str) -> str  — the app's or CLI's LLM wrapper

    Returns:
        A new mystery dict with localized surface text.
        Internal fields (_provenance, _coherence, _meta, cinematic_brief) are
        re-attached unchanged after substitution.
    """
    setting = mystery_dict.get("setting", {})

    # Optimization 3: skip entirely for contemporary / near-future settings
    if _is_modern(setting):
        return mystery_dict

    era_key = _era_key(setting)
    cached_rules = _load_era_rules(era_key)

    # Build the compact prompt
    prompt = _build_prompt(setting, mystery_dict, cached_rules)

    raw = llm_fn(prompt)
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    result = json.loads(raw)

    # Optimization 2: cache era rules on first encounter
    if cached_rules is None and "era_rules" in result:
        _save_era_rules(era_key, result["era_rules"])

    name_map = result.get("name_map", [])
    if not name_map:
        return mystery_dict

    # Optimization 1: Python does the substitution, not Claude
    localized = _apply_name_map(mystery_dict, name_map)

    # Re-attach internal fields that localization must not touch
    for key in ("_provenance", "_coherence", "_meta", "cinematic_brief"):
        if key in mystery_dict:
            localized[key] = mystery_dict[key]

    return localized


def cache_stats() -> dict:
    """Return info about the current era ruleset cache."""
    if not os.path.isdir(_CACHE_DIR):
        return {"cached_eras": 0, "eras": []}
    files = [f for f in os.listdir(_CACHE_DIR) if f.endswith(".json")]
    return {"cached_eras": len(files), "eras": [f[:-5] for f in sorted(files)]}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_modern(setting: dict) -> bool:
    """Return True if the setting is contemporary / near-future."""
    tp = setting.get("time_period", "").lower()
    loc = setting.get("location", "").lower()
    combined = f"{tp} {loc}"
    return any(m in combined for m in _MODERN_MARKERS)


def _era_key(setting: dict) -> str:
    """Derive a filesystem-safe cache key from location + time_period."""
    raw = f"{setting.get('location', '')} {setting.get('time_period', '')}".lower()
    clean = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return clean[:64]


def _load_era_rules(key: str) -> dict | None:
    path = os.path.join(_CACHE_DIR, f"{key}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _save_era_rules(key: str, rules: dict) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    path = os.path.join(_CACHE_DIR, f"{key}.json")
    with open(path, "w") as f:
        json.dump(rules, f, indent=2)


def _apply_name_map(mystery_dict: dict, name_map: list[dict]) -> dict:
    """
    Apply [{old, new, old_occ, new_occ}] to all string fields in mystery_dict
    via JSON-string replacement with word boundaries.
    Processes longest names first to avoid substring collisions.
    """
    text = json.dumps(mystery_dict, ensure_ascii=False)
    # Sort longest-old-name first to prevent "Marcus" replacing inside "Marcus Flavius"
    for entry in sorted(name_map, key=lambda x: -len(x.get("old", ""))):
        old = entry.get("old", "").strip()
        new = entry.get("new", "").strip()
        if old and new and old != new:
            text = re.sub(r"\b" + re.escape(old) + r"\b", new, text)
        old_occ = entry.get("old_occ", "").strip()
        new_occ = entry.get("new_occ", "").strip()
        if old_occ and new_occ and old_occ != new_occ:
            text = re.sub(r"\b" + re.escape(old_occ) + r"\b", new_occ, text)
    return json.loads(text)


def _build_prompt(setting: dict, mystery_dict: dict, cached_rules: dict | None) -> str:
    location = setting.get("location", "")
    time_period = setting.get("time_period", "")

    chars = mystery_dict.get("characters", [])
    char_list = "\n".join(
        f"  - {c['name']} | {c.get('occupation', '')} | {c.get('role', '')}"
        for c in chars
    )

    if cached_rules:
        rules_block = f"""CACHED ERA RULES (apply these):
{json.dumps(cached_rules, indent=2)}

Using the rules above, produce only the name_map below. Do NOT include era_rules in output."""
        era_rules_instruction = ""
    else:
        rules_block = f"""No cached rules exist for this era. Derive appropriate conventions."""
        era_rules_instruction = """Also return "era_rules" with the conventions you derive, so they can be cached:
  era_rules: {{
    "name_examples": {{"male": [...], "female": [...]}},
    "occupation_map": {{"modern_term": "era_term", ...}},
    "forbidden_titles": ["Mr.", "Ms.", ...],
    "allowed_titles": ["Senator", "Tribune", ...],
    "pun_style": "brief description of playful naming style",
    "notes": "any other era-specific guidance"
  }}"""

    return f"""\
Localize mystery characters for: {location} — {time_period}

{rules_block}

CHARACTERS TO LOCALIZE:
{char_list}

Rules:
1. Names must fit the culture and era (no modern surnames in ancient settings).
2. Occupations → period-appropriate equivalents.
3. No anachronistic honorifics (no Mr./Ms./Dr. in ancient/medieval settings).
4. One or two playful period puns for witnesses or minor bit-parts only.
   Example: Roman witness "I Saw It All" → "Vidiomnius". Keep to 1–2 max.
5. Update the culprit's name/occupation too — just not their role or guilt.

{era_rules_instruction}

Return ONLY this JSON (no commentary):
{{
  {'"era_rules": {{ ... }},' if not cached_rules else ''}
  "name_map": [
    {{"old": "Dr. Pemberton", "new": "Alexios the Physician", "old_occ": "Doctor", "new_occ": "Physician"}},
    ...
  ]
}}"""
