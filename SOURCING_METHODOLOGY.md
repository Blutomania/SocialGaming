# Choose Your Mystery — Craft Sourcing Methodology

## Purpose

`RESEARCH_FINDINGS.md`, `SCREEN_CRAFT_FINDINGS.md`, and `PARTY_CRAFT_FINDINGS.md` each ground the
mystery generator's craft authority in a different medium (prose novelists, film/TV, live
social-deduction games). The second and third documents independently arrived at the same
sourcing discipline while being built. This document extracts that discipline into one place so
the next companion doc doesn't have to re-derive it, and so a session evaluating a new source
knows the bar it needs to clear.

## Confidence tiers

Every cited insight gets one of three tags:

1. **`[full text verified]`** — the source's own full text was directly available (user-pasted,
   or fetched in full), not a search-engine summary. Treat as an accurate quote.
2. **Primary-source, clearly attributed** (no explicit tag — the default) — a `WebSearch`-returned
   excerpt from the creator's own interview/blog/notebook, with a specific named outlet and URL.
   Treat as accurate paraphrase/excerpt, not manually verified verbatim.
3. **`[third-party analysis]` / secondary attribution** — commentary *about* the creator's choices
   (criticism, fan-site digests, listicles summarizing an interview) rather than the creator's own
   words, or a search snippet where the originating outlet couldn't be confirmed. Lowest
   confidence; flag explicitly, don't present as a direct quote.

**Hard gate:** nothing below tier 1 feeds an actual generation prompt. Tiers 2–3 are fine for
building out a companion doc's craft-grounding corpus, but anything destined for
`server/main.py`'s live prompt needs a verification pass against full source text first.

## Corroboration rule

A "new concept" (something with no existing P1–P4 or game-system-category home) only gets
promoted to a **"Cross-source concepts worth flagging together"** section — the signal that
justifies eventually adding a taxonomy code — once **2 or more independent creators/sources**
name it separately. A single source naming something stays in that source's own section,
flagged as a candidate, not promoted. This mirrors `RESEARCH_FINDINGS.md`'s original "Cross-Writer
Consensus" rule (3+ writers), scaled down slightly since companion docs cover fewer sources per
medium so far.

## Design authority vs. reception evidence

Keep these in visibly separate registers — never blend them:

- **Design/craft authority** — the creator, designer, or producer explaining their own reasoning
  (an interview, a design blog, a writers'-room account). This is what actually grounds a taxonomy
  code.
- **Reception evidence** — testimonials, reviews, journalism about audience psychology. Useful as
  corroborating *validation* that a design choice works in practice, but never cited as if it were
  the creator's own stated intent. `PARTY_CRAFT_FINDINGS.md`'s Part 1 / Part 2 split is the
  reference pattern for this.

## Scope discipline

- Capture **craft/process commentary only** — how something was built and why — never the
  underlying narrative content itself. This matters most for true-crime sourcing: quote a host's
  own reflection on *why* a case is compelling, never reproduce the case narrative as source
  material for a generated mystery.
- Exclude material that's off-topic for craft grounding even if it's about the same creator (e.g.
  Pizzolatto's plagiarism-allegation coverage was excluded from `SCREEN_CRAFT_FINDINGS.md` as out
  of scope — not a craft insight).
- Omit findings with no game-relevant analogue rather than force-mapping them (e.g. McQuarrie's
  camera/cinematography rules were noted and explicitly excluded, not stretched onto a category
  that doesn't fit).

## Mapping convention

Map each finding onto exactly one of:

- An existing **P1–P4 taxonomy code** (`extraction_protocols.py` C1–C6 / M1–M8 / F1–F12), if it
  fits — cite the code directly (e.g. "Extends M3 Clue Fairness").
- An existing **game-system category** (75% Sharing Mechanic, Interrogation Phase, Investigation/
  Scene Phase, Accusation/Reveal Phase, Replayability/Generation, Host/GM Function, Social
  Dynamics, Win Condition Design — see `PARTY_CRAFT_FINDINGS.md`), for mechanics-level findings
  that aren't about plot construction at all.
- A **"New concepts flagged for taxonomy consideration"** subsection, if neither fits. Never
  silently edit `extraction_protocols.py` or invent a new code from a single finding — surface it
  for a human decision instead.

## Known technical constraint

Direct `WebFetch` to most interview/article hosts is blocked by this session's egress policy (403
on CONNECT — confirmed via `$HTTPS_PROXY/__agentproxy/status` as a policy denial, not a site-side
block). `WebSearch` is unaffected and is the default research path. When a finding needs to reach
`[full text verified]` confidence, ask the user to paste the full source text directly rather than
attempting a fetch workaround.

## Process for evaluating a new media type or source

1. **Confirm the gap.** Check this doc and the three existing companion docs — don't duplicate a
   medium already covered. Covered so far: prose novelists, film/TV, live/social-deduction games.
   Open candidates: true-crime podcast producers/hosts (discussed, not yet started); other
   candidates worth considering if this expands further: tabletop/board mystery game designers,
   escape-room designers, interactive-fiction/visual-novel writers.
2. **Prioritize primary craft-reflection sources** for that medium — interviews, design blogs,
   writers'-room accounts, notebooks — over reviews or third-party analysis. Reception evidence
   (Part 2-style) is worth collecting too, but never as a substitute for design authority.
3. **Search, don't fetch** — use `WebSearch` per the constraint above; note the outlet and URL for
   every excerpt.
4. **Tag confidence honestly** per the tiers above as you go — don't upgrade a search snippet to
   "verified" for convenience.
5. **Only promote cross-source concepts** once a second independent source corroborates them.
6. **Map every finding** to an existing taxonomy code or game-system category, or flag it as new —
   never leave a finding unmapped.
7. **Add to the relevant companion doc**, or start a new one if it's genuinely a new medium; update
   that doc's `Sources` list.
8. **Log the session** in `SESSIONS.md` and update `CLAUDE.md`'s Current To-Do — don't leave a
   research pass undocumented, per this repo's Session End Protocol.
