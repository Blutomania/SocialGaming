import json
import streamlit as st
import os
from anthropic import Anthropic
from part_registry import load_registry, PART_TYPE_NAMES
from coherence_validator import check_mystery

# -------------------------
# Page Config
# -------------------------
st.set_page_config(
    page_title="Choose Your Mystery",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------
# Load API Key
# -------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    st.error("ANTHROPIC_API_KEY not found. Set it in your environment or Hugging Face Secrets.")
    st.stop()

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# -------------------------
# Load Part Registry (cached — loaded once per session)
# -------------------------
@st.cache_resource
def get_registry():
    return load_registry("./mystery_database")

registry = get_registry()

# -------------------------
# LLM Helper
# -------------------------
def llm(prompt, system="You are a creative mystery game engine. Never reveal the culprit unless explicitly asked in the solution phase."):
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {e}"

# -------------------------
# Mystery Generation — Registry-backed RAG → structured JSON
# -------------------------
def generate_mystery(user_prompt):
    """
    Sample compatible parts from the registry, then ask Claude to assemble
    them into a validated structured JSON mystery. Returns (mystery_dict, recipe).
    """
    parts, recipe = registry.sample_for_generation(target_setting=user_prompt)

    parts_block = "\n".join(
        f"  [{p.label()} — {p.part_type}]: {p.content}"
        for p in parts
    )

    prompt = f"""\
You are generating a mystery scenario for a social deduction game with 4 players.

SETTING: {user_prompt}

The following atomized parts have been selected from existing mystery literature
(recipe: {recipe.format()}). Adapt them to the target setting — do not copy verbatim.

SELECTED PARTS:
{parts_block}

QUALITY REQUIREMENTS — every generated mystery MUST satisfy these:

SETTING:
  - description must explicitly explain why suspects cannot simply leave (isolation mechanic).

CHARACTERS (include 1 victim, 3–4 suspects, optionally 1–2 witnesses):
  - alibi: SPECIFIC — state where the person was, with whom or doing what. Never "—" or vague.
  - secret: CONCRETE FACT (≥ 2 sentences) anchoring interrogation questions.
  - motive (suspects): specific stake — financial, relational, reputational, or political. Never "—".
  - occupation: always present; must logically place the character in the closed world.

EVIDENCE (include at least 6 items total):
  - At least 2 items with type "physical".
  - At least 1 item with relevance "red_herring" and type "physical" or "documentary".
  - At least 2 items with relevance "critical".
  - description: ≥ 2 sentences; state what the item is, where found, and what it suggests.

SOLUTION:
  - key_evidence must list at least 2 evidence IDs.
  - how_to_deduce: step-by-step logic chain (3+ steps).

Generate a complete mystery JSON with this exact structure:
{{
  "title": "string",
  "setting": {{
    "location": "string",
    "time_period": "string",
    "environment": "string",
    "description": "2–3 sentence atmospheric description including why suspects cannot leave"
  }},
  "crime": {{
    "type": "string",
    "what_happened": "string",
    "when": "string",
    "initial_discovery": "string"
  }},
  "characters": [
    {{
      "name": "string",
      "role": "victim | suspect | detective | witness",
      "occupation": "string",
      "motive": "string",
      "alibi": "string",
      "secret": "string"
    }}
  ],
  "evidence": [
    {{
      "id": "E1",
      "name": "string",
      "description": "string",
      "type": "physical | testimonial | circumstantial | documentary",
      "relevance": "critical | supporting | red_herring"
    }}
  ],
  "solution": {{
    "culprit": "string",
    "method": "string",
    "motive": "string",
    "key_evidence": ["E1", "E2"],
    "how_to_deduce": "step-by-step reasoning"
  }},
  "gameplay_notes": {{
    "difficulty": "EASY | MEDIUM | HARD",
    "estimated_playtime": "string",
    "key_twists": ["string"]
  }}
}}

Return only valid JSON. No commentary outside the JSON block."""

    raw = llm(prompt, system="You are a mystery game engine. Return only valid JSON.")
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    mystery_dict = json.loads(raw)
    mystery_dict["_provenance"] = recipe.to_dict()
    return mystery_dict, recipe


def localize_mystery(mystery_dict: dict) -> dict:
    """
    Post-generation localization pass — one Claude call.
    Rewrites all character names, occupations, titles, and embedded
    dialogue/text so they fit the setting's time period and culture.
    Preserves the full JSON structure; only surface text changes.
    Licensed to be playful: a Roman witness can be WhatICius, etc.
    """
    s = mystery_dict.get("setting", {})
    location = s.get("location", "")
    time_period = s.get("time_period", "")

    prompt = f"""\
You are localizing a mystery game script for historical/cultural authenticity and fun.

SETTING: {location} — {time_period}

The mystery was generated with placeholder names that may be anachronistic
(e.g. "Dr. Pemberton" in Ancient Rome, "CEO Marcus Webb" in 1520 Istanbul).
Your job: rewrite EVERY name, title, occupation, and any dialogue or embedded
text so they belong to this time and place.

Rules:
1. Names must fit the culture and era. No modern surnames in ancient settings.
   Ancient Rome: Gaius, Livia, Marcus Flavius. Ottoman: Mehmed, Fatima, Yusuf.
   Harlem 1920s: Josephine, Duke, Red. Antarctic now: Dr. Chen is fine.
2. Occupations must have period-appropriate equivalents.
   "Doctor" → "Physician" or "Surgeon" in Victorian; "Healer" or "Physician" in Ancient.
   "Lawyer" → "Advocate" in Roman; "Kadi" in Ottoman.
   "CEO" → "Merchant Prince", "Guild Master", "Trading House Head".
3. Titles and honorifics must match the era.
   No "Mr.", "Ms.", "Dr." in ancient or medieval settings.
   Use "Senator", "Tribune", "Archon", "Bey", "Effendi", "Lord", "Lady" as appropriate.
4. You MAY (encouraged!) create playful period-appropriate puns for minor characters.
   A Roman witness called "I Saw Everything" could become "Vidiomnius".
   A gossipy Harlem bystander could be "Tells-It-All Thomas".
   Don't overdo it — one or two playful names per mystery, for witnesses/minor suspects.
5. Update ALL text fields where names or titles appear: secrets, alibis, motives,
   evidence descriptions, crime description, solution. Be thorough — a name left
   unchanged in one field breaks immersion.
6. Do NOT change the mystery structure, plot, culprit, or evidence. Only surface text.
7. Update the title if it contains a modern-sounding name.

Return the COMPLETE mystery JSON with localizations applied. Same structure, same keys.
Return only valid JSON. No commentary.

MYSTERY TO LOCALIZE:
{json.dumps(mystery_dict, indent=2)}"""

    raw = llm(prompt, system="You are a historical authenticity editor. Return only valid JSON.")
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    localized = json.loads(raw)
    # Preserve internal fields that Claude shouldn't touch
    for key in ("_provenance", "_coherence", "_meta", "cinematic_brief"):
        if key in mystery_dict:
            localized[key] = mystery_dict[key]
    return localized


def generate_cinematic_brief(mystery_dict: dict) -> dict:
    """
    One extra LLM call — converts a structured mystery dict into a
    video-generation-optimized brief. Returns a cinematic_brief dict.
    Only called when the user explicitly enables it.
    """
    m = mystery_dict
    s = m.get("setting", {})
    c = m.get("crime", {})
    chars = m.get("characters", [])
    suspects = [ch for ch in chars if ch.get("role") == "suspect"]
    cast_lines = "\n".join(
        f"  - {ch['name']} ({ch.get('occupation', '')}): {ch.get('secret', '')[:80]}"
        for ch in suspects
    )

    prompt = f"""\
You are writing a cinematic brief for an AI video generator (e.g. Sora, Runway Gen-3).
The brief will become the opening sequence of a mystery party game — 15–30 seconds,
no spoilers, pure visual and atmospheric hook.

MYSTERY TITLE: {m.get('title', '')}
SETTING: {s.get('location', '')} — {s.get('time_period', '')}
ATMOSPHERE: {s.get('description', '')}
CRIME: {c.get('what_happened', '')}
DISCOVERED BY: {c.get('initial_discovery', '')}
SUSPECTS (do NOT show guilt or motive — only appearance and first moment):
{cast_lines}

Return ONLY valid JSON in this exact structure:
{{
  "logline": "One sentence. Visual, urgent, present tense. Under 20 words.",
  "opening_shot": "Establishing shot description — lens, light, movement, no dialogue. 2–3 sentences.",
  "crime_reveal_shot": "The moment the crime is discovered — camera angle, reaction, sound. 2–3 sentences.",
  "atmosphere_tags": ["3–6 single words or short phrases: mood, texture, colour palette"],
  "sound_design": "What the audience hears before any dialogue. One sentence.",
  "cast_visuals": [
    {{
      "name": "character name",
      "appearance": "Clothing, posture, distinguishing detail. One sentence.",
      "first_seen_doing": "Their first on-screen action. One sentence."
    }}
  ],
  "title_card": "The text overlay that ends the opening sequence. Short, evocative."
}}

Return only valid JSON. No commentary."""

    raw = llm(prompt, system="You are a cinematic brief writer for AI video generation. Return only valid JSON.")
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)


def _mystery_to_markdown(m: dict) -> str:
    """Convert a structured mystery dict to a readable narrative for display."""
    s = m.get("setting", {})
    c = m.get("crime", {})
    chars = m.get("characters", [])
    victim = next((ch for ch in chars if ch.get("role") == "victim"), None)
    suspects = [ch for ch in chars if ch.get("role") == "suspect"]

    lines = [
        f"## {m.get('title', 'Untitled Mystery')}",
        "",
        f"**{s.get('location', '')}** — *{s.get('time_period', '')}*",
        "",
        s.get("description", ""),
        "",
        "### The Crime",
        c.get("what_happened", ""),
        f"*Discovered: {c.get('initial_discovery', '')}*",
        "",
    ]
    if victim:
        lines += [
            "### The Victim",
            f"**{victim['name']}** — {victim.get('occupation', '')}",
            "",
        ]
    if suspects:
        lines.append("### The Suspects")
        for su in suspects:
            lines.append(f"**{su['name']}** — {su.get('occupation', '')}")
        lines.append("")
    lines.append("### Your Role")
    lines.append("You are the investigator. Question the suspects. Examine the evidence. Find the truth.")
    return "\n".join(lines)

# -------------------------
# Session State
# -------------------------
defaults = {
    "mystery": "",        # markdown narrative for display
    "mystery_dict": None, # full structured dict
    "suspects": [],
    "solution": "",
    "recipe": None,
    "coherence": None,         # {"passed": bool, "blocking": int, "warnings": int}
    "cinematic_brief": None,   # video-gen optimized brief (opt-in)
    "generated": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------
# Header
# -------------------------
st.title("Choose Your Mystery")
st.caption("An AI-powered detective game. Set the scene. Interrogate the suspects. Solve the case.")
st.divider()

# -------------------------
# Mystery Prompt Input
# -------------------------
st.subheader("Set Your Mystery")
user_prompt = st.text_input(
    "Describe your scenario:",
    placeholder='e.g. "A murder on a Mars colony" or "An art theft in Renaissance Venice"',
)
cinematic_on = st.checkbox(
    "Generate cinematic brief (video prompt)",
    value=False,
    help="Adds one extra AI call to produce a shot-list and visual brief for video generation. Off by default.",
)

if st.button("Generate Mystery", disabled=not user_prompt.strip()):
    with st.spinner("Building your case from the archives..."):
        mystery_dict, recipe = generate_mystery(user_prompt)
        with st.spinner("Localizing names and occupations to setting..."):
            mystery_dict = localize_mystery(mystery_dict)
        st.session_state.mystery_dict = mystery_dict
        st.session_state.mystery = _mystery_to_markdown(mystery_dict)
        st.session_state.recipe = recipe.to_dict()

        # Extract suspects directly from structured characters — no extra LLM call
        chars = mystery_dict.get("characters", [])
        st.session_state.suspects = [
            ch["name"] for ch in chars if ch.get("role") == "suspect"
        ]

        # Solution is already embedded in the dict — no extra LLM call
        sol = mystery_dict.get("solution", {})
        st.session_state.solution = (
            f"CULPRIT: {sol.get('culprit', '?')}\n"
            f"METHOD: {sol.get('method', '?')}\n"
            f"MOTIVE: {sol.get('motive', '?')}\n"
            f"KEY EVIDENCE: {', '.join(sol.get('key_evidence', []))}\n"
            f"HOW TO DEDUCE: {sol.get('how_to_deduce', '?')}"
        )

        # Coherence check
        report = check_mystery(mystery_dict)
        st.session_state.coherence = {
            "passed": report.passed,
            "blocking": report.blocking_count,
            "warnings": report.warning_count,
        }

        # Cinematic brief — opt-in only
        if cinematic_on:
            brief = generate_cinematic_brief(mystery_dict)
            mystery_dict["cinematic_brief"] = brief
            st.session_state.cinematic_brief = brief
        else:
            st.session_state.cinematic_brief = None

        st.session_state.generated = True

st.divider()

# -------------------------
# Main Game Area
# -------------------------
if st.session_state.generated:

    left_col, right_col = st.columns([2, 1])

    # -------------------------
    # Left: The Case
    # -------------------------
    with left_col:
        st.subheader("The Case")
        st.markdown(st.session_state.mystery)

        # Coherence badge
        coh = st.session_state.coherence
        if coh:
            if coh["passed"]:
                st.success(
                    f"Coherence: PASS — {coh['blocking']} blocking, {coh['warnings']} warnings",
                    icon="✅",
                )
            else:
                st.error(
                    f"Coherence: FAIL — {coh['blocking']} blocking issue(s), {coh['warnings']} warnings. "
                    "This mystery may have logical gaps.",
                    icon="⚠️",
                )

        # Provenance expander — shows which registry parts were used
        if st.session_state.recipe:
            with st.expander("Mystery DNA (part provenance)", expanded=False):
                st.caption(f"Recipe: `{st.session_state.recipe['recipe']}`")
                for slot in st.session_state.recipe["slots"]:
                    st.caption(
                        f"**{slot['part_type'].replace('_', ' ').title()}** — "
                        f"source `{slot['source_id']}`, part {slot['part_index']}"
                    )

        # Cinematic brief expander — only shown when opted in
        brief = st.session_state.cinematic_brief
        if brief:
            with st.expander("Cinematic Brief (video prompt)", expanded=True):
                st.markdown(f"**Logline:** {brief.get('logline', '')}")
                st.divider()
                st.markdown(f"**Opening shot**\n\n{brief.get('opening_shot', '')}")
                st.markdown(f"**Crime reveal**\n\n{brief.get('crime_reveal_shot', '')}")
                tags = brief.get("atmosphere_tags", [])
                if tags:
                    st.markdown("**Atmosphere:** " + " · ".join(f"`{t}`" for t in tags))
                st.markdown(f"**Sound design:** {brief.get('sound_design', '')}")
                cast = brief.get("cast_visuals", [])
                if cast:
                    st.markdown("**Cast visuals**")
                    for ch in cast:
                        st.markdown(
                            f"- **{ch.get('name', '')}** — {ch.get('appearance', '')} "
                            f"*First seen: {ch.get('first_seen_doing', '')}*"
                        )
                st.markdown(f"**Title card:** _{brief.get('title_card', '')}_")

    # -------------------------
    # Right: Suspects + Interrogation + Coming Soon
    # -------------------------
    with right_col:
        st.subheader("Suspects")

        if st.session_state.suspects:
            selected_suspect = st.selectbox("Select a suspect to interrogate:", st.session_state.suspects)
            question = st.text_input("Your question:")

            if st.button("Interrogate"):
                if question.strip():
                    with st.spinner(f"Interrogating {selected_suspect}..."):
                        # Pull this character's details for richer in-character replies
                        chars = (st.session_state.mystery_dict or {}).get("characters", [])
                        char_data = next((c for c in chars if c["name"] == selected_suspect), {})
                        char_context = (
                            f"Role: {char_data.get('role', 'suspect')}\n"
                            f"Occupation: {char_data.get('occupation', '')}\n"
                            f"Alibi: {char_data.get('alibi', '')}\n"
                            f"Secret: {char_data.get('secret', '')}\n"
                            f"Motive: {char_data.get('motive', '')}"
                        ) if char_data else ""
                        reply = llm(f"""
You are {selected_suspect} in this mystery:

{st.session_state.mystery}

Your private character details (do NOT reveal these directly):
{char_context}

Answer the detective's question in character.
Be evasive if you are the culprit. Be defensive if you are innocent but suspicious.
Do NOT directly reveal the real culprit.

Detective's question: {question}
""")
                        st.success(reply)
                else:
                    st.warning("Type a question first.")

        st.divider()

        # Coming Soon box
        st.markdown("""
<div style='background-color:#1a1a2e; padding:16px; border-radius:10px; border:1px solid #3a3a5c;'>
  <p style='color:#f0a500; font-weight:bold; margin-bottom:10px;'>Coming Soon</p>
  <p style='color:#cccccc; margin:4px 0;'>🎬 &nbsp;Generative AI depiction scenes</p>
  <p style='color:#cccccc; margin:4px 0;'>👥 &nbsp;Multiplayer</p>
  <p style='color:#cccccc; margin:4px 0;'>🔗 &nbsp;Clue sharing</p>
  <p style='color:#cccccc; margin:4px 0;'>🧬 &nbsp;Gen AI avatars</p>
</div>
""", unsafe_allow_html=True)

    # -------------------------
    # Final Accusation
    # -------------------------
    st.divider()
    st.subheader("Make Your Accusation")

    guess = st.selectbox("Who is the culprit?", ["Select a suspect"] + st.session_state.suspects)

    if st.button("Submit Final Answer"):
        if guess == "Select a suspect":
            st.warning("Select a suspect before submitting.")
        else:
            with st.spinner("Evaluating your accusation..."):
                verdict = llm(f"""
Mystery:
{st.session_state.mystery}

Player accused: {guess}

Actual solution:
{st.session_state.solution}

Tell the player dramatically whether they are right or wrong.
If wrong: reveal the real culprit with a full logical walkthrough of the evidence trail.
If right: congratulate them and walk through the deduction path that proves it.
""")
                st.subheader("Case Closed")
                st.write(verdict)

else:
    st.info("Enter a mystery prompt above to begin your investigation.")

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption("Powered by Claude AI · mysteries sourced from the archive")
