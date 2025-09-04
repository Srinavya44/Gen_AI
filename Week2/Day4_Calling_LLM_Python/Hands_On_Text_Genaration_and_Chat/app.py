import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from streamlit.components.v1 import html as st_html

# --------------------------
# Config
# --------------------------
st.set_page_config(page_title="Groq AI Playground", page_icon="🤖", layout="centered")
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

HISTORY_FILE = "chat_history.json"

# --------------------------
# Intro / Header
# --------------------------
st.markdown("""
    <div style="text-align: center; padding: 30px;">
        <h1 style="font-size: 36px; color: #6C63FF;">🤖 Groq AI Playground</h1>
        <p style="font-size: 18px; color: #555;">
            Experiment with <b>Text Generation</b> and <b>Chat</b> using Groq's LLMs.<br>
            Switch modes from the sidebar and try prompts instantly.
        </p>
    </div>
""", unsafe_allow_html=True)

# --------------------------
# Helpers (multi-chat for Chat Mode)
# --------------------------
def load_all_chats():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chats": {}, "active_chat": None}

def save_all_chats(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_active_chat(data):
    active_id = data.get("active_chat")
    if not active_id or active_id not in data["chats"]:
        return None, []
    return active_id, data["chats"][active_id]["messages"]

def new_chat(data):
    chat_id = f"chat_{len(data['chats'])+1}"
    data["chats"][chat_id] = {
        "title": "Untitled Chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Always respond in English."}
        ]
    }
    data["active_chat"] = chat_id
    return chat_id, data

def delete_chat(data, chat_id):
    if chat_id in data["chats"]:
        del data["chats"][chat_id]
        if data["chats"]:
            data["active_chat"] = next(iter(data["chats"]))
        else:
            _, data = new_chat(data)
    return data

# --------------------------
# Init session
# --------------------------
if "all_chats" not in st.session_state:
    st.session_state["all_chats"] = load_all_chats()

chat_id, messages = get_active_chat(st.session_state["all_chats"])
if not chat_id:  # first launch
    chat_id, st.session_state["all_chats"] = new_chat(st.session_state["all_chats"])
    save_all_chats(st.session_state["all_chats"])

st.session_state["messages"] = messages

# --------------------------
# Sidebar
# --------------------------
st.sidebar.header("⚙️ Settings")

# Mode toggle
mode = st.sidebar.radio("Mode", ["Chat", "Text Generation"], index=0)

# Model settings
def get_available_models():
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        models = [m["id"] for m in r.json().get("data", [])]
        preferred = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"]
        ordered = [m for m in preferred if m in models] + [m for m in sorted(models) if m not in preferred]
        return ordered or preferred
    except Exception:
        return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"]

models = get_available_models()
selected_model = st.sidebar.selectbox("Model", models, index=0)
temperature = st.sidebar.slider("Creativity (temperature)", 0.0, 1.5, 0.7, 0.1)
max_tokens = st.sidebar.slider("Max tokens", 50, 2000, 500, 50)

# --------------------------
# Global Styles
# --------------------------
st.markdown("""
<style>
/* Chat bubbles */
.chat-row { display: flex; align-items: flex-start; margin: 8px 0; }
.chat-bubble {
    display: inline-block;
    padding: 10px 14px;
    border-radius: 16px;
    font-size: 15px;
    line-height: 1.45;
    word-wrap: break-word;
    max-width: 75%;
}
.chat-bubble.user {
    background: #0084ff; color: #fff;
    margin-left: auto; text-align: left;
    border-bottom-right-radius: 4px;
}
.chat-bubble.assistant {
    background: #f1f0f0; color: #000;
    margin-right: auto; text-align: left;
    border-bottom-left-radius: 4px;
}
.avatar { font-size: 20px; margin: 0 8px; }

</style>
""", unsafe_allow_html=True)

# --------------------------
# TEXT GENERATION MODE (minimal, Clear without explicit rerun)
# --------------------------
if mode == "Text Generation":
    st.subheader("Text Generation")

    # styles
    st.markdown("""
    <style>
      .tg-card{
        background:#fff; border:1px solid #e5e7eb; border-radius:16px;
        padding:18px; box-shadow:0 2px 10px rgba(0,0,0,.04); margin-top:8px;
      }
      .tg-bubble{
        background:#f1f0f0; color:#000;
        border-radius:16px; border-bottom-left-radius:4px;
        padding:12px 14px; line-height:1.55; font-size:15px;
        margin-top:10px;
      }
    </style>
    """, unsafe_allow_html=True)

    # session state
    st.session_state.setdefault("tg_prompt", "")
    st.session_state.setdefault("tg_output", "")

    # clear handler (no explicit st.rerun)
    def clear_tg():
        st.session_state["tg_prompt"] = ""
        st.session_state["tg_output"] = ""

    # input card
    tg_prompt = st.text_area(
        "Prompt",
        key="tg_prompt",     # bound to session state so clearing works
        height=140,
        placeholder="Type your prompt here...",
        label_visibility="collapsed"
    )
    SYSTEM_INSTRUCT = (
    "You are a concise, professional writing assistant. "
    "Write fluent, natural English. Do not output code or token-like strings.")
    c1, c2 = st.columns([1,1])
    generate_clicked = c1.button("Generate", type="primary", use_container_width=True)
    c2.button("Clear", type="secondary", use_container_width=True, on_click=clear_tg)
    # generate
    if generate_clicked and tg_prompt.strip():
        try:
            with st.spinner("Generating…"):
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_INSTRUCT},
                        {"role": "user", "content": tg_prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            st.session_state["tg_output"] = (response.choices[0].message.content or "").strip()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

    # output bubble
    if st.session_state["tg_output"]:
        def _escape_html(s: str) -> str:
            return (
                s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace("\n", "<br>")
            )
        st.markdown(
            f'<div class="tg-bubble">{_escape_html(st.session_state["tg_output"])}</div>',
            unsafe_allow_html=True
        )

# --------------------------
# CHAT MODE (fixed + robust)
# --------------------------
else:
    # st.subheader("Chat with Groq AI")

    # Sidebar chat controls
    if st.sidebar.button("➕ New Chat"):
        chat_id, st.session_state["all_chats"] = new_chat(st.session_state["all_chats"])
        save_all_chats(st.session_state["all_chats"])
        st.rerun()

    # Snapshot list so deleting while iterating is safe
    chat_items = list(st.session_state["all_chats"]["chats"].items())

    for cid, chat in chat_items:
        cols = st.sidebar.columns([4, 1])
        with cols[0]:
            if st.button(chat["title"], key=f"select_{cid}"):
                st.session_state["all_chats"]["active_chat"] = cid
                save_all_chats(st.session_state["all_chats"])
                st.rerun()
        with cols[1]:
            if st.button("🗑️", key=f"delete_{cid}"):
                st.session_state["all_chats"] = delete_chat(st.session_state["all_chats"], cid)
                save_all_chats(st.session_state["all_chats"])
                st.rerun()

    # Guard: ensure we always have a valid active chat + messages list
    active_chat = st.session_state["all_chats"].get("active_chat")
    if not active_chat or active_chat not in st.session_state["all_chats"]["chats"]:
        chat_id, st.session_state["all_chats"] = new_chat(st.session_state["all_chats"])
        save_all_chats(st.session_state["all_chats"])
        active_chat = chat_id

    st.session_state["messages"] = st.session_state["all_chats"]["chats"][active_chat].get("messages", [])
    if not isinstance(st.session_state["messages"], list):
        st.session_state["messages"] = []

    # Render history
    for msg in st.session_state["messages"]:
        if msg.get("role") == "system":
            continue
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            st.markdown(
                f"""
                <div class="chat-row" style="justify-content: flex-end;">
                    <div class="chat-bubble user">{content}</div>
                    <div class="avatar">🧑</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="chat-row" style="justify-content: flex-start;">
                    <div class="avatar">🤖</div>
                    <div class="chat-bubble assistant">{content}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Chat input
    prompt = st.chat_input("Type your message here...")
    if prompt:
        st.session_state["messages"].append({"role": "user", "content": prompt})

        if st.session_state["all_chats"]["chats"][active_chat]["title"] == "Untitled Chat":
            st.session_state["all_chats"]["chats"][active_chat]["title"] = prompt[:30]

        st.session_state["all_chats"]["chats"][active_chat]["messages"] = st.session_state["messages"]
        save_all_chats(st.session_state["all_chats"])

        st.markdown(
            f"""
            <div class="chat-row" style="justify-content: flex-end;">
                <div class="chat-bubble user">{prompt}</div>
                <div class="avatar">🧑</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        placeholder = st.empty()
        streamed = ""

        try:
            stream = client.chat.completions.create(
                model=selected_model,
                messages=st.session_state["messages"],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            for chunk in stream:
                if getattr(chunk, "choices", None):
                    delta = getattr(chunk.choices[0], "delta", None)
                    token = getattr(delta, "content", None) if delta else None
                    if token:
                        streamed += token
                        placeholder.markdown(
                            f"""
                            <div class="chat-row" style="justify-content: flex-start;">
                                <div class="avatar">🤖</div>
                                <div class="chat-bubble assistant">{streamed}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            st.session_state["messages"].append({"role": "assistant", "content": streamed})
            st.session_state["all_chats"]["chats"][active_chat]["messages"] = st.session_state["messages"]
            save_all_chats(st.session_state["all_chats"])

        except Exception as e:
            st.error(f"❌ Streaming Error: {str(e)}")
