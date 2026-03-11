import streamlit as st
import os
from anthropic import Anthropic
from part_registry import load_registry, PART_TYPE_NAMES

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
# Mystery Generation — Registry-backed RAG
# -------------------------
def generate_mystery(user_prompt):
    """
    Sample compatible parts from the registry, then ask Claude to assemble
    them into a coherent mystery narrative. The parts act as structured
    constraints — Claude fleshes out the prose but cannot invent a different
    crime, motive, or red herring from scratch.
    """
    parts, recipe = registry.sample_for_generation(target_setting=user_prompt)

    # Build a structured part brief for Claude
    part_lines = []
    for part in parts:
        part_lines.append(f"- {part.part_type.replace('_', ' ').upper()} [{part.source_id}({part.part_index})]: {part.content}")
    parts_brief = "\n".join(part_lines)

    mystery_text = llm(f"""
You are generating a mystery scenario for a detective party game.

Player prompt: "{user_prompt}"

You have been given the following mystery components drawn from real published mystery fiction.
USE THESE COMPONENTS — do not invent replacements. Adapt them to fit the player's setting,
but preserve the essence of each element.

MYSTERY COMPONENTS:
{parts_brief}

Write the mystery as an engaging narrative the player reads at the start of the game.
Structure it as follows:

THE CRIME: What happened, how, and what question it poses.
THE VICTIM: Who they are and why they had enemies.
THE SETTING: The closed world — where this takes place and why no one can simply leave.
THE SUSPECTS: Introduce 3-4 suspects drawn from the components above. Make each memorable.
YOUR ROLE: Address the player directly — they are the investigator entering this scene.

Do NOT reveal the culprit. Plant the red herring naturally. Make the setting vivid.
""")

    return mystery_text, recipe


# -------------------------
# Suspect Extraction
# -------------------------
def extract_suspects(mystery):
    return llm(f"""
From this mystery, extract the list of suspects (exclude the victim and the detective/player).
Return ONLY their names, one per line, no bullets, numbers, or extra text.

Mystery:
{mystery}
""")

# -------------------------
# Solution Generation
# -------------------------
def generate_solution(mystery, user_prompt):
    return llm(f"""
Original prompt: {user_prompt}

Mystery:
{mystery}

Identify the following and return a structured solution:
- CULPRIT: Who did it, and their means, motive, and opportunity
- RED HERRINGS: Which clues or characters were planted to mislead
- ALIBI: What false alibi the culprit used
- REVEAL: What single piece of evidence definitively breaks the case

Be precise. This is the game engine's internal solution vault.
""", system="You are the mystery game engine's internal solution vault. Be precise and logical.")

# -------------------------
# Session State
# -------------------------
defaults = {
    "mystery": "",
    "suspects": [],
    "solution": "",
    "recipe": None,
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
        mystery_text, recipe = generate_mystery(user_prompt)
        st.session_state.mystery = mystery_text
        st.session_state.recipe = recipe.to_dict()

        suspects_raw = extract_suspects(mystery_text)
        st.session_state.suspects = [s.strip() for s in suspects_raw.split("\n") if s.strip()]

        solution = generate_solution(mystery_text, user_prompt)
        st.session_state.solution = solution

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

        # Provenance expander — shows which registry parts were used
        if st.session_state.recipe:
            with st.expander("Mystery DNA (part provenance)", expanded=False):
                st.caption(f"Recipe: `{st.session_state.recipe['recipe']}`")
                for slot in st.session_state.recipe["slots"]:
                    st.caption(
                        f"**{slot['part_type'].replace('_', ' ').title()}** — "
                        f"source `{slot['source_id']}`, part {slot['part_index']}"
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
                    with st.spinner(f"Interrogating {selected_suspect}..."):
                        reply = llm(f"""
You are {selected_suspect} in this mystery:

{st.session_state.mystery}

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
