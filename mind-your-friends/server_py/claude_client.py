# Ported from lib/claudeClient.js. All Claude API calls live here — the
# Godot client never touches the API key (same rule CYM's server/main.py
# and the JS version both already follow).

import json
import os
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor

from anthropic import Anthropic

from constants import CATEGORIES_PER_FETCH_BATCH, FACTS_PER_CATEGORY

MODEL = "claude-sonnet-4-6"
INGRESS_TOKEN_FILE = "/home/claude/.claude/remote/.session_ingress_token"

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def _build_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return Anthropic(api_key=api_key)
    if os.path.exists(INGRESS_TOKEN_FILE):
        with open(INGRESS_TOKEN_FILE) as f:
            auth_token = f.read().strip()
        return Anthropic(auth_token=auth_token)
    return None


_client = _build_client()


def _require_client():
    if _client is None:
        raise RuntimeError(
            "No API key found. Set ANTHROPIC_API_KEY or ensure ingress token exists."
        )
    return _client


def _parse_json(text: str):
    """Claude sometimes wraps JSON replies in a ```json ... ``` fence despite
    being asked for raw JSON — strip it before parsing."""
    trimmed = text.strip()
    m = _JSON_FENCE_RE.search(trimmed)
    return json.loads(m.group(1) if m else trimmed)


def fetch_facts_batch(categories: list[str], on_progress=None) -> dict:
    """Fetch structured factoids for a batch of categories. Called at game
    start to build the fact bank — all questions are later constructed from
    these factoids rather than generated from scratch per turn.

    The batches are independent, so they run CONCURRENTLY in a thread pool
    rather than in sequence — the same change as lib/claudeClient.js's
    Promise.all, and for the same reason: 5 sequential ~50s batches is what
    made game start take ~250s and read as a hang. See CLAUDE.md item 36.
    The Anthropic SDK client is thread-safe, and this function is already
    called off the event loop (start_game_endpoint is a plain `def`, so
    FastAPI runs it in the thread pool), so blocking here is fine.

    `on_progress(completed, total)` — optional; called once with (0, total)
    before any request goes out, then again as each batch lands. `completed`
    counts finished batches in completion order, not batch order. Called from
    worker threads, so it must be cheap and thread-safe; main.py's callback
    just fires a broadcast.
    """
    anthropic = _require_client()

    batches = [
        categories[i:i + CATEGORIES_PER_FETCH_BATCH]
        for i in range(0, len(categories), CATEGORIES_PER_FETCH_BATCH)
    ]

    progress_lock = threading.Lock()
    completed = 0

    def report(n: int) -> None:
        # A throwing progress callback must never take the game start down
        # with it — the fact bank is the real work, progress is decoration.
        if on_progress is None:
            return
        try:
            on_progress(n, len(batches))
        except Exception as e:  # noqa: BLE001
            print(f"fetch_facts_batch progress callback failed: {e}")

    report(0)

    def run_batch(batch: list[str]) -> dict:
        nonlocal completed
        category_list = ", ".join(f'"{c}"' for c in batch)

        prompt = f"""You are an expert researcher. For each of the following categories: {category_list}

Provide {FACTS_PER_CATEGORY} diverse, strictly factual data points per category. Organize each category's facts into these five buckets (2 facts per bucket):

1. Catalyst & Origins: Key dates, events, and underlying factors that caused or initiated this topic.
2. Execution & Methodology: The primary strategies, tools, techniques, or defining characteristics.
3. Key Figures & Collaborators: Crucial individuals, leaders, or recurring contributors.
4. Major Milestones & Turning Points: The most significant events, releases, or awards.
5. Verified Trivia & Behind-the-Scenes: Esoteric, lesser-known, yet confirmed and documented anecdotes.

Each fact must be objective and free of opinion or speculation.

Respond with ONLY a JSON object mapping each category to its array of facts:
{{
  "Category Name": [
    {{
      "fact": "A clear, specific factual statement",
      "answer": "The key piece of information (the trivia answer)",
      "bucket": 1,
      "difficulty": "easy",
      "answerWordCount": 2,
      "questionAngles": ["naming", "year", "person-to-achievement"],
      "sourceType": "encyclopedia"
    }}
  ]
}}

difficulty must be "easy", "medium", or "hard". Buckets 1-3 should lean easy/medium, bucket 4 medium/hard, bucket 5 hard.
questionAngles is an array of 1-3 strings describing how this fact could be asked as a trivia question (e.g. "naming", "year", "person-to-achievement", "number", "location", "cause-effect").
answerWordCount is the word count of the answer field.
sourceType is the kind of reference this fact would be found in. Use one of: "encyclopedia", "biography", "news-archive", "awards-registry", "music-database", "sports-database", "academic-journal", "government-record", "industry-publication", "documentary", "interview", "almanac"."""

        response = anthropic.messages.create(
            model=MODEL, max_tokens=4096, messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text
        parsed = _parse_json(text)
        with progress_lock:
            completed += 1
            done = completed
        report(done)
        return parsed

    with ThreadPoolExecutor(max_workers=max(1, len(batches))) as pool:
        # list() re-raises the first failure, matching the old sequential
        # behaviour where a bad batch aborted the whole fact-bank build.
        parsed_batches = list(pool.map(run_batch, batches))

    # Merged in batch order, not completion order, so an overlapping category
    # name resolves the same way it did when these ran sequentially.
    results: dict = {}
    for parsed in parsed_batches:
        results.update(parsed)
    return results


def generate_question(*, constraints, factoid, active_player_name, player_names):
    """Generate a question for the active player.

    `constraints` — assembled by the Coherence Engine (coherence.py, not yet
    ported — see docs/WIRING.md). Contains promptInstructions (list of str),
    category, difficulty, and any card effects.
    """
    anthropic = _require_client()

    instructions = "\n".join(constraints["promptInstructions"])
    other_players = ", ".join(n for n in player_names if n != active_player_name)

    if factoid:
        angle = random.choice(factoid["questionAngles"]) if factoid.get("questionAngles") else ""
        prompt = f"""You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Build a trivia question from this factoid for {active_player_name}
(other players: {other_players}).

Factoid: {factoid['fact']}
Answer: {factoid['answer']}
Question angle: {angle}

{instructions}

Turn this factoid into an engaging trivia question using the given angle.
The answer MUST be exactly: {factoid['answer']}

Respond with ONLY a JSON object, no other text:
{{
  "question": "the trivia question text",
  "answer": "{factoid['answer']}",
  "hostQuip": "a short, personalized, game-show-host-style line addressed to {active_player_name} introducing the question"
}}"""
    else:
        prompt = f"""You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Generate one trivia question for {active_player_name} (other
players: {other_players}).

{instructions}

By default, the correct answer should be a short phrase of MORE than 3 words,
unless a card or round rule overrides this.

Respond with ONLY a JSON object, no other text:
{{
  "question": "the trivia question text",
  "answer": "the correct answer",
  "hostQuip": "a short, personalized, game-show-host-style line addressed to {active_player_name} introducing the question"
}}"""

    response = anthropic.messages.create(
        model=MODEL, max_tokens=2048, messages=[{"role": "user", "content": prompt}]
    )
    return _parse_json(response.content[0].text)


def generate_lineup_options(*, factoid, active_player_name, player_names):
    """Generate a 'pick the right one' multiple-choice question for The
    Lineup round rule — 5 options, exactly one correct."""
    anthropic = _require_client()
    other_players = ", ".join(n for n in player_names if n != active_player_name)

    if factoid:
        prompt = f"""You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Build a "pick the right one" multiple-choice question from this
factoid for {active_player_name} (other players: {other_players}).

Factoid: {factoid['fact']}
Correct answer: {factoid['answer']}

One of the 5 options MUST be exactly "{factoid['answer']}". Generate 4 decoy
options that are plausible near-misses — real adjacent entities that are NOT
correct, or believable invented look-alikes. Decoys should genuinely tempt a
guess, not be obviously wrong.

Respond with ONLY a JSON object, no other text:
{{
  "question": "the multiple-choice question text",
  "options": ["option A", "option B", "option C", "option D", "option E"],
  "correctIndex": 0,
  "hostQuip": "a short, personalized, game-show-host-style line addressed to {active_player_name} introducing the question"
}}

"options" must have exactly 5 short, distinct entries in random order.
"correctIndex" is the 0-based index of "{factoid['answer']}" within "options"."""
    else:
        prompt = f"""You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Generate one "pick the right one" multiple-choice question for
{active_player_name} (other players: {other_players}).

Pick a real, verifiable fact with one clearly correct answer. Generate 4
decoy options that are plausible near-misses — real adjacent entities that
are NOT correct, or believable invented look-alikes. Decoys should genuinely
tempt a guess, not be obviously wrong.

Respond with ONLY a JSON object, no other text:
{{
  "question": "the multiple-choice question text",
  "options": ["option A", "option B", "option C", "option D", "option E"],
  "correctIndex": 0,
  "hostQuip": "a short, personalized, game-show-host-style line addressed to {active_player_name} introducing the question"
}}

"options" must have exactly 5 short, distinct entries in random order.
"correctIndex" is the 0-based index of the correct one within "options"."""

    response = anthropic.messages.create(
        model=MODEL, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
    )
    return _parse_json(response.content[0].text)


def evaluate_answer(*, question, correct_answer, player_answer, round_rule):
    """Evaluate a player's answer."""
    anthropic = _require_client()

    rule_id = round_rule.get("id") if round_rule else None
    if rule_id == "eli5":
        evaluation_note = (
            "This is an ELI5 round — judge whether the player demonstrated "
            "understanding, not exact wording."
        )
    elif rule_id == "worstAnswerWins":
        evaluation_note = (
            "This is a Worst Answer Wins round — the answer should be factually "
            "wrong. Do not evaluate for correctness."
        )
    else:
        evaluation_note = (
            "Use fuzzy matching — minor wording differences, typos, or synonyms "
            "still count as correct."
        )

    prompt = f"""Question: {question}
Expected answer: {correct_answer}
Player's answer: {player_answer}

{evaluation_note}

Respond with ONLY a JSON object, no other text:
{{
  "correct": true or false,
  "feedback": "a short, host-style line reacting to the answer"
}}"""

    response = anthropic.messages.create(
        model=MODEL, max_tokens=512, messages=[{"role": "user", "content": prompt}]
    )
    return _parse_json(response.content[0].text)


def evaluate_worst_answers(*, question, correct_answer, submissions):
    """Score every player's submission for a Worst Answer Wins round in a
    single call."""
    anthropic = _require_client()

    listing = "\n".join(
        f'{i + 1}. {s["name"]}: "{s["answer"] or "(no answer submitted)"}"'
        for i, s in enumerate(submissions)
    )

    prompt = f"""Question: {question}
Expected correct answer: {correct_answer}

This is a "Worst Answer Wins" round — every player was told to submit an
answer that is confidently, entertainingly WRONG. Score each submission on
three axes, each 1-10:
- factuallyWrong: how far from the truth? 1 = maximally wrong, 10 = actually correct
- creativelyWrong: how inventive is the wrongness? 1 = most creative/funny, 10 = laziest/most boring
- plausibility: how convincing does it sound despite being false? 1 = most convincing, 10 = obviously absurd
A blank submission ("(no answer submitted)") should score 10 on all three axes —
they didn't attempt the bit.

Submissions:
{listing}

Respond with ONLY a JSON array, no other text, one object per submission in
the SAME ORDER as listed above:
[
  {{ "factuallyWrong": 1-10, "creativelyWrong": 1-10, "plausibility": 1-10, "feedback": "a short, host-style line reacting to this specific answer" }}
]"""

    response = anthropic.messages.create(
        model=MODEL, max_tokens=1536, messages=[{"role": "user", "content": prompt}]
    )
    scores = _parse_json(response.content[0].text)
    if not isinstance(scores, list) or len(scores) != len(submissions):
        raise ValueError("evaluate_worst_answers: response length did not match submissions")
    return scores


def moderate_heckle(*, heckle_text, active_player_name, heckler_name):
    """Moderate a Heckle submission via host-reinterpretation."""
    anthropic = _require_client()

    prompt = f"""You are the AI host of "Mind Your Friends," a social trivia game.
A player named {heckler_name} submitted this heckle aimed at {active_player_name}:

"{heckle_text}"

Your job: deliver this heckle in your game-show-host voice. Rules:
- Light trash talk, teasing, and playful insults are ENCOURAGED — this is a party game
- Rewrite (don't censor) anything that crosses into slurs, hate speech, or attacks on identity
- Keep it short — one punchy line
- If the original is fine, you can use it nearly verbatim with your own flair

Respond with ONLY a JSON object:
{{
  "heckle": "the host-delivered heckle line",
  "moderated": true or false
}}

Set moderated to true only if you had to meaningfully change the intent."""

    response = anthropic.messages.create(
        model=MODEL, max_tokens=256, messages=[{"role": "user", "content": prompt}]
    )
    return _parse_json(response.content[0].text)
