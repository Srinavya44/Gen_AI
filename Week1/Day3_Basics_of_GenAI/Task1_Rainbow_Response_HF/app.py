import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Streamlit page setup
st.set_page_config(page_title="Groq Chatbot", page_icon="💬", layout="wide")

# Title
st.markdown("<h1 style='text-align: center;'>💬 Groq AI Chatbot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Talk to LLaMA-3 or mix models for fun!</p>", unsafe_allow_html=True)

# Sidebar for settings
st.sidebar.header("⚙️ Settings")
model_choice = st.sidebar.selectbox(
    "Choose Model:",
    ["llama3-8b-8192", "llama3-70b-8192"],
    index=0
)

# Session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# Display chat history with avatars
for msg in st.session_state.messages:
    if msg["role"] != "system":  # Skip system prompt
        avatar = "👤" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Generate assistant reply
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model=model_choice,
                messages=st.session_state.messages
            )
            answer = response.choices[0].message.content
            st.markdown(answer)

    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": answer})
