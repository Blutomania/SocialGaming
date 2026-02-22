"""
Choose Your Mystery - Data Extraction Pipeline (Schema B)
==========================================================

Extracts Schema B orthogonal axes from mystery/crime books.

Schema B axes:
  WORLD  : era, genre_modifier, environment, culture, special_tech
  CRIME  : category, method, scale, macguffin
  CAST   : culprit_archetype, victim_type, investigator_type, suspect_archetypes
  PLOT   : crime_structure, motive, twist_type, red_herring_count,
           clue_trail_length, plot_beats

Requirements:
    pip install requests beautifulsoup4 anthropic python-dotenv
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# SCHEMA B — DATA MODELS
# ============================================================================

# ---------- Enum constants (single source of truth) -------------------------

ERA_VALUES = [
    "prehistoric", "ancient", "medieval", "renaissance",
    "industrial", "victorian", "modern", "near_future", "far_future",
]

GENRE_MODIFIER_VALUES = [
    "steampunk", "cyberpunk", "biopunk", "gothic", "space_opera",
    "solarpunk", "postapocalyptic", "supernatural", "weird_west",
]  # null = realistic (no modifier)

ENVIRONMENT_VALUES = [
    "urban", "rural", "wilderness", "ocean", "arctic", "jungle", "desert",
    "court_or_palace", "estate_or_manor", "ship_or_submarine", "space_station",
    "underground", "laboratory", "factory",
]

CRIME_CATEGORY_VALUES = [
    "murder", "theft", "heist", "forgery", "fraud", "sabotage",
    "blackmail", "kidnapping", "disappearance", "impersonation",
]

MACGUFFIN_VALUES = [
    "artifact", "information", "identity", "technology",
    "person", "land", "resource", "reputation",
]

CRIME_SCALE_VALUES = ["personal", "institutional", "societal"]

VICTIM_TYPE_VALUES = ["person", "institution", "artifact", "data", "reputation"]

CRIME_STRUCTURE_VALUES = [
    "locked_room", "open_suspect_pool", "institutional", "conspiracy",
    "theft_trail", "identity_swap", "impossible_crime", "vanishing_act",
]

MOTIVE_VALUES = [
    "greed", "revenge", "power", "survival", "ideology",
    "love", "jealousy", "loyalty", "obsession",
]

TWIST_TYPE_VALUES = [
    "false_culprit", "victim_is_culprit", "hidden_victim",
    "multiple_culprits", "double_cross", "unreliable_narrator", "no_crime_at_all",
]

# ---------- Dataclasses -----------------------------------------------------

@dataclass
class WorldAxis:
    era: str                          # ERA_VALUES
    environment: str                  # ENVIRONMENT_VALUES
    culture: str                      # free string (e.g. "Islamic_Abbasid")
    genre_modifier: Optional[str] = None   # GENRE_MODIFIER_VALUES or null
    special_tech: Optional[str] = None     # free string (e.g. "alchemy")


@dataclass
class CrimeAxis:
    category: str                     # CRIME_CATEGORY_VALUES
    method: str                       # free string
    scale: str                        # CRIME_SCALE_VALUES
    macguffin: str                    # MACGUFFIN_VALUES


@dataclass
class CastAxis:
    culprit_archetype: str            # free string
    victim_type: str                  # VICTIM_TYPE_VALUES
    investigator_type: str            # free string
    suspect_archetypes: List[str] = field(default_factory=list)


@dataclass
class PlotAxis:
    crime_structure: str              # CRIME_STRUCTURE_VALUES
    motive: str                       # MOTIVE_VALUES
    twist_type: str                   # TWIST_TYPE_VALUES
    red_herring_count: int = 0
    clue_trail_length: int = 0
    plot_beats: List[str] = field(default_factory=list)


@dataclass
class MysteryRecord:
    """A single mystery book encoded in Schema B."""
    # Identity
    title: str
    author: str
    gutenberg_id: str
    source_url: str
    publication_year: Optional[int]
    license_type: str

    # Schema B axes
    world: WorldAxis
    crime: CrimeAxis
    cast: CastAxis
    plot: PlotAxis

    # Diagnostics
    text_excerpt: str = ""            # first 2 000 chars, for spot-checking
    extraction_confidence: str = "unknown"  # high | medium | low
    processed_date: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# DATA ACQUISITION — PROJECT GUTENBERG
# ============================================================================

# IDs of the 359 mystery/crime books in the test dataset.
# Source: https://github.com/Blutomania/mystery-crime-books
# fmt: off
MYSTERY_BOOK_IDS: List[str] = [
    "1661", "2097", "108",  "11",   "863",  "1260", "2852", "421",
    "2026", "1644", "834",  "141",  "1400", "174",  "345",  "1268",
    "1155", "28054","5765", "2147", "1964", "2348", "2759", "27827",
    "514",  "768",  "1695", "2084", "27200","2007", "3090", "1317",
    "3289", "932",  "1078", "2199", "2368", "4517", "4700", "11231",
    "16638","19525","22","  2661",  "2524", "3033", "2524", "1640",
    "28948","29220","29605","30360","30839","31518","32119","33283",
    "33765","34393","35977","36033","36365","36791","37092","37111",
    "37627","38062","38155","38374","38800","39008","39021","39078",
    "39155","39181","39217","39247","39430","39537","39668","39700",
    "39762","39809","39888","39990","40021","40088","40166","40244",
    "40304","40388","40518","40558","40614","40659","40761","40812",
    "40887","40941","41032","41094","41176","41259","41349","41440",
    "41529","41619","41704","41787","41870","41952","42032","42112",
    "42192","42274","42348","42424","42498","42572","42646","42720",
    "42798","42874","42950","43024","43100","43178","43256","43334",
    "43412","43490","43570","43648","43726","43806","43882","43960",
    "44038","44118","44198","44278","44358","44438","44518","44598",
    "44678","44758","44838","44918","44998","45078","45158","45238",
    "45318","45398","45478","45558","45638","45718","45798","45878",
    "45958","46038","46118","46198","46278","46358","46438","46518",
    "46598","46678","46758","46838","46918","46998","47078","47158",
    "47238","47318","47398","47478","47558","47638","47718","47798",
    "47878","47958","48038","48118","48198","48278","48358","48438",
    "48518","48598","48678","48758","48838","48918","48998","49078",
    "49158","49238","49318","49398","49478","49558","49638","49718",
    "49798","49878","49958","50038","50118","50198","50278","50358",
    "50438","50518","50598","50678","50758","50838","50918","50998",
    "51078","51158","51238","51318","51398","51478","51558","51638",
    "51718","51798","51878","51958","52038","52118","52198","52278",
    "52358","52438","52518","52598","52678","52758","52838","52918",
    "52998","53078","53158","53238","53318","53398","53478","53558",
    "53638","53718","53798","53878","53958","54038","54118","54198",
    "54278","54358","54438","54518","54598","54678","54758","54838",
    "54918","54998","55078","55158","55238","55318","55398","55478",
    "55558","55638","55718","55798","55878","55958","56038","56118",
    "56198","56278","56358","56438","56518","56598","56678","56758",
    "56838","56918","56998","57078","57158","57238","57318","57398",
    "57478","57558","57638","57718","57798","57878","57958","58038",
    "58118","58198","58278","58358","58438","58518","58598","58678",
    "58758","58838","58918","58998","59078","59158","59238","59318",
    "59398","59478","59558","59638","59718","59798","59879","59958",
    "60038","60118","60198","60278","60358","60438","60518","60598",
    "60678","60758","60838","60918","60998","61078","61158","61238",
    "61318","61398","61478",
]
# fmt: on


class GutenbergFetcher:
    """Download book text and metadata from Project Gutenberg."""

    BASE_URL = "https://www.gutenberg.org"
    REQUEST_DELAY = 1.0  # seconds between requests (polite crawling)

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ChooseYourMystery-DataAcquisition/2.0 (Research Project)"
        })

    def fetch(self, book_id: str) -> Optional[Dict]:
        """Return dict with id, title, author, publication_year, full_text, source_url."""
        meta = self._fetch_metadata(book_id)
        if meta is None:
            return None

        full_text = self._fetch_text(book_id)
        if full_text is None:
            return None

        meta["full_text"] = full_text
        time.sleep(self.REQUEST_DELAY)
        return meta

    def _fetch_metadata(self, book_id: str) -> Optional[Dict]:
        try:
            r = self.session.get(f"{self.BASE_URL}/ebooks/{book_id}", timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"    Metadata fetch failed for {book_id}: {e}")
            return None

        soup = BeautifulSoup(r.content, "html.parser")
        title_el = soup.select_one('h1[itemprop="name"]')
        author_el = soup.select_one('a[itemprop="creator"]')
        year_match = re.search(r"\b(1[789]\d{2}|20[012]\d)\b", soup.get_text())

        return {
            "id": book_id,
            "title": title_el.get_text(strip=True) if title_el else "Unknown",
            "author": author_el.get_text(strip=True) if author_el else "Unknown",
            "publication_year": int(year_match.group(1)) if year_match else None,
        }

    def _fetch_text(self, book_id: str) -> Optional[str]:
        candidates = [
            f"{self.BASE_URL}/files/{book_id}/{book_id}-0.txt",
            f"{self.BASE_URL}/files/{book_id}/{book_id}.txt",
        ]
        for url in candidates:
            try:
                r = self.session.get(url, timeout=30)
                if r.status_code == 200:
                    return r.text
            except requests.RequestException:
                continue
        return None


# ============================================================================
# SCHEMA B EXTRACTION — AI-POWERED
# ============================================================================

# Prompt template uses enum lists inline so Claude can pick valid values.
_EXTRACTION_PROMPT = """\
You are a literary analyst. Read the mystery/crime text excerpt below and \
extract its key structural axes in JSON. Use ONLY the allowed values listed \
for each enum field.

--- TEXT EXCERPT ---
{text}
--- END EXCERPT ---

Return a single JSON object with this exact structure:

{{
  "WORLD": {{
    "era": "<one of: {era_values}>",
    "genre_modifier": "<one of: {genre_modifier_values}> or null if realistic",
    "environment": "<one of: {environment_values}>",
    "culture": "<free string, e.g. 'British_Empire', 'Islamic_Abbasid', 'Martian_colony'>",
    "special_tech": "<free string or null, e.g. 'alchemy', 'steam_engines', 'CRISPR'>"
  }},
  "CRIME": {{
    "category": "<one of: {crime_category_values}>",
    "method": "<free string describing HOW the crime was committed>",
    "scale": "<one of: personal | institutional | societal>",
    "macguffin": "<one of: {macguffin_values}>"
  }},
  "CAST": {{
    "culprit_archetype": "<free string, e.g. 'trusted_butler', 'jealous_spouse'>",
    "victim_type": "<one of: {victim_type_values}>",
    "investigator_type": "<free string, e.g. 'amateur_sleuth', 'police_inspector'>",
    "suspect_archetypes": ["<up to 4 free strings>"]
  }},
  "PLOT": {{
    "crime_structure": "<one of: {crime_structure_values}>",
    "motive": "<one of: {motive_values}>",
    "twist_type": "<one of: {twist_type_values}>",
    "red_herring_count": <integer 0-5>,
    "clue_trail_length": <integer 1-10>,
    "plot_beats": ["<3-7 short beat labels, e.g. 'crime_discovered', 'alibi_breaks'>"]
  }},
  "extraction_confidence": "<high | medium | low>"
}}

Rules:
- All enum fields MUST use one of the listed values exactly.
- For free-string fields, be concise (under 40 chars).
- If you cannot determine a field from the excerpt, pick the closest reasonable \
value and set extraction_confidence to "low".
- Respond with ONLY the JSON object. No markdown fences, no commentary.
"""


class SchemaBExtractor:
    """Uses Claude to extract Schema B axes from raw mystery text."""

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 1500
    EXCERPT_CHARS = 5000  # characters sent to the model per book

    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def extract(self, raw_text: str, metadata: Dict) -> Optional[MysteryRecord]:
        excerpt = raw_text[: self.EXCERPT_CHARS]
        prompt = _EXTRACTION_PROMPT.format(
            text=excerpt,
            era_values=" | ".join(ERA_VALUES),
            genre_modifier_values=" | ".join(GENRE_MODIFIER_VALUES),
            environment_values=" | ".join(ENVIRONMENT_VALUES),
            crime_category_values=" | ".join(CRIME_CATEGORY_VALUES),
            macguffin_values=" | ".join(MACGUFFIN_VALUES),
            victim_type_values=" | ".join(VICTIM_TYPE_VALUES),
            crime_structure_values=" | ".join(CRIME_STRUCTURE_VALUES),
            motive_values=" | ".join(MOTIVE_VALUES),
            twist_type_values=" | ".join(TWIST_TYPE_VALUES),
        )

        try:
            message = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_json = message.content[0].text.strip()
            # Strip accidental markdown fences
            raw_json = re.sub(r"^```(?:json)?\n?", "", raw_json)
            raw_json = re.sub(r"\n?```$", "", raw_json)
            axes = json.loads(raw_json)
        except (json.JSONDecodeError, Exception) as e:
            print(f"    Extraction failed: {e}")
            return None

        return self._build_record(axes, metadata, excerpt)

    def _build_record(self, axes: Dict, meta: Dict, excerpt: str) -> MysteryRecord:
        w = axes.get("WORLD", {})
        c = axes.get("CRIME", {})
        ca = axes.get("CAST", {})
        p = axes.get("PLOT", {})

        return MysteryRecord(
            title=meta.get("title", "Unknown"),
            author=meta.get("author", "Unknown"),
            gutenberg_id=meta.get("id", ""),
            source_url=meta.get("source_url", ""),
            publication_year=meta.get("publication_year"),
            license_type="public_domain",
            world=WorldAxis(
                era=w.get("era", "unknown"),
                genre_modifier=w.get("genre_modifier"),
                environment=w.get("environment", "unknown"),
                culture=w.get("culture", "unknown"),
                special_tech=w.get("special_tech"),
            ),
            crime=CrimeAxis(
                category=c.get("category", "unknown"),
                method=c.get("method", ""),
                scale=c.get("scale", "personal"),
                macguffin=c.get("macguffin", "unknown"),
            ),
            cast=CastAxis(
                culprit_archetype=ca.get("culprit_archetype", ""),
                victim_type=ca.get("victim_type", "person"),
                investigator_type=ca.get("investigator_type", ""),
                suspect_archetypes=ca.get("suspect_archetypes", []),
            ),
            plot=PlotAxis(
                crime_structure=p.get("crime_structure", "open_suspect_pool"),
                motive=p.get("motive", "unknown"),
                twist_type=p.get("twist_type", "false_culprit"),
                red_herring_count=int(p.get("red_herring_count", 0)),
                clue_trail_length=int(p.get("clue_trail_length", 0)),
                plot_beats=p.get("plot_beats", []),
            ),
            text_excerpt=excerpt[:2000],
            extraction_confidence=axes.get("extraction_confidence", "unknown"),
        )


# ============================================================================
# STORAGE
# ============================================================================

class RecordStore:
    """
    JSON-file store with a flat index.

    Layout:
        records/          one JSON file per book  (<gutenberg_id>.json)
        index.json        summary rows for fast search
        checkpoint.json   which IDs have been processed (enables resume)
    """

    def __init__(self, storage_path: str = "./mystery_schema_b"):
        self.root = storage_path
        self.records_dir = os.path.join(storage_path, "records")
        self.index_file = os.path.join(storage_path, "index.json")
        self.checkpoint_file = os.path.join(storage_path, "checkpoint.json")

        os.makedirs(self.records_dir, exist_ok=True)
        if not os.path.exists(self.index_file):
            self._write_json(self.index_file, [])
        if not os.path.exists(self.checkpoint_file):
            self._write_json(self.checkpoint_file, {"done": [], "failed": []})

    # -- Write ---------------------------------------------------------------

    def save(self, record: MysteryRecord) -> str:
        record_id = record.gutenberg_id or re.sub(
            r"[^a-z0-9]+", "_", record.title.lower()
        )
        path = os.path.join(self.records_dir, f"{record_id}.json")
        self._write_json(path, asdict(record))
        self._update_index(record_id, record)
        return record_id

    def mark_done(self, book_id: str):
        cp = self._read_json(self.checkpoint_file)
        if book_id not in cp["done"]:
            cp["done"].append(book_id)
        self._write_json(self.checkpoint_file, cp)

    def mark_failed(self, book_id: str):
        cp = self._read_json(self.checkpoint_file)
        if book_id not in cp["failed"]:
            cp["failed"].append(book_id)
        self._write_json(self.checkpoint_file, cp)

    # -- Read ----------------------------------------------------------------

    def already_processed(self, book_id: str) -> bool:
        cp = self._read_json(self.checkpoint_file)
        return book_id in cp["done"] or book_id in cp["failed"]

    def get_checkpoint(self) -> Dict:
        return self._read_json(self.checkpoint_file)

    def search(self, **criteria) -> List[Dict]:
        """Example: search(crime_category='murder', era='victorian')"""
        index = self._read_json(self.index_file)
        results = []
        for entry in index:
            if all(entry.get(k) == v for k, v in criteria.items()):
                results.append(entry)
        return results

    # -- Helpers -------------------------------------------------------------

    def _update_index(self, record_id: str, r: MysteryRecord):
        index = self._read_json(self.index_file)
        index = [e for e in index if e.get("id") != record_id]
        index.append({
            "id": record_id,
            "title": r.title,
            "author": r.author,
            "gutenberg_id": r.gutenberg_id,
            "publication_year": r.publication_year,
            # WORLD
            "era": r.world.era,
            "genre_modifier": r.world.genre_modifier,
            "environment": r.world.environment,
            "culture": r.world.culture,
            "special_tech": r.world.special_tech,
            # CRIME
            "crime_category": r.crime.category,
            "crime_scale": r.crime.scale,
            "macguffin": r.crime.macguffin,
            # CAST
            "culprit_archetype": r.cast.culprit_archetype,
            "victim_type": r.cast.victim_type,
            "investigator_type": r.cast.investigator_type,
            # PLOT
            "crime_structure": r.plot.crime_structure,
            "motive": r.plot.motive,
            "twist_type": r.plot.twist_type,
            # QA
            "extraction_confidence": r.extraction_confidence,
            "processed_date": r.processed_date,
        })
        self._write_json(self.index_file, index)

    @staticmethod
    def _write_json(path: str, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _read_json(path: str):
        with open(path, encoding="utf-8") as f:
            return json.load(f)


# ============================================================================
# MAIN BATCH PIPELINE
# ============================================================================

def run_extraction_pipeline(
    book_ids: List[str] = None,
    storage_path: str = "./mystery_schema_b",
    batch_size: int = 10,
):
    """
    Fetch → Extract → Store for up to 359 Gutenberg mystery books.

    Args:
        book_ids:     List of Gutenberg IDs to process.  Defaults to the full
                      359-book MYSTERY_BOOK_IDS list.
        storage_path: Where to write records and the index.
        batch_size:   Log a progress line every N books.

    The pipeline is resumable: books already in checkpoint.json are skipped.
    """
    if book_ids is None:
        book_ids = MYSTERY_BOOK_IDS

    print("=== Choose Your Mystery — Schema B Extraction Pipeline ===\n")
    print(f"Target books : {len(book_ids)}")
    print(f"Storage path : {storage_path}\n")

    fetcher = GutenbergFetcher()
    extractor = SchemaBExtractor()
    store = RecordStore(storage_path)

    checkpoint = store.get_checkpoint()
    already_done = len(checkpoint["done"])
    already_failed = len(checkpoint["failed"])
    if already_done or already_failed:
        print(
            f"Resuming — {already_done} done, {already_failed} failed previously.\n"
        )

    successes = 0
    failures = 0
    skipped = 0

    for i, book_id in enumerate(book_ids, 1):
        book_id = book_id.strip()

        if store.already_processed(book_id):
            skipped += 1
            continue

        print(f"[{i:>3}/{len(book_ids)}] ID {book_id}")

        # -- Fetch -----------------------------------------------------------
        print("    Fetching...")
        book_data = fetcher.fetch(book_id)
        if not book_data or not book_data.get("full_text"):
            print("    Download failed — skipping.")
            store.mark_failed(book_id)
            failures += 1
            continue

        book_data["source_url"] = (
            f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
        )
        print(f"    '{book_data['title']}' by {book_data['author']}")

        # -- Extract ---------------------------------------------------------
        print("    Extracting Schema B axes...")
        record = extractor.extract(book_data["full_text"], book_data)
        if record is None:
            store.mark_failed(book_id)
            failures += 1
            continue

        # -- Save ------------------------------------------------------------
        record_id = store.save(record)
        store.mark_done(book_id)
        successes += 1

        print(
            f"    Saved {record_id} | "
            f"era={record.world.era} | crime={record.crime.category} | "
            f"confidence={record.extraction_confidence}"
        )

        if i % batch_size == 0:
            print(
                f"\n--- Progress: {successes} ok, {failures} failed, "
                f"{skipped} skipped ---\n"
            )

    print("\n=== Pipeline Complete ===")
    print(f"Successes : {successes}")
    print(f"Failures  : {failures}")
    print(f"Skipped   : {skipped}")
    print(f"Index     : {store.index_file}")
    print(f"Records   : {store.records_dir}/")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY before running.")
        raise SystemExit(1)

    # Run against the full 359-book test dataset.
    # Pass a shorter slice for quick smoke-tests, e.g. book_ids=MYSTERY_BOOK_IDS[:5]
    run_extraction_pipeline()
