# P1→P1P2P3 extraction — running it, and what to do when it breaks

Written Session 34, August 21 2026, immediately after getting the run working end to end.
Every symptom below is one that was actually hit, or one the code can still produce.

**A future session picking this up:** the run is **idempotent and resumable**. `--upgrade`
re-extracts a source only when its existing file lacks a requested protocol, so re-running the
same command after any failure resumes rather than re-paying. When in doubt, re-run the plan.

---

## The commands

```bash
python3 scripts/upgrade_p1_to_p1p2.py --check-sources   # free: are the PDFs readable?
python3 scripts/upgrade_p1_to_p1p2.py                   # free: the plan and the cost
python3 scripts/upgrade_p1_to_p1p2.py --go              # spends money
```

Useful flags: `--source-dir DIR` (search outside the repo, repeatable), `--model`,
`--novel-chars N`, `--find-missing`.

Scope is the **75 P1-only extractions**, run at **P1P2P3** on **claude-opus-5**, ~$0.147/source.
It deliberately does *not* deepen the 206 sources already at P1P2 — that is ~$83 and a separate
decision.

---

## Errors, in the order they are likely to appear

### `ERROR: no credentials. Set ANTHROPIC_API_KEY…`
Expected outside a Claude session. `export ANTHROPIC_API_KEY=sk-ant-…`, or put it in `.env`.
The session-ingress fallback only works inside a Claude Code session.

### `argument --protocol: invalid choice: 'P1P2P3'`
A stale checkout. `--protocol` accepted only single values until Session 34, even though the
code consuming it always split combined ones. `git pull` and retry.

### `SKIP … (already extracted)` on every source, nothing spent
The `--upgrade` flag is missing, or the checkout predates it. Dedup is by output filename, so
without `--upgrade` an already-extracted source is skipped before anything checks its depth —
which is why `--protocol P1P2` on a P1-only source used to do nothing at all.

### `SKIP … (already has P1+P2+P3)`
Not an error. That source is done. If *every* source says this, the run finished.

### `ValueError: no text block in response (blocks: ['thinking']; stop_reason=max_tokens)`
The response spent its whole budget thinking and produced no text. Raise
`EXTRACTION_MAX_TOKENS` in `scripts/extract_from_pdfs.py` (currently 4000).

**This one is intermittent by nature.** Opus 5 runs *adaptive* thinking, deciding per request
whether to think — so a run can succeed thirty times and then hit it. If it appears once, it
will appear again; raise the ceiling rather than re-running and hoping.

### `AttributeError: 'ThinkingBlock' object has no attribute 'text'`
Same root cause, older code. Something is indexing `content[0]` instead of scanning for the
text block. `_first_text()` in `extract_from_pdfs.py` is the correct pattern; `server/main.py`
has its own copy. `git pull` if you see this in a file that should already be fixed.

### `WARNING … API error: … — retrying` then `ERROR … skipping, not saving a placeholder`
A network or API failure. Deliberate design (Session 23): nothing is saved, so the
dedup-by-filename rule lets the next run retry that source. Just re-run.

### JSON parse failure that *is* saved
Retried once; on a second failure the result is saved with `_meta.extraction_warnings`. Find them:

```bash
python3 -c "
import json,glob
for f in glob.glob('mystery_database/extractions/*.json'):
    w=json.load(open(f)).get('_meta',{}).get('extraction_warnings')
    if w: print(f.split('/')[-1], w)
"
```
To retry one: delete the file and re-run (dedup is by filename, so it will be re-extracted).

### `429` / rate limit
The SDK retries twice with backoff on its own. If it persists, stop and re-run later — the
work already done is kept.

### Detected story count looks wrong on an anthology
`--dry-run --anthology` lists the detected split without spending anything. The extractor also
warns when the detected count differs from the Contents page by more than 10%.

---

## Verifying the result

```bash
python3 scripts/test_registry_staleness.py     # the registry rebuild noticed the new parts
python3 scripts/upgrade_p1_to_p1p2.py          # should report 0 upgradeable
```

Then measure what it actually bought — the point of the whole exercise is axis coverage:

```bash
python3 -c "
import json,glob,collections
import part_registry as pr
axis=collections.Counter(); n=0
for f in glob.glob('mystery_database/extractions/*.json'):
    d=json.load(open(f))
    if not isinstance(d,dict) or '_meta' not in d: continue
    n+=1
    reg=pr.PartRegistry.__new__(pr.PartRegistry); reg.parts=[]
    reg._atomize_extraction(d,'x','x')
    for i in {p.part_index for p in reg.parts}: axis[i]+=1
for i,name in enumerate(pr.PART_TYPE_NAMES,1):
    print(f'{i} {name:18} {100*axis[i]/n:5.1f}%')
"
```

**Before this run** (Haiku, P1P2, 206 files): alibi 74.3%, suspect_archetype 80.1%,
crime_type 63.1%; 133 of 206 files yielded fewer than 13 parts, mean 10.3.
Those are the numbers to beat. On the one novel done here, *The Red House Mystery* went from
**4 parts to 19**.

---

## Undoing it

Every replaced extraction is moved to `mystery_database/extractions/_superseded/`, never
deleted. `PartRegistry.load_extractions` globs `*.json` non-recursively, so that directory is
never sampled by generation.

```bash
cp mystery_database/extractions/_superseded/*.json mystery_database/extractions/
python3 scripts/test_registry_staleness.py      # forces the registry to notice
```

Delete `_superseded/` only once the new extractions have been checked and committed.

---

## Things that are NOT errors

- **A source stays BLOCKED.** Its PDF is not on this machine. `--find-missing` names them and
  writes `mystery_database/new_sources/_MISSING_SOURCES.md`. PDFs are gitignored — they are
  extraction's input, not its output — so they never need committing or pushing.
- **A source is flagged "matched by title".** The filename on disk differs from the one the
  extraction recorded. Matching tolerates punctuation and a missing author but accepts only a
  *unique* hit; a single-shared-word tier was tried and removed because it matched
  *Turkish Delight Mystery* to *Turkish Gambit*. Check the flagged one before running.
- **Novels sample 24,000 chars, anthology stories up to 25,000.** The extractor's own default
  is 6,000 — ~1.7% of a novel — which is thin for P2/P3, whose fields describe structure only
  visible across a whole book. `--novel-chars` controls it.
