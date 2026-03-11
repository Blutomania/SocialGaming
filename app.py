import streamlit as st
import os
from anthropic import Anthropic

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
# Mystery Generation — P1 Skeleton Protocol
# -------------------------
def generate_mystery(user_prompt):
    return llm(f"""
You are generating a mystery scenario for a detective party game.

Player prompt: "{user_prompt}"

Generate the mystery using this structure:

C1 - THE CRIME: Describe the crime, its method, and the central question it poses.
C2 - THE VICTIM: Who are they and what made them a target? Establish why this person had enemies.
C3 - THE CLOSED WORLD: Define the bounded setting and introduce the circle of 3-4 suspects.
C5 - THE INVESTIGATION PATH: Plant 2-3 visible clues and at least one red herring.
C6 - THE DETECTIVE ROLE: Address the player directly — they are the investigator entering this scene.

Write this as an engaging narrative the player reads at the start of the game.
Do NOT reveal the culprit. Make the setting vivid and the suspects memorable.
""")

# -------------------------
# Suspect Extraction — P2 Architecture Protocol (M1)
# -------------------------
def extract_suspects(mystery):
    return llm(f"""
From this mystery, extract the list of suspects (exclude the victim and the detective/player).
Return ONLY their names, one per line, no bullets, numbers, or extra text.

Mystery:
{mystery}
""")

# -------------------------
# Solution Generation — P2 Architecture Protocol (M1, M2, M5, M6)
# -------------------------
def generate_solution(mystery, user_prompt):
    return llm(f"""
Original prompt: {user_prompt}

Mystery:
{mystery}

Identify the following and return a structured solution:
- M1 (Culprit): Who did it, and their means, motive, and opportunity
- M2 (Red Herrings): Which clues or characters were planted to mislead
- M5 (Alibi): What false alibi the culprit used
- M6 (Reveal): What single piece of evidence definitively breaks the case

Be precise. This is the game engine's internal solution vault.
""", system="You are the mystery game engine's internal solution vault. Be precise and logical.")

# -------------------------
# Session State
# -------------------------
defaults = {
    "mystery": "",
    "suspects": [],
    "solution": "",
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
    with st.spinner("Building your case..."):
        story = generate_mystery(user_prompt)
        st.session_state.mystery = story

        suspects_raw = extract_suspects(story)
        st.session_state.suspects = [s.strip() for s in suspects_raw.split("\n") if s.strip()]

        solution = generate_solution(story, user_prompt)
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
st.caption("Powered by Claude AI (Anthropic)")
