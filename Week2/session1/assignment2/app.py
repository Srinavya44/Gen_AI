import os
import requests
import streamlit as st
from dotenv import load_dotenv

# -----------------------
# Load environment variables
# -----------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama3-8b-8192"   # Groq model

# -----------------------
# Groq API Call
# -----------------------
def generate_response(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()["choices"][0]["message"]["content"]

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="AI Travel Buddy", page_icon="🌍", layout="wide")

st.markdown(
    """
    <h1 style='text-align: center;'>🌍 AI Travel Buddy ✈️</h1>
    <p style='text-align: center; font-size:18px; color:gray;'>
    Plan your trip with Role-based or Chain-of-Thought prompting!
    </p>
    """,
    unsafe_allow_html=True
)

# Destination input
destination = st.text_input("📍 Enter a destination:", "Tokyo")

# Prompt type selection
prompt_type = st.radio("🎯 Choose Prompting Style:", ["Role-based", "Chain-of-Thought", "Compare Both"])

# Role dropdown if Role-based or Compare
role = None
if prompt_type in ["Role-based", "Compare Both"]:
    role = st.selectbox("👤 Choose a travel persona:",
                        ["Tour Guide", "Foodie", "Historian", "Luxury Travel Agent"])

# -----------------------
# Generate button
# -----------------------
if st.button("✨ Generate Itinerary"):
    if prompt_type == "Role-based":
        prompt = f"You are a {role}. Plan a 3-day trip to {destination} in your unique style."
        with st.spinner("✈️ Planning your trip..."):
            role_output = generate_response(prompt)

        st.markdown(
            f"""
            <div style="background-color:#f0f8ff; padding:20px; border-radius:12px; box-shadow:2px 2px 8px rgba(0,0,0,0.1);">
            <h3>🗺️ {role} Style Itinerary</h3>
            <p>{role_output}</p>
            </div>
            """, unsafe_allow_html=True
        )

    elif prompt_type == "Chain-of-Thought":
        prompt = f"Plan a 3-day trip to {destination} step by step. " \
                 f"First choose attractions, then organize them into daily itineraries, " \
                 f"then add food and cultural recommendations. Explain your reasoning clearly."
        with st.spinner("🧠 Thinking step by step..."):
            cot_output = generate_response(prompt)

        st.markdown(
            f"""
            <div style="background-color:#fff0f5; padding:20px; border-radius:12px; box-shadow:2px 2px 8px rgba(0,0,0,0.1);">
            <h3>🧠 Step-by-Step Itinerary</h3>
            <p>{cot_output}</p>
            </div>
            """, unsafe_allow_html=True
        )

    elif prompt_type == "Compare Both":
        role_prompt = f"You are a {role}. Plan a 3-day trip to {destination} in your unique style."
        cot_prompt = f"Plan a 3-day trip to {destination} step by step. " \
                     f"First choose attractions, then organize them into daily itineraries, " \
                     f"then add food and cultural recommendations. Explain your reasoning clearly."

        with st.spinner("✨ Generating both styles..."):
            role_output = generate_response(role_prompt)
            cot_output = generate_response(cot_prompt)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f"""
                <div style="background-color:#f0f8ff; padding:20px; border-radius:12px; box-shadow:2px 2px 8px rgba(0,0,0,0.1);">
                <h3>🗺️ Role-based ({role})</h3>
                <p>{role_output}</p>
                </div>
                """, unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div style="background-color:#fff0f5; padding:20px; border-radius:12px; box-shadow:2px 2px 8px rgba(0,0,0,0.1);">
                <h3>🧠 Chain-of-Thought</h3>
                <p>{cot_output}</p>
                </div>
                """, unsafe_allow_html=True
            )
