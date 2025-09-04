import os
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# Load env vars
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# Initialize client
client = Groq(api_key=GROQ_API_KEY)
system_prompt = """
You are The Mystic Oracle 🔮.
Speak in a poetic, mystical, metaphorical style—but stay relevant to the seeker's question.
Use symbols like 🌙✨🃏 when fitting. Avoid plain yes/no; offer omens and guidance.
Keep responses short and impactful (1–3 sentences).
When possible, weave the essence of the drawn Tarot card into the prophecy.
"""


def ask_oracle(question, tarot_card=None):
    messages = [{"role": "system", "content": system_prompt}]
    if tarot_card:
        messages.append({
            "role": "system",
            "content": f"The drawn tarot card is '{tarot_card['name']}' with meaning '{tarot_card['meaning']}'. "
                       "Weave this essence into your prophecy."
        })
    messages.append({"role": "user", "content": question})

    # your Groq/OpenAI call here...
    response = ""
    for token in client.chat.completions.create(
        model="llama3-8b-8192",
        messages=messages,
        stream=True
    ):
        if token.choices[0].delta.content:
            yield token.choices[0].delta.content
