import os
import json
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# -----------------------
# Env & Config
# -----------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

if not GROQ_API_KEY:
    st.warning("Set GROQ_API_KEY in your .env file before using the app.")

# -----------------------
# Prompt templates
# -----------------------
ZERO_SHOT_TEMPLATE = """Given a short movie idea, create a catchy one-sentence movie pitch suitable for a poster.
Keep it to one sentence.

Idea: "{idea}"
"""

FEW_SHOT_TEMPLATE = """Given a short movie idea, create a catchy one-sentence movie pitch suitable for a poster.
Keep it to one sentence.

Example 1:
Idea: "A chef who can taste people's emotions in food."
Pitch: "A gifted chef discovers the bittersweet truth hidden in every bite — and every heart."

Example 2:
Idea: "A shy teenager finds a pair of magical shoes."
Pitch: "One step at a time, she dances her way into a world she never dreamed was hers."

Example 3:
Idea: "A scientist builds a time machine out of a photo booth."
Pitch: "Every snapshot takes them deeper into the past — and closer to rewriting the future."

Now create a pitch for this idea:
"{idea}"
"""

# -----------------------
# Groq Chat helper
# -----------------------
def groq_chat(prompt: str, temperature: float = 0.7, max_tokens: int = 128) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Return only the final pitch without extra commentary."},
            {"role": "user", "content": prompt},
        ],
        "temperature": float(temperature),
        "max_completion_tokens": int(max_tokens)  # ✅ Correct param for Groq
    }

    try:
        resp = requests.post(GROQ_URL, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as http_err:
        try:
            err_data = resp.json()
            err_msg = err_data.get("error", {}).get("message", str(http_err))
        except Exception:
            err_msg = str(http_err)
        raise RuntimeError(f"Groq API Error: {err_msg}")
    except requests.exceptions.RequestException as req_err:
        raise RuntimeError(f"Request Error: {req_err}")

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="Zero-shot vs Few-shot — Movie Pitch Generator", page_icon="🎬", layout="wide")
st.markdown(
    """
    <div style="text-align:center;">
      <h2 style="font-size:28px; margin-bottom:5px;">
        🎬 Zero-shot vs Few-shot — Movie Pitch Generator
      </h2>
    """,
    unsafe_allow_html=True
)
st.caption("Compare outputs instantly ")

with st.sidebar:
    st.subheader("Model & Parameters")
    st.text_input("Groq Model", value=GROQ_MODEL, key="model", help="Set in .env as GROQ_MODEL")
    temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.1)
    max_tokens = st.slider("Max tokens", 32, 512, 128, 16)
    st.markdown("---")
    st.markdown("**Tip:** One click runs both prompts for instant comparison.")

# -----------------------
# Session state
# -----------------------
if "zero_out" not in st.session_state:
    st.session_state.zero_out = ""
if "few_out" not in st.session_state:
    st.session_state.few_out = ""

# -----------------------
# Single Idea Test
# -----------------------
# st.markdown("### Single Idea Test")
idea = st.text_input(
    "Enter a short movie idea",
    value="A librarian finds a book that writes back."
)

if st.button("Generate Both Outputs"):
    if not GROQ_API_KEY:
        st.error("Missing GROQ_API_KEY. Set it in your .env.")
    else:
        try:
            z_prompt = ZERO_SHOT_TEMPLATE.format(idea=idea)
            f_prompt = FEW_SHOT_TEMPLATE.format(idea=idea)
            st.session_state.zero_out = groq_chat(z_prompt, temperature=temperature, max_tokens=max_tokens)
            st.session_state.few_out = groq_chat(f_prompt, temperature=temperature, max_tokens=max_tokens)
            st.success("Both outputs generated!")
        except Exception as e:
            st.error(str(e))

col1, col2 = st.columns(2)

with col1:
    if st.session_state.zero_out:   # ✅ Show only if generated
        st.markdown("### 🎯 Zero-shot Output")
        st.markdown(
            f"""
            <div style="
                background-color:#f9f9f9;
                padding:15px;
                border-radius:12px;
                box-shadow:0 2px 6px rgba(0,0,0,0.1);
                font-size:16px;
            ">
                {st.session_state.zero_out}
            </div>
            """,
            unsafe_allow_html=True
        )

with col2:
    if st.session_state.few_out:    # ✅ Show only if generated
        st.markdown("### 🎬 Few-shot Output")
        st.markdown(
            f"""
            <div style="
                background-color:#f9f9f9;
                padding:15px;
                border-radius:12px;
                box-shadow:0 2px 6px rgba(0,0,0,0.1);
                font-size:16px;
            ">
                {st.session_state.few_out}
            </div>
            """,
            unsafe_allow_html=True
        )


