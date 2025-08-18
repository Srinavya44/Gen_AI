import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# --------------------------
# Config
# --------------------------
st.set_page_config(page_title="Groq AI Chat", page_icon="🤖", layout="centered")
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

HISTORY_FILE = "chat_history.json"

# --------------------------
# Helpers (multi-chat)
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
# Sidebar (multi-chat)
# --------------------------
st.sidebar.header("⚙️ Settings")

if st.sidebar.button("➕ New Chat"):
    chat_id, st.session_state["all_chats"] = new_chat(st.session_state["all_chats"])
    save_all_chats(st.session_state["all_chats"])
    st.rerun()

# list all chats with delete button
for cid, chat in st.session_state["all_chats"]["chats"].items():
    cols = st.sidebar.columns([4,1])
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

# model + settings
models = []
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
# Styles (iMessage-like)
# --------------------------
st.markdown("""
<style>
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
avatar { font-size: 20px; margin: 0 8px; }
</style>
""", unsafe_allow_html=True)

# --------------------------
# Title / Welcome
# --------------------------
if len([m for m in st.session_state["messages"] if m["role"] != "system"]) == 0:
    st.markdown("""
        <div style="text-align: center; padding-top: 60px;">
            <h1 style="font-size: 34px; color: #333;">🤖 Welcome to <span style="color:#6C63FF;">Groq AI Chat</span></h1>
            <p style="color: #666; font-size: 18px;">Ask me anything and I’ll respond instantly.</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.title("🤖 Groq AI Chat")

# --------------------------
# Render history (skip system)
# --------------------------
for msg in st.session_state["messages"]:
    role = msg["role"]
    if role == "system":
        continue
    content = msg["content"]
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

# --------------------------
# Input + Streaming
# --------------------------
prompt = st.chat_input("Type your message here...")

if prompt:
    # 1) Record user message
    st.session_state["messages"].append({"role": "user", "content": prompt})

    # update title if needed
    active_chat = st.session_state["all_chats"]["active_chat"]
    if st.session_state["all_chats"]["chats"][active_chat]["title"] == "Untitled Chat":
        st.session_state["all_chats"]["chats"][active_chat]["title"] = prompt[:30]

    st.session_state["all_chats"]["chats"][active_chat]["messages"] = st.session_state["messages"]
    save_all_chats(st.session_state["all_chats"])

    # 2) Show user's bubble immediately
    st.markdown(
        f"""
        <div class="chat-row" style="justify-content: flex-end;">
            <div class="chat-bubble user">{prompt}</div>
            <div class="avatar">🧑</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3) Stream assistant reply
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
            if chunk.choices and getattr(chunk.choices[0].delta, "content", None):
                token = chunk.choices[0].delta.content
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

        # 4) Save final assistant message
        st.session_state["messages"].append({"role": "assistant", "content": streamed})
        st.session_state["all_chats"]["chats"][active_chat]["messages"] = st.session_state["messages"]
        save_all_chats(st.session_state["all_chats"])

    except Exception as e:
        st.error(f"❌ Streaming Error: {str(e)}")
