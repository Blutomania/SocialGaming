import json
import re
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
def llm(prompt, system="You are a creative mystery game engine. Never reveal the culprit unless explicitly asked in the solution phase.", max_tokens=1500):
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {e}"


def _parse_json(text: str) -> dict:
    """Extract and parse the first JSON block from a Claude response."""
    # Strip markdown code fences if present
    clean = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Fall back: find first { ... } block
        match = re.search(r"\{[\s\S]*\}", clean)
        if match:
            return json.loads(match.group())
        raise


# -------------------------
# Mystery Generation — Registry-backed RAG with coherence validation
# -------------------------
def generate_mystery(user_prompt):
    """
    Sample compatible parts from the registry, generate a structured mystery JSON,
    validate it with check_mystery, and return (mystery_dict, recipe, coherence_report).
    """
    parts, recipe = registry.sample_for_generation(target_setting=user_prompt)

    parts_block = "\n".join(
        f"  [{p.label()} — {p.part_type}]: {p.content}"
        for p in parts
    )

    json_text = llm(f"""
You are generating a mystery scenario for a social deduction party game.

Player prompt: "{user_prompt}"

The following atomized parts have been selected from real published mystery fiction via
part-tracked RAG (recipe: {recipe.format()}). Adapt them to the target setting — do not
copy them verbatim.

SELECTED PARTS:
{parts_block}

QUALITY REQUIREMENTS — every generated mystery MUST satisfy these:

SETTING:
  - description must explicitly explain why suspects cannot simply leave (isolation mechanic).

CHARACTERS (include 1 victim, 3–4 suspects, optionally 1–2 witnesses):
  - alibi: SPECIFIC — state where the person was, with whom or doing what. Never "—" or vague.
    Good: "Was supervising the night shift in the boiler room with two apprentices until dawn."
    Bad: "Was elsewhere." or "—"
  - secret: CONCRETE FACT (≥ 2 sentences) anchoring why-were-you-there interrogation questions.
    Good: "Had borrowed money from the victim six months ago and had not repaid it; was seen
           arguing with them the evening before in the garden."
    Bad: "Has a dark past."
  - motive (suspects): specific stake — financial, relational, reputational, or political.
    Never "—" for suspects.
  - occupation: always present; must logically place the character in the closed world.

EVIDENCE (include at least 6 items total):
  - At least 2 items with type "physical".
  - At least 1 item with relevance "red_herring" and type "physical" or "documentary".
  - At least 2 items with relevance "critical".
  - description: ≥ 2 sentences (what the item is, where found, what it suggests).

SOLUTION:
  - key_evidence must list at least 2 evidence IDs that together prove the culprit's guilt.
  - how_to_deduce: step-by-step logic chain (3+ steps), not a single sentence.

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

Return only valid JSON. No commentary outside the JSON block.
""", max_tokens=4096)

    mystery = _parse_json(json_text)
    report = check_mystery(mystery)
    return mystery, recipe, report


def _render_mystery_narrative(mystery: dict) -> str:
    """Format a mystery dict as a readable narrative for display."""
    s = mystery.get("setting", {})
    c = mystery.get("crime", {})
    lines = []
    lines.append(f"### {mystery.get('title', 'Untitled Mystery')}\n")
    lines.append(f"**{s.get('location', '')}** · {s.get('time_period', '')}")
    lines.append(f"\n{s.get('description', '')}\n")
    lines.append(f"**THE CRIME:** {c.get('what_happened', '')} {c.get('initial_discovery', '')}\n")

    suspects = [ch for ch in mystery.get("characters", []) if ch.get("role") == "suspect"]
    victim = next((ch for ch in mystery.get("characters", []) if ch.get("role") == "victim"), None)
    if victim:
        lines.append(f"**THE VICTIM:** {victim['name']} — {victim.get('occupation', '')}\n")
    if suspects:
        lines.append("**THE SUSPECTS:**")
        for s in suspects:
            lines.append(f"- **{s['name']}** ({s.get('occupation', '')}) — {s.get('motive', 'motive unknown')}")

    lines.append("\n*You are the investigator. Interrogate the suspects. Find the truth.*")
    return "\n".join(lines)


# -------------------------
# Solution Generation
# -------------------------
def generate_solution(mystery: dict, user_prompt: str) -> str:
    sol = mystery.get("solution", {})
    if sol.get("culprit"):
        # Solution is already in the structured mystery; format it for display
        return (
            f"**CULPRIT:** {sol.get('culprit')}\n\n"
            f"**METHOD:** {sol.get('method')}\n\n"
            f"**MOTIVE:** {sol.get('motive')}\n\n"
            f"**KEY EVIDENCE:** {', '.join(sol.get('key_evidence', []))}\n\n"
            f"**HOW TO DEDUCE:** {sol.get('how_to_deduce')}"
        )
    # Fallback: ask Claude if solution section is empty
    return llm(f"""
Original prompt: {user_prompt}

Mystery title: {mystery.get('title')}
Characters: {json.dumps(mystery.get('characters', []), indent=2)}
Evidence: {json.dumps(mystery.get('evidence', []), indent=2)}

Identify the culprit and explain the solution with:
- CULPRIT, METHOD, MOTIVE, KEY EVIDENCE, REVEAL

Be precise. This is the game engine's internal solution vault.
""", system="You are the mystery game engine's internal solution vault. Be precise and logical.")


# -------------------------
# Session State
# -------------------------
defaults = {
    "mystery": None,       # dict
    "suspects": [],
    "solution": "",
    "recipe": None,
    "coherence": None,     # {"passed": bool, "blocking": int, "warnings": int}
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

if st.button("Generate Mystery", disabled=not user_prompt.strip()):
    with st.spinner("Building your case from the archives..."):
        try:
            mystery, recipe, report = generate_mystery(user_prompt)

            st.session_state.mystery = mystery
            st.session_state.recipe = recipe.to_dict()
            st.session_state.suspects = [
                c["name"] for c in mystery.get("characters", [])
                if c.get("role") == "suspect"
            ]
            st.session_state.solution = generate_solution(mystery, user_prompt)
            st.session_state.coherence = {
                "passed": report.passed,
                "blocking": report.blocking_count,
                "warnings": report.warning_count,
            }
            st.session_state.generated = True

            if not report.passed:
                st.warning(
                    f"⚠️ This mystery has {report.blocking_count} blocking coherence issue(s) "
                    f"and may have gaps in its logic. It has been flagged for review."
                )
        except Exception as e:
            st.error(f"Generation failed: {e}")

st.divider()

# -------------------------
# Main Game Area
# -------------------------
if st.session_state.generated and st.session_state.mystery:

    left_col, right_col = st.columns([2, 1])

    # -------------------------
    # Left: The Case
    # -------------------------
    with left_col:
        st.subheader("The Case")
        st.markdown(_render_mystery_narrative(st.session_state.mystery))

        # Provenance + coherence expander
        if st.session_state.recipe:
            coh = st.session_state.coherence or {}
            coh_label = "✅ Validated" if coh.get("passed") else f"⚠️ {coh.get('blocking', 0)} blocking issues"
            with st.expander(f"Mystery DNA · {coh_label}", expanded=False):
                st.caption(f"Recipe: `{st.session_state.recipe['recipe']}`")
                for slot in st.session_state.recipe["slots"]:
                    st.caption(
                        f"**{slot['part_type'].replace('_', ' ').title()}** — "
                        f"source `{slot['source_id']}`, part {slot['part_index']}"
                    )
                if coh:
                    st.caption(
                        f"Coherence: {'✅ passed' if coh.get('passed') else '❌ failed'} · "
                        f"{coh.get('blocking', 0)} blocking · {coh.get('warnings', 0)} warnings"
                    )

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
                    mystery_summary = _render_mystery_narrative(st.session_state.mystery)
                    with st.spinner(f"Interrogating {selected_suspect}..."):
                        # Find this character's secret for richer in-character responses
                        char = next(
                            (c for c in st.session_state.mystery.get("characters", [])
                             if c["name"] == selected_suspect),
                            {}
                        )
                        secret_hint = f"(Your secret: {char.get('secret', '')})" if char.get("secret") else ""
                        reply = llm(f"""
You are {selected_suspect} in this mystery. {secret_hint}

Mystery context:
{mystery_summary}

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
            sol = st.session_state.mystery.get("solution", {})
            actual_culprit = sol.get("culprit", "")
            correct = guess.lower() in actual_culprit.lower() or actual_culprit.lower() in guess.lower()

            with st.spinner("Evaluating your accusation..."):
                verdict = llm(f"""
Mystery title: {st.session_state.mystery.get('title')}

Player accused: {guess}
Actual culprit: {actual_culprit}
Solution: {st.session_state.solution}

{"The player is CORRECT." if correct else "The player is WRONG."}

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
