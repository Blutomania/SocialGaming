import csv
import io
import json
import streamlit as st
import os
from datetime import datetime, timezone
from anthropic import Anthropic
from part_registry import load_registry, PART_TYPE_NAMES
from coherence_validator import check_mystery
from localization import localize_mystery as _localize_mystery, cache_stats as _loc_cache_stats

MYSTERY_STOCK_MAX = 10
DOWNLOAD_TRIGGER = "peter parker"

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
    """Thin wrapper — delegates to localization.py with the app's llm function."""
    return _localize_mystery(mystery_dict, llm)


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
    witnesses = [ch for ch in chars if ch.get("role") == "witness"]

    lines = [
        f"## {m.get('title', 'Untitled Mystery')}",
        "",
        f"**{s.get('location', '')}** — *{s.get('time_period', '')}*",
        "",
        s.get("description", ""),
        "",
        "### The Crime",
        c.get("what_happened", ""),
        f"*When: {c.get('when', '—')}*",
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
    if witnesses:
        lines.append("### Witnesses")
        for w in witnesses:
            lines.append(f"**{w['name']}** — {w.get('occupation', '')}")
        lines.append("")
    lines.append("### Your Role")
    lines.append("You are the investigator. Question the suspects. Examine the evidence. Find the truth.")
    return "\n".join(lines)

# -------------------------
# Stock helpers
# -------------------------
def _add_to_stock(mystery_dict: dict, prompt: str, coherence: dict, viability: int = 5):
    """Append a mystery to the session stock (max MYSTERY_STOCK_MAX, rolling)."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "mystery_dict": mystery_dict,
        "coherence": coherence,
        "viability_rating": viability,
    }
    stock = st.session_state.mystery_stock
    stock.append(entry)
    if len(stock) > MYSTERY_STOCK_MAX:
        stock.pop(0)


def _stock_to_json_bytes() -> bytes:
    """Serialise the full stock to a pretty-printed JSON byte string."""
    return json.dumps(st.session_state.mystery_stock, indent=2).encode("utf-8")


def _stock_to_csv_bytes() -> bytes:
    """Serialise the stock to a flat CSV byte string."""
    rows = []
    for entry in st.session_state.mystery_stock:
        m = entry.get("mystery_dict", {})
        sol = m.get("solution", {})
        coh = entry.get("coherence", {})
        notes = m.get("gameplay_notes", {})
        suspects = [c for c in m.get("characters", []) if c.get("role") == "suspect"]
        rows.append({
            "timestamp":          entry.get("timestamp", ""),
            "prompt":             entry.get("prompt", ""),
            "title":              m.get("title", ""),
            "location":           m.get("setting", {}).get("location", ""),
            "time_period":        m.get("setting", {}).get("time_period", ""),
            "difficulty":         notes.get("difficulty", ""),
            "estimated_playtime": notes.get("estimated_playtime", ""),
            "culprit":            sol.get("culprit", ""),
            "method":             sol.get("method", ""),
            "motive":             sol.get("motive", ""),
            "key_evidence":       ", ".join(sol.get("key_evidence", [])),
            "coherence_passed":   coh.get("passed", ""),
            "coherence_blocking": coh.get("blocking", ""),
            "coherence_warnings": coh.get("warnings", ""),
            "viability_rating":   entry.get("viability_rating", ""),
            "num_suspects":       len(suspects),
            "num_evidence":       len(m.get("evidence", [])),
        })
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _render_download_buttons(label_prefix: str = ""):
    """Render JSON + CSV download buttons for the current stock."""
    stock = st.session_state.mystery_stock
    if not stock:
        st.info("No mysteries in stock yet — generate one first.")
        return
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label=f"{label_prefix}Download JSON ({len(stock)} mysteries)",
            data=_stock_to_json_bytes(),
            file_name="mystery_stock.json",
            mime="application/json",
        )
    with col2:
        st.download_button(
            label=f"{label_prefix}Download CSV ({len(stock)} mysteries)",
            data=_stock_to_csv_bytes(),
            file_name="mystery_stock.csv",
            mime="text/csv",
        )


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
    "viability_rating": 5,     # creator-side 1–10 viability rating
    "generated": False,
    "mystery_stock": [],       # rolling stock of up to MYSTERY_STOCK_MAX mysteries
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------
# Header
# -------------------------
st.title("Choose Your Mystery")
st.caption("Ultimately: An AI-powered detective game. Set the scene. Interrogate the suspects. Solve the case.")
st.caption("Currently: An AI-powered mystery creator. Set the scene. Verify the output")
st.divider()

# -------------------------
# Mystery Stock Status Bar
# -------------------------
stock_count = len(st.session_state.mystery_stock)
with st.expander(
    f"Mystery Stock — {stock_count}/{MYSTERY_STOCK_MAX} saved"
    + (" · type \"Peter Parker\" to download" if stock_count > 0 else ""),
    expanded=False,
):
    if stock_count:
        for i, entry in enumerate(reversed(st.session_state.mystery_stock), 1):
            m = entry.get("mystery_dict", {})
            coh = entry.get("coherence", {})
            coh_badge = "✅" if coh.get("passed") else "⚠️"
            st.caption(
                f"{i}. **{m.get('title', 'Untitled')}** — "
                f"viability {entry.get('viability_rating', '?')}/10 · "
                f"{coh_badge} coherence · "
                f"_{entry.get('prompt', '')}_ · "
                f"{entry.get('timestamp', '')[:10]}"
            )
        st.divider()
        _render_download_buttons()
    else:
        st.caption("No mysteries yet. Generate one to start building your stock.")

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

_is_download_trigger = user_prompt.strip().lower() == DOWNLOAD_TRIGGER

if _is_download_trigger:
    st.info("🕷️ **Download mode activated.** Your mystery stock is ready to export.")
    _render_download_buttons()
elif st.button("Generate Mystery", disabled=not user_prompt.strip()):
    with st.spinner("Building your case from the archives..."):
        mystery_dict, recipe = generate_mystery(user_prompt)
        from localization import _is_modern, _era_key, _load_era_rules
        _setting = mystery_dict.get("setting", {})
        if _is_modern(_setting):
            loc_label = "Localization: modern setting — skipped"
        elif _load_era_rules(_era_key(_setting)):
            loc_label = "Localizing names (era rules cached)..."
        else:
            loc_label = "Localizing names and occupations (building era cache)..."
        with st.spinner(loc_label):
            mystery_dict = localize_mystery(mystery_dict)
        st.session_state.mystery_dict = mystery_dict
        st.session_state.mystery = _mystery_to_markdown(mystery_dict)
        st.session_state.recipe = recipe.to_dict()

        # Extract interrogatable characters (suspects + witnesses) — no extra LLM call
        chars = mystery_dict.get("characters", [])
        st.session_state.suspects = [
            ch["name"] for ch in chars if ch.get("role") in ("suspect", "witness")
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

        # Add to rolling stock (viability defaults to 5 at generation time)
        _add_to_stock(
            mystery_dict,
            prompt=user_prompt,
            coherence=st.session_state.coherence,
            viability=5,
        )

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

        # Evidence section
        md = st.session_state.mystery_dict
        ev = md.get("evidence", []) if md else []
        if ev:
            relevance_tag = {
                "critical":    "★ Critical",
                "red_herring": "✗ Red herring",
                "supporting":  "· Supporting",
            }
            with st.expander(f"Evidence — {len(ev)} items", expanded=True):
                for e in ev:
                    tag = relevance_tag.get(e.get("relevance", ""), e.get("relevance", ""))
                    st.markdown(
                        f"**[{e.get('id','?')}] {e.get('name','?')}** "
                        f"&nbsp;`{e.get('type','')}`&nbsp; · {tag}"
                    )
                    st.caption(e.get("description", ""))

        # Gameplay notes
        notes = (md or {}).get("gameplay_notes", {})
        if notes:
            diff = notes.get("difficulty", "?")
            playtime = notes.get("estimated_playtime", "?")
            twists = notes.get("key_twists", [])
            st.markdown(f"**Difficulty:** {diff} &nbsp;·&nbsp; **Estimated playtime:** {playtime}")
            if twists:
                st.markdown("**Key twists:** " + " · ".join(twists))

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
            selected_suspect = st.selectbox("Select a character to interrogate:", st.session_state.suspects)
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
    # Mystery Viability Rating
    # -------------------------
    st.divider()
    st.subheader("Rate This Mystery")
    st.caption("As the creator / reviewer — how viable is this mystery for actual play?")
    viability = st.radio(
        "Viability (1 = unplayable, 10 = ready to play):",
        options=list(range(1, 11)),
        horizontal=True,
        index=4,  # default: 5
        key="viability_rating",
    )
    rating_labels = {
        1: "Incoherent — do not use",
        2: "Major logical gaps",
        3: "Needs significant rework",
        4: "Playable with heavy GM prep",
        5: "Workable with some prep",
        6: "Good with minor tweaks",
        7: "Solid — minor polish only",
        8: "Strong — nearly ready",
        9: "Excellent — use as-is",
        10: "Perfect — publish it",
    }
    st.caption(f"_{rating_labels.get(viability, '')}_")

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
