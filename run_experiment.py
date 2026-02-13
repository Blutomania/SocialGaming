"""
Choose Your Mystery - Extraction Experiment Runner
====================================================

Downloads source texts ONCE, then runs all four extraction variants against
the same corpus. Outputs go to separate directories for side-by-side comparison.

Supports two corpus sources:
  - Gutenberg: Scrapes Project Gutenberg by search query (default)
  - Hugging Face: Uses AlekseyKorshuk/mystery-crime-books dataset (359 books)

Usage:
    # Download corpus and run all variants (Gutenberg)
    python run_experiment.py

    # Use the Hugging Face mystery corpus instead (359 pre-curated books)
    python run_experiment.py --source huggingface --limit 10

    # Download corpus only (skip processing)
    python run_experiment.py --download-only

    # Process only (corpus already downloaded)
    python run_experiment.py --process-only

    # Run specific variants
    python run_experiment.py --variants lean,rich

    # Use a different Gutenberg search query or limit
    python run_experiment.py --source gutenberg --query "agatha christie" --limit 5

Requirements:
    pip install requests beautifulsoup4 anthropic python-dotenv
    pip install datasets  # only needed for --source huggingface
"""

import os
import re
import json
import sys
import time
import argparse
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# SHARED CORPUS MANAGEMENT
# ============================================================================

CORPUS_DIR = "./mystery_corpus"
CORPUS_INDEX = f"{CORPUS_DIR}/corpus_index.json"

VARIANT_MODULES = {
    "baseline": {
        "module": "mystery_data_acquisition",
        "processor_class": "MysteryProcessor",
        "database_class": "MysteryDatabase",
        "db_path": "./mystery_database",
        "description": "Baseline (6 LLM calls, moderate detail)",
    },
    "lean": {
        "module": "mystery_extraction_lean",
        "processor_class": "LeanProcessor",
        "database_class": "MysteryDatabase",
        "db_path": "./mystery_database_lean",
        "description": "Lean (1 LLM call, sparse seed)",
    },
    "rich": {
        "module": "mystery_extraction_rich",
        "processor_class": "RichProcessor",
        "database_class": "MysteryDatabase",
        "db_path": "./mystery_database_rich",
        "description": "Rich (8 LLM calls, maximum depth)",
    },
    "template": {
        "module": "mystery_extraction_templates",
        "processor_class": "TemplateProcessor",
        "database_class": "TemplateDatabase",
        "db_path": "./mystery_database_templates",
        "description": "Templates (6 LLM calls, reusable patterns)",
    },
}


class CorpusManager:
    """Download and cache source texts for reproducible experiments."""

    BASE_URL = "https://www.gutenberg.org"
    SEARCH_URL = f"{BASE_URL}/ebooks/search/"
    REQUEST_DELAY = 2

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ChooseYourMystery-DataAcquisition/1.0 (Research Project)'
        })
        os.makedirs(CORPUS_DIR, exist_ok=True)

    def download_corpus(self, query: str = "sherlock holmes", limit: int = 3) -> List[Dict]:
        """
        Download texts and cache them locally. Returns the corpus index.
        If corpus already exists, loads from cache instead.
        """
        if os.path.exists(CORPUS_INDEX):
            print(f"Corpus already exists at {CORPUS_DIR}/")
            print("Loading cached corpus (use --force-download to re-download)\n")
            return self._load_index()

        print(f"Downloading corpus: query='{query}', limit={limit}")
        print(f"Saving to {CORPUS_DIR}/\n")

        # Search
        params = {'query': query, 'submit_search': 'Go!'}
        response = self.session.get(self.SEARCH_URL, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        books = []
        for item in soup.select('.booklink')[:limit]:
            book_id = item.get('href', '').split('/')[-1]
            title = item.get_text(strip=True)
            if book_id.isdigit():
                books.append({'id': book_id, 'title': title})

        print(f"Found {len(books)} books on Gutenberg\n")

        # Download each
        corpus = []
        for i, book in enumerate(books, 1):
            print(f"  [{i}/{len(books)}] Downloading: {book['title']}")
            entry = self._download_and_cache(book['id'])
            if entry:
                corpus.append(entry)
                print(f"    Cached: {entry['text_file']} "
                      f"({len(entry['full_text'])} chars)")
            else:
                print(f"    Failed to download")

        # Save corpus index
        # Strip full_text from index (it's in the cached files)
        index_entries = []
        for entry in corpus:
            index_entry = {k: v for k, v in entry.items() if k != 'full_text'}
            index_entries.append(index_entry)

        with open(CORPUS_INDEX, 'w') as f:
            json.dump({
                'query': query,
                'download_date': datetime.now().isoformat(),
                'book_count': len(corpus),
                'books': index_entries,
            }, f, indent=2)

        print(f"\nCorpus downloaded: {len(corpus)} books cached")
        return corpus

    def _download_and_cache(self, book_id: str) -> Optional[Dict]:
        time.sleep(self.REQUEST_DELAY)

        # Metadata
        response = self.session.get(f"{self.BASE_URL}/ebooks/{book_id}")
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        title_elem = soup.select_one('h1[itemprop="name"]')
        author_elem = soup.select_one('a[itemprop="creator"]')
        year_match = re.search(r'\b(1[789]\d{2}|20\d{2})\b', soup.get_text())

        metadata = {
            'id': book_id,
            'title': title_elem.get_text(strip=True) if title_elem else "Unknown",
            'author': author_elem.get_text(strip=True) if author_elem else "Unknown",
            'publication_year': int(year_match.group(1)) if year_match else None,
        }

        # Download text
        time.sleep(self.REQUEST_DELAY)
        for url in [f"{self.BASE_URL}/files/{book_id}/{book_id}-0.txt",
                     f"{self.BASE_URL}/files/{book_id}/{book_id}.txt"]:
            try:
                r = self.session.get(url)
                r.raise_for_status()
                text = r.text
                metadata['source_url'] = url

                # Cache text to file
                text_file = f"book_{book_id}.txt"
                with open(f"{CORPUS_DIR}/{text_file}", 'w', encoding='utf-8') as f:
                    f.write(text)
                metadata['text_file'] = text_file
                metadata['full_text'] = text
                return metadata
            except requests.RequestException:
                continue

        return None

    def _load_index(self) -> List[Dict]:
        """Load corpus from cache, including full text."""
        with open(CORPUS_INDEX, 'r') as f:
            index = json.load(f)

        corpus = []
        for entry in index['books']:
            text_path = f"{CORPUS_DIR}/{entry['text_file']}"
            if os.path.exists(text_path):
                with open(text_path, 'r', encoding='utf-8') as f:
                    entry['full_text'] = f.read()
                corpus.append(entry)
            else:
                print(f"  Warning: cached text missing for {entry['title']}")

        return corpus

    def download_huggingface_corpus(self, limit: int = 20) -> List[Dict]:
        """
        Download mystery texts from the AlekseyKorshuk/mystery-crime-books
        Hugging Face dataset (359 full-text mystery/crime books).

        This is a better source than Gutenberg scraping -- it's pre-curated
        for the mystery/crime genre, so every entry is relevant.

        Requirements: pip install datasets
        """
        if os.path.exists(CORPUS_INDEX):
            index = self._load_index()
            if index and index[0].get('_source') == 'huggingface':
                print(f"HuggingFace corpus already cached at {CORPUS_DIR}/")
                print("Loading cached corpus (use --force-download to re-download)\n")
                return index
            # Different source -- warn and re-download
            print("Existing corpus is from a different source. Re-downloading.\n")

        try:
            from datasets import load_dataset
        except ImportError:
            print("ERROR: 'datasets' library not installed.")
            print("Run: pip install datasets")
            sys.exit(1)

        print(f"Downloading AlekseyKorshuk/mystery-crime-books from Hugging Face...")
        print(f"Limiting to first {limit} of 359 books\n")

        ds = load_dataset("AlekseyKorshuk/mystery-crime-books", split="train")
        print(f"Dataset loaded: {len(ds)} total books")

        corpus = []
        for i, entry in enumerate(ds):
            if i >= limit:
                break

            text = entry.get("text", "")
            if not text or len(text) < 1000:
                continue

            # Extract a title from the first few lines if possible
            lines = text[:2000].split('\n')
            title = "Unknown"
            for line in lines[:20]:
                stripped = line.strip()
                if stripped and len(stripped) > 5 and len(stripped) < 200:
                    # Skip common boilerplate
                    if not any(skip in stripped.lower() for skip in
                               ['project gutenberg', 'utf-8', 'encoding',
                                'copyright', '***', 'ebook', 'e-book']):
                        title = stripped
                        break

            book_id = f"hf_{i:04d}"
            text_file = f"book_{book_id}.txt"

            # Cache text to file
            with open(f"{CORPUS_DIR}/{text_file}", 'w', encoding='utf-8') as f:
                f.write(text)

            metadata = {
                'id': book_id,
                'title': title,
                'author': 'Unknown',  # dataset doesn't include author metadata
                'publication_year': None,
                'source_url': 'https://huggingface.co/datasets/AlekseyKorshuk/mystery-crime-books',
                'text_file': text_file,
                'full_text': text,
                '_source': 'huggingface',
                '_hf_index': i,
            }
            corpus.append(metadata)
            print(f"  [{i+1}/{min(limit, len(ds))}] {title[:60]}... ({len(text)} chars)")

        # Save corpus index
        index_entries = []
        for entry in corpus:
            index_entry = {k: v for k, v in entry.items() if k != 'full_text'}
            index_entries.append(index_entry)

        with open(CORPUS_INDEX, 'w') as f:
            json.dump({
                'source': 'huggingface',
                'dataset': 'AlekseyKorshuk/mystery-crime-books',
                'download_date': datetime.now().isoformat(),
                'book_count': len(corpus),
                'books': index_entries,
            }, f, indent=2)

        print(f"\nCorpus downloaded: {len(corpus)} mystery books cached")
        return corpus

    def force_download(self, query: str, limit: int, source: str = "gutenberg") -> List[Dict]:
        """Re-download corpus even if cache exists."""
        if os.path.exists(CORPUS_INDEX):
            os.remove(CORPUS_INDEX)
        if source == "huggingface":
            return self.download_huggingface_corpus(limit)
        return self.download_corpus(query, limit)


# ============================================================================
# EXPERIMENT RUNNER
# ============================================================================

def import_variant(variant_name: str):
    """Dynamically import a variant's processor and database classes."""
    import importlib
    config = VARIANT_MODULES[variant_name]
    module = importlib.import_module(config['module'])
    processor_cls = getattr(module, config['processor_class'])
    database_cls = getattr(module, config['database_class'])
    return processor_cls, database_cls, config['db_path']


def run_variant(variant_name: str, corpus: List[Dict]):
    """Run a single extraction variant against the full corpus."""
    config = VARIANT_MODULES[variant_name]
    print(f"\n{'='*60}")
    print(f"VARIANT: {variant_name.upper()}")
    print(f"{config['description']}")
    print(f"{'='*60}\n")

    processor_cls, database_cls, db_path = import_variant(variant_name)

    processor = processor_cls()
    database = database_cls(storage_path=db_path)

    results = []
    for i, book in enumerate(corpus, 1):
        print(f"[{i}/{len(corpus)}] {book['title']}")

        start_time = time.time()
        try:
            if variant_name == "template":
                scenario = processor.process_mystery(book['full_text'], book)
                database.save_template(scenario)
            else:
                scenario = processor.process_mystery(book['full_text'], book)
                database.save_scenario(scenario)

            elapsed = time.time() - start_time

            results.append({
                'title': book['title'],
                'variant': variant_name,
                'success': True,
                'elapsed_seconds': round(elapsed, 1),
                'scenario': scenario,
            })
            print(f"  Done in {elapsed:.1f}s\n")

        except Exception as e:
            elapsed = time.time() - start_time
            results.append({
                'title': book['title'],
                'variant': variant_name,
                'success': False,
                'elapsed_seconds': round(elapsed, 1),
                'error': str(e),
            })
            print(f"  Failed in {elapsed:.1f}s: {e}\n")

    return results


def print_comparison(all_results: Dict[str, List[Dict]]):
    """Print a comparison summary across all variants."""
    print(f"\n{'='*60}")
    print("EXPERIMENT COMPARISON")
    print(f"{'='*60}\n")

    # Collect book titles from first variant that has results
    titles = []
    for results in all_results.values():
        if results:
            titles = [r['title'] for r in results]
            break

    # Header
    variants = list(all_results.keys())
    header = f"{'Book':<40} " + " ".join(f"{v:>10}" for v in variants)
    print(header)
    print("-" * len(header))

    # Time comparison per book
    print("\nProcessing time (seconds):")
    for title in titles:
        row = f"  {title[:38]:<40}"
        for v in variants:
            result = next((r for r in all_results[v] if r['title'] == title), None)
            if result and result['success']:
                row += f" {result['elapsed_seconds']:>9.1f}s"
            elif result:
                row += f" {'FAILED':>10}"
            else:
                row += f" {'N/A':>10}"
        print(row)

    # Summary stats
    print(f"\n{'Metric':<40} " + " ".join(f"{v:>10}" for v in variants))
    print("-" * (40 + 11 * len(variants)))

    for v in variants:
        successes = [r for r in all_results[v] if r['success']]
        total_time = sum(r['elapsed_seconds'] for r in successes)
        avg_time = total_time / len(successes) if successes else 0

        if v == "lean":
            # Lean-specific stats
            for r in successes:
                s = r['scenario']
                print(f"  {r['title'][:36]:<38} {v:>10}")
                print(f"    {'Suspects':<36} {len(s.suspects):>10}")
                print(f"    {'Real clues':<36} {len(s.real_clues):>10}")
                print(f"    {'Red herrings':<36} {len(s.red_herrings):>10}")
        elif v == "template":
            for r in successes:
                s = r['scenario']
                dp = s.deception_pattern
                print(f"  {r['title'][:36]:<38} {v:>10}")
                print(f"    {'Deception pattern':<36} {(dp.pattern_name if dp else 'N/A'):>10}")
                print(f"    {'Archetypes':<36} {len(s.character_archetypes):>10}")
                print(f"    {'Red herring techniques':<36} {len(s.red_herring_techniques):>10}")
        elif v == "rich":
            for r in successes:
                s = r['scenario']
                print(f"  {r['title'][:36]:<38} {v:>10}")
                print(f"    {'Characters':<36} {len(s.characters):>10}")
                print(f"    {'Clues':<36} {len(s.clues):>10}")
                print(f"    {'Solution paths':<36} {len(s.solution_paths):>10}")
                print(f"    {'Difficulty':<36} {s.estimated_difficulty:>10}")
        elif v == "baseline":
            for r in successes:
                s = r['scenario']
                print(f"  {r['title'][:36]:<38} {v:>10}")
                print(f"    {'Characters':<36} {len(s.characters):>10}")
                print(f"    {'Physical clues':<36} {len(s.physical_clues):>10}")
                print(f"    {'Testimonials':<36} {len(s.testimonial_revelations):>10}")
                print(f"    {'Timeline events':<36} {len(s.timeline):>10}")

    # Timing summary
    print(f"\n{'Timing Summary':<40} " + " ".join(f"{v:>10}" for v in variants))
    print("-" * (40 + 11 * len(variants)))
    row_total = f"  {'Total time':<38}"
    row_avg = f"  {'Avg per book':<38}"
    row_success = f"  {'Success rate':<38}"
    for v in variants:
        successes = [r for r in all_results[v] if r['success']]
        total = sum(r['elapsed_seconds'] for r in all_results[v])
        avg = total / len(all_results[v]) if all_results[v] else 0
        rate = f"{len(successes)}/{len(all_results[v])}"
        row_total += f" {total:>9.1f}s"
        row_avg += f" {avg:>9.1f}s"
        row_success += f" {rate:>10}"
    print(row_total)
    print(row_avg)
    print(row_success)

    print(f"\nOutput directories:")
    for v in variants:
        print(f"  {v}: {VARIANT_MODULES[v]['db_path']}/")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run extraction experiments against a shared corpus"
    )
    parser.add_argument("--source", default="gutenberg",
                        choices=["gutenberg", "huggingface"],
                        help="Corpus source: 'gutenberg' (scrape) or 'huggingface' "
                             "(AlekseyKorshuk/mystery-crime-books, 359 books)")
    parser.add_argument("--query", default="sherlock holmes",
                        help="Gutenberg search query (default: 'sherlock holmes')")
    parser.add_argument("--limit", type=int, default=3,
                        help="Number of books to download (default: 3)")
    parser.add_argument("--variants", default="baseline,lean,rich,template",
                        help="Comma-separated variants to run (default: all)")
    parser.add_argument("--download-only", action="store_true",
                        help="Download corpus only, don't process")
    parser.add_argument("--process-only", action="store_true",
                        help="Process only, corpus must already exist")
    parser.add_argument("--force-download", action="store_true",
                        help="Re-download corpus even if cached")

    args = parser.parse_args()

    # Check API key
    if not args.download_only and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("(or use --download-only to just fetch the corpus)")
        sys.exit(1)

    # Download corpus
    manager = CorpusManager()
    if args.process_only:
        if not os.path.exists(CORPUS_INDEX):
            print("ERROR: No corpus found. Run without --process-only first.")
            sys.exit(1)
        corpus = manager._load_index()
    elif args.force_download:
        corpus = manager.force_download(args.query, args.limit, args.source)
    elif args.source == "huggingface":
        corpus = manager.download_huggingface_corpus(args.limit)
    else:
        corpus = manager.download_corpus(args.query, args.limit)

    print(f"Corpus: {len(corpus)} books loaded\n")
    for book in corpus:
        print(f"  - {book['title']} by {book['author']} "
              f"({len(book['full_text'])} chars)")
    print()

    if args.download_only:
        print("Corpus downloaded. Run with --process-only to extract.")
        return

    # Run variants
    variants = [v.strip() for v in args.variants.split(",")]
    valid_variants = [v for v in variants if v in VARIANT_MODULES]

    if not valid_variants:
        print(f"ERROR: No valid variants. Choose from: {list(VARIANT_MODULES.keys())}")
        sys.exit(1)

    all_results = {}
    for variant in valid_variants:
        all_results[variant] = run_variant(variant, corpus)

    # Print comparison
    print_comparison(all_results)


if __name__ == "__main__":
    main()
