## Task: Pull Script 03 — Causal Chain Extraction

Goal: Build the target PlayableMystery JSON schema and Script 3 (Causal Chain),
which extracts a cause→effect clue graph from mystery source text and evaluates
game playability via MCD, RSE, and UST metrics.

- [x] Read existing codebase (mystery_data_acquisition.py, demo_acquisition.py)
- [x] Define evaluation criteria: solvable in ≤4 rounds, Q&A driven, multi-player sharing
- [x] Design PlayableMystery target JSON schema (dataclasses)
- [x] Implement CausalChainExtractor (Claude API)
- [x] Implement MockCausalChainExtractor (demo, no API)
- [x] Implement PlayabilityCalculator (MCD, RSE, UST, composite score)
- [x] Write demo __main__ block and verify output
- [ ] Commit and push

## Metrics Defined

| Metric | Target | Description |
|--------|--------|-------------|
| MCD (Minimum Clue Depth) | 4–8 | Fewest clues to uniquely solve |
| RSE (Round-to-Solution Estimate) | ≤4 rounds | Rounds needed with N players + 75% sharing |
| UST (Unique Solution Test) | Pass | Exactly one valid culprit |
| Playability Score | 0.0–1.0 | Composite of above |

## Results
Verified via `python pull_script_03_causal_chain.py` (demo mode, no API needed):
- 6 characters, 9 clues (7 real + 2 red herrings)
- UST: PASS | MCD: 3 | RHR: 22% | RSE: 3 rounds (3/4/5 players)
- Playability score: 0.950 — EXCELLENT
- Output saved to: causal_chain_output/causal_the_locked_room_mystery.json
