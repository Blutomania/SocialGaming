"""
Corpus Loader
=============

Loads the mystery-crime-books Parquet corpus from a local clone of:
    https://huggingface.co/datasets/AlekseyKorshuk/mystery-crime-books

The dataset has 359 rows, each with:
    - url   : source URL of the book text
    - text  : full book content (plain text)

This module replaces the GutenbergScraper step in the acquisition pipeline.
The MysteryProcessor and MysteryDatabase remain unchanged.

Usage:
    from corpus_loader import CorpusLoader

    loader = CorpusLoader("./mystery-crime-books")
    for row in loader.iter_rows():
        print(row["url"], len(row["text"]))
"""

import os
from pathlib import Path
from typing import Iterator, Optional
import pandas as pd


# ============================================================================
# CONSTANTS
# ============================================================================

PARQUET_FILENAME = "train-00000-of-00001.parquet"
MIN_TEXT_LENGTH  = 2_000     # rows shorter than this are skipped (headers, stubs)
MAX_TEXT_LENGTH  = 500_000   # rows longer than this are truncated before processing


# ============================================================================
# CORPUS LOADER
# ============================================================================

class CorpusLoader:
    """
    Reads the mystery-crime-books Parquet file and yields rows one at a time.

    Args:
        corpus_dir: path to the cloned mystery-crime-books repo
                    (the directory that contains the .parquet file)
    """

    def __init__(self, corpus_dir: str = "./mystery-crime-books"):
        self.corpus_dir = Path(corpus_dir)
        # HuggingFace dataset clones nest the parquet under data/
        data_subdir = self.corpus_dir / "data"
        if (data_subdir / PARQUET_FILENAME).exists():
            self.parquet_path = data_subdir / PARQUET_FILENAME
        else:
            self.parquet_path = self.corpus_dir / PARQUET_FILENAME
        self._df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """
        Load the Parquet file into memory.
        Call this once before iterating. Safe to call multiple times.
        """
        if self._df is not None:
            return

        if not self.parquet_path.exists():
            raise FileNotFoundError(
                f"Parquet file not found at: {self.parquet_path}\n"
                f"Clone the corpus repo first:\n"
                f"  git clone https://huggingface.co/datasets/AlekseyKorshuk/mystery-crime-books"
            )

        print(f"Loading corpus from: {self.parquet_path}")
        self._df = pd.read_parquet(self.parquet_path)
        print(f"  Loaded {len(self._df)} rows | columns: {list(self._df.columns)}")

    def total_rows(self) -> int:
        """Total number of rows in the corpus (including short/empty ones)."""
        self.load()
        return len(self._df)

    def usable_rows(self) -> int:
        """Rows that pass the minimum text-length filter."""
        self.load()
        return int((self._df["text"].str.len() >= MIN_TEXT_LENGTH).sum())

    def iter_rows(
        self,
        start: int = 0,
        end: Optional[int] = None,
        skip_short: bool = True,
    ) -> Iterator[dict]:
        """
        Yield corpus rows as dicts, one at a time.

        Each dict contains:
            index    : 0-based position in the corpus
            url      : source URL string
            text     : book text (truncated to MAX_TEXT_LENGTH if very long)
            text_len : character count of the original text

        Args:
            start      : first row index to yield (0-based, inclusive)
            end        : last row index to yield (exclusive); None = all rows
            skip_short : if True, skip rows shorter than MIN_TEXT_LENGTH
        """
        self.load()
        df_slice = self._df.iloc[start:end]

        for idx, row in df_slice.iterrows():
            text = str(row.get("text", "") or "")
            url  = str(row.get("url",  "") or "")

            if skip_short and len(text) < MIN_TEXT_LENGTH:
                continue

            yield {
                "index":    int(idx),
                "url":      url,
                "text":     text[:MAX_TEXT_LENGTH],
                "text_len": len(text),
            }

    def iter_batches(
        self,
        batch_size: int = 10,
        start: int = 0,
        end: Optional[int] = None,
    ) -> Iterator[list[dict]]:
        """
        Yield rows in batches. Useful for resumable pipeline runs.

        Args:
            batch_size : number of rows per batch
            start      : first row to include
            end        : last row (exclusive)
        """
        batch = []
        for row in self.iter_rows(start=start, end=end):
            batch.append(row)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def get_row(self, index: int) -> dict:
        """Return a single row by its 0-based corpus index."""
        self.load()
        row = self._df.iloc[index]
        text = str(row.get("text", "") or "")
        return {
            "index":    index,
            "url":      str(row.get("url", "") or ""),
            "text":     text[:MAX_TEXT_LENGTH],
            "text_len": len(text),
        }

    def sample(self, n: int = 5, random_state: int = 42) -> list[dict]:
        """Return n random rows (useful for spot-checking the corpus)."""
        self.load()
        sample_df = self._df[self._df["text"].str.len() >= MIN_TEXT_LENGTH].sample(
            n=min(n, self.usable_rows()), random_state=random_state
        )
        return [
            {
                "index":    int(idx),
                "url":      str(row.get("url", "") or ""),
                "text":     str(row.get("text", "") or "")[:MAX_TEXT_LENGTH],
                "text_len": len(str(row.get("text", "") or "")),
            }
            for idx, row in sample_df.iterrows()
        ]

    def print_stats(self) -> None:
        """Print a summary of corpus statistics."""
        self.load()
        lengths = self._df["text"].str.len().dropna()
        usable  = (lengths >= MIN_TEXT_LENGTH).sum()

        print("\n=== Corpus Statistics ===")
        print(f"  Total rows    : {len(self._df)}")
        print(f"  Usable rows   : {usable}  (>= {MIN_TEXT_LENGTH:,} chars)")
        print(f"  Skipped rows  : {len(self._df) - usable}")
        print(f"  Median length : {int(lengths.median()):,} chars")
        print(f"  Max length    : {int(lengths.max()):,} chars")
        print(f"  Min length    : {int(lengths.min()):,} chars")
        print(f"  Total text    : {int(lengths.sum()) // 1_000_000:.1f} MB")
        print()


# ============================================================================
# METADATA BUILDER
# ============================================================================

def row_to_metadata(row: dict) -> dict:
    """
    Convert a corpus row to the metadata dict expected by MysteryProcessor.

    MysteryProcessor.process_mystery(raw_text, metadata) expects:
        title          : str
        author         : str
        source_url     : str
        publication_year: int | None

    We infer title and author from the URL where possible.
    """
    url = row["url"]

    # Try to extract a readable title from the URL path
    # e.g. "https://gutenberg.org/files/1661/1661-0.txt" → "1661-0"
    path_part = url.rstrip("/").split("/")[-1]
    title = path_part.replace("-", " ").replace("_", " ").strip() or "Unknown"

    return {
        "title":            title,
        "author":           "Unknown",
        "source_url":       url,
        "publication_year": None,
    }


# ============================================================================
# CLI: quick inspection
# ============================================================================

if __name__ == "__main__":
    import sys

    corpus_dir = sys.argv[1] if len(sys.argv) > 1 else "./mystery-crime-books"
    loader = CorpusLoader(corpus_dir)

    loader.print_stats()

    print("=== 3 Sample Rows ===\n")
    for row in loader.sample(n=3):
        print(f"  [{row['index']}] {row['url']}")
        print(f"       length : {row['text_len']:,} chars")
        print(f"       preview: {row['text'][:120].strip()!r}")
        print()
