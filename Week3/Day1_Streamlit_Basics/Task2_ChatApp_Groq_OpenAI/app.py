import os
import time
import base64
from pathlib import Path
from textwrap import dedent

import streamlit as st
from oracle import ask_oracle
from tarot import draw_tarot_card


# ---------------------------
# Streamlit Config
# ---------------------------
st.set_page_config(page_title="🔮 Mystic Oracle Chat", page_icon="🔮", layout="wide")


# ---------------------------
# Load external CSS (styles.css)
# ---------------------------
def load_css(path: str):
    css = Path(path).read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css("styles.css")  # keep all styling in styles.css only
# st.caption("🌌 Mystic Oracle ready.")


# ---------------------------
# Header
# ---------------------------
st.markdown("<h1>🔮 Mystic Oracle Chat 🔮</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; color:#d9b3ff;'>Converse with the Oracle... your fate unfolds 🌌</p>",
    unsafe_allow_html=True,
)


# ---------------------------
# Session State
# ---------------------------
if "history" not in st.session_state:
    # list of dicts: {"role": "user"/"oracle"/"tarot", "content": ...}
    st.session_state.history = []
if "tarot_archive" not in st.session_state:
    # flat list of drawn cards (dicts) for sidebar archive
    st.session_state.tarot_archive = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


# ---------------------------
# Sidebar — Spread mode, samples, archive, clear
# ---------------------------
spread_mode = st.sidebar.radio(
    "Choose Spread 🌌",
    ["Single Card", "3-Card Spread"],
    index=0,
)

st.sidebar.markdown("<h2 style='color:#e0b3ff;'>🌙 Ask the Oracle</h2>", unsafe_allow_html=True)
sample_questions = [
    "What awaits me in love?",
    "Will fortune favor me soon?",
    "Am I on the right path in life?",
]
for q in sample_questions:
    if st.sidebar.button(q, key=f"sample-{q}"):
        st.session_state.pending_question = q

# Sidebar — Oracle’s Archive (last 2 mini-cards, thumbnail + name only)
st.sidebar.markdown("<h2 style='color:#e0b3ff;'>📜 Oracle's Archive</h2>", unsafe_allow_html=True)
if st.session_state.tarot_archive:
    recent_cards = st.session_state.tarot_archive[-2:][::-1]  # newest first
    for card in recent_cards:
        tarot_path = os.path.join("images", "tarot", card["image"])
        try:
            with open(tarot_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            html = dedent(f"""
            <div class="sidebar-mini-card{' reversed' if card.get('reversed') else ''}">
              <img class="sidebar-mini-thumb" src="data:image/jpg;base64,{img_b64}" />
              <div class="sidebar-mini-title">
                {card['name']}{' <span class="badge">Reversed</span>' if card.get('reversed') else ''}
              </div>
            </div>
            """).strip()
            st.sidebar.markdown(html, unsafe_allow_html=True)
        except FileNotFoundError:
            st.sidebar.warning(f"Missing image: {tarot_path}")
else:
    st.sidebar.info("No cards drawn yet... 🌌")

# Clear conversation
if st.sidebar.button("🧹 Clear Conversation"):
    st.session_state.history = []
    st.session_state.tarot_archive = []


# ---------------------------
# Chat Input Handling (sidebar click -> prefill & send)
# ---------------------------
typed_input = st.chat_input("✨ Ask the Oracle...")
user_input = st.session_state.pending_question if st.session_state.pending_question else typed_input
st.session_state.pending_question = None


# ---------------------------
# Process Input
# ---------------------------
if user_input:
    # Save user message
    st.session_state.history.append({"role": "user", "content": user_input})

    # Draw tarot (before prophecy, so oracle can use it)
    if spread_mode == "Single Card":
        card = draw_tarot_card()
        st.session_state.history.append({"role": "tarot", "content": [card]})
        st.session_state.tarot_archive.append(card)

        # Pass single card into oracle
        prophecy_text = ""
        for token in ask_oracle(user_input, tarot_card=card):
            prophecy_text += token

    else:  # 3-Card Spread
        positions = ["Past", "Present", "Future"]
        spread = []
        for pos in positions:
            c = draw_tarot_card()
            spread.append({"position": pos, **c})
            st.session_state.tarot_archive.append(c)
        st.session_state.history.append({"role": "tarot", "content": spread})

        # Build a tarot summary string for Oracle
        tarot_summary = "; ".join([f"{c['position']}: {c['name']} ({c['meaning']})" for c in spread])

        prophecy_text = ""
        for token in ask_oracle(
            user_input,
            tarot_card={"name": "3-Card Spread", "meaning": tarot_summary}
        ):
            prophecy_text += token

    # Save oracle message (unrendered so typing effect will play)
    st.session_state.history.append({"role": "oracle", "content": prophecy_text, "rendered": False})

# ---------------------------
# Display Chat
# ---------------------------
for entry in st.session_state.history:
    role = entry["role"]

    if role == "user":
        st.markdown(f"<div class='user-bubble'>{entry['content']}</div>", unsafe_allow_html=True)

    elif role == "oracle":
        # typing effect only once on the latest oracle message
        if not entry.get("rendered", False):
            placeholder = st.empty()
            typed = ""
            for ch in entry["content"]:
                typed += ch
                placeholder.markdown(f"<div class='oracle-bubble'>{typed} ▌</div>", unsafe_allow_html=True)
                time.sleep(0.02)
            placeholder.markdown(f"<div class='oracle-bubble'>{entry['content']}</div>", unsafe_allow_html=True)
            entry["rendered"] = True
        else:
            st.markdown(f"<div class='oracle-bubble'>{entry['content']}</div>", unsafe_allow_html=True)

    elif role == "tarot":
        tarot = entry["content"]
        is_spread = any(isinstance(c, dict) and ("position" in c) for c in tarot)

        if is_spread:
            cols = st.columns(len(tarot))
            for idx, card in enumerate(tarot):
                tarot_path = os.path.join("images", "tarot", card["image"])
                with open(tarot_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()

                card_html = dedent(f"""
                <div class='tarot-card {"reversed" if card.get("reversed") else ""}'>
                    <img src='data:image/jpg;base64,{img_b64}' />
                    <b>{card['position']} – {card['name']}</b>
                    <span>{card['meaning']}</span>
                    {"<div class='badge'>Reversed</div>" if card.get("reversed") else ""}
                </div>
                """).strip()
                with cols[idx]:
                    st.markdown(card_html, unsafe_allow_html=True)

        else:
            card = tarot[0]
            tarot_path = os.path.join("images", "tarot", card["image"])
            with open(tarot_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            card_html = dedent(f"""
            <div class='tarot-card {"reversed" if card.get("reversed") else ""}'>
                <img src='data:image/jpg;base64,{img_b64}' />
                <b>{card['name']}</b>
                <span>{card['meaning']}</span>
                {"<div class='badge'>Reversed</div>" if card.get("reversed") else ""}
            </div>
            """).strip()
            st.markdown(card_html, unsafe_allow_html=True)
