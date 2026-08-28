"""The critic — one Claude call that reads a finished mystery and reports faults.

WHAT A CRITIC IS, PRECISELY. Its input is a finished artefact and its output is a
judgement about that artefact. It does not rewrite anything. That distinguishes
it from the three things it is easily confused with:

    validator   ordinary code checking structure. Free, certain, no opinions.
                coherence_validator.py and scripts/check_narrative.py.
    critic      this file. One API call, reads a lot, writes a little.
    reviser     a call that rewrites the faulty part. Not built.
    re-roll     throw the mystery away and generate again. A full generation.

WHY IT IS CHEAP, WHICH IS NOT OBVIOUS. docs/AI_COST_PLAYBOOK.md measures a
generation at $0.1374 with output at 95% of it: a short prompt buying a long
answer. A critic inverts that shape — the whole mystery goes in, a short verdict
comes out — so it costs a fraction of a generation even on a more expensive
model. Meaning is the cheapest kind of call this pipeline can make, precisely
because what makes generation expensive is length of output.

WHY A DIFFERENT MODEL FROM THE GENERATOR. A model reviewing its own work tends
to approve it. Gameplay generation runs on Sonnet (server/main.py MODEL); the
critic runs on Opus by default, so the reviewer is not the author.

WHY THE RUBRIC ENUMERATES INSTEAD OF ASKING. "Is this mystery coherent?" is a
vibe check and will agree with whatever it is shown. "List every person named in
the deduction, and for each say whether they appear in characters[]" is a
question with a countable answer that can be checked afterwards. Every section
of the rubric below is written in that shape, and every finding must cite the
text it is about.

WHAT IT COVERS THAT NOTHING ELSE CAN. scripts/check_narrative.py already proves
the declared links are self-consistent — that `supports` resolves, that
elimination leaves one suspect. What it cannot do is tell whether a label is
TRUE: a clue may declare `supports: ["S2"]` and not support S2, and no
structural check will ever see it. Reading the prose is the only way. So the
critic re-asks the structural questions on purpose, and a disagreement between
the two is the most valuable thing this file produces.
"""

from __future__ import annotations

import json
import re
from typing import Optional

# Opus by default: see "why a different model from the generator" above. The
# generator runs on Sonnet, so this is deliberately not the same model.
DEFAULT_MODEL = "claude-opus-5"

# Short by construction. The rubric asks for findings, not prose, and the whole
# economic argument for a critic is that its output stays small. The ceiling is
# generous rather than tight because adaptive thinking is billed against it and
# a truncated response is not a discount — see AI_COST_PLAYBOOK lever 3.
MAX_TOKENS = 16000

SYSTEM = (
    "You are a mystery editor auditing a generated murder-mystery scenario for a "
    "party game. You report faults; you never rewrite. Return only valid JSON."
)


def build_prompt(mystery: dict) -> str:
    """The rubric. Every section demands an enumeration, not an opinion."""
    user_prompt = (mystery.get("_meta") or {}).get("user_prompt")
    delivery_section = (
        f"""
D. DELIVERY — did we make the mystery that was asked for?
   The player typed exactly this:

       "{user_prompt}"

   Say whether the mystery delivers it. Name the specific elements that do, and
   any part of the request that went unanswered or was quietly replaced.
"""
        if user_prompt
        else """
D. DELIVERY — skipped. This mystery predates prompt storage, so what the player
   asked for was not recorded and delivery cannot be judged. Report one finding
   with code "delivery.prompt_not_recorded" at severity NOTE and move on.
"""
    )

    return f"""Audit this mystery. Work through every section. Do not skip one because
another looked fine.

For EVERY finding, quote the text you are judging. A finding with no quotation is
not a finding.

--- THE MYSTERY ---
{json.dumps(mystery, indent=2, ensure_ascii=False)}
--- END ---

A. CAST — enumerate, do not summarise.
   List every PERSON named anywhere in solution.method, solution.motive,
   solution.chain and solution.how_to_deduce. For each one, state whether they
   appear in "characters" by that name. A person the solution reasons about who
   is not in the cast cannot be met, questioned or accused, and is a BLOCKING
   fault. Historical or background figures nobody could interrogate are fine —
   say so rather than flagging them.

B. THE CHAIN, BACKWARD — for each step in solution.chain, in order:
   name the evidence that supports it, and then the act that produced that
   evidence. A step with no evidence behind it is a leap the player cannot make.
   A step whose evidence has no cause is a fact that exists only because the plot
   needed it.

C. THE CLUES, FORWARD — for each item in "evidence", in order:
   name the act that produced it. Then judge whether the declared labels are
   TRUE, which is the one thing structural checking cannot do:
     - does it really support the chain steps its "supports" names?
     - does it really clear everyone its "exonerates" names?
     - does it really point at everyone its "implicates" names?
     - if it is a red_herring, is the act that produced it genuinely innocent?
   A label that is present but false is worse than a missing one, because
   everything downstream trusts it. Flag each with code "label.false".
{delivery_section}
E. MOTIVE — is the stated motive sufficient for THIS crime by THIS person?
   Not "is it a motive" — money is always a motive. Would this person, with this
   stake, do this specific thing? Say what is missing if it is thin.

F. METHOD — is the method possible as described?
   Check it against the alibis, the timeline and the physical setting. Name any
   conflict: two people in one place, an act with no time to happen in, a locked
   door nobody could pass.

Return JSON in exactly this shape and nothing else:

{{
  "verdict": "SOUND | FLAWED | BROKEN",
  "summary": "two sentences at most",
  "findings": [
    {{
      "code": "cast.not_in_characters | chain.unsupported | clue.uncaused | label.false | delivery.* | motive.insufficient | method.impossible",
      "severity": "BLOCKING | WARNING | NOTE",
      "claim": "what is wrong, one sentence",
      "citation": "the exact text from the mystery that shows it"
    }}
  ]
}}

BROKEN means a player could not win or could not follow the answer. FLAWED means
it plays but something is wrong. SOUND means you found nothing blocking — say so
plainly rather than inventing a finding to look thorough."""


def _extract_json(raw: str) -> dict:
    """Pull the JSON object out of a response.

    Written here rather than imported from server/main.py on purpose: that module
    imports FastAPI, and this one must run from a plain script with nothing but
    the Anthropic SDK installed.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if fenced:
        raw = fenced.group(1)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in response: {raw[:200]}")
    return json.loads(raw[start:end + 1])


def count_input_tokens(mystery: dict, client, model: str = DEFAULT_MODEL) -> int:
    """Free. Used by the dry run to price a batch before spending anything."""
    return client.messages.count_tokens(
        model=model,
        system=SYSTEM,
        messages=[{"role": "user", "content": build_prompt(mystery)}],
    ).input_tokens


def critique(mystery: dict, client, model: str = DEFAULT_MODEL) -> dict:
    """One call. Returns the parsed report, plus what it cost."""
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": build_prompt(mystery)}],
    )

    if response.stop_reason == "refusal":
        detail = getattr(response, "stop_details", None)
        raise RuntimeError(
            f"critic refused: {getattr(detail, 'category', 'unknown')} — "
            f"{getattr(detail, 'explanation', '')}")

    text = "".join(b.text for b in response.content if b.type == "text")
    report = _extract_json(text)
    report["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "model": model,
        "stop_reason": response.stop_reason,
    }
    return report


def summarise(report: dict) -> str:
    """One line per report, for a batch run's console output."""
    findings = report.get("findings") or []
    blocking = sum(1 for f in findings if f.get("severity") == "BLOCKING")
    warning = sum(1 for f in findings if f.get("severity") == "WARNING")
    return (f"{report.get('verdict', '?'):<7} "
            f"{blocking} blocking, {warning} warning, {len(findings)} total")
