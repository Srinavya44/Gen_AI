import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import base64
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
# CONFIG

POEM_MODEL = "llama3-8b-8192"
IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

def image_to_base64(img):
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

# Streamlit page config
st.set_page_config(page_title="Poem & Art Generator", page_icon="🎨", layout="centered")

# Global CSS Styling
# Updated CSS with adaptive colors
st.markdown(
    """
    <style>
    :root {
        --bg-start: #d9e4f5;  /* gradient start */
        --bg-end: #f8f0e3;    /* gradient end */
        --text-color: #222222; /* default dark text */
    }

    /* Background */
    body, .css-18e3th9 {
        background: linear-gradient(135deg, var(--bg-start), var(--bg-end));
        color: var(--text-color);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Title */
    .center-title {
        text-align: center;
        margin-top: -20px;
        color: var(--text-color);
    }

    /* Card styling with equal heights */
    .card {
        background-color: rgba(250, 249, 247, 0.9);
        padding: 25px;
        border-radius: 18px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
        margin-bottom: 25px;
        height: 500px; /* fixed equal height */
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        text-align: center;
        color: var(--text-color);
        transition: transform 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 25px rgba(0, 0, 0, 0.2);
    }

    /* Poem text */
    .poem-text {
        white-space: pre-line;
        text-align: left;
        margin-top: 10px;
        font-size: clamp(14px, 2vw, 18px);
        line-height: 1.6;
        flex-grow: 1;
        overflow-y: auto;
        color: var(--text-color);
    }

    /* Image */
    .card img {
        max-width: 100%;
        max-height: 350px;
        border-radius: 14px;
        object-fit: contain;
        flex-grow: 1;
        box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    }

    /* Footer */
    .card-footer {
        margin-top: auto;
        font-size: 14px;
        color: #555555;
        font-style: italic;
    }

    /* Headings */
    h1, h2, h3 {
        color: var(--text-color);
    }

    /* Buttons */
    div.stButton > button {
        background: linear-gradient(45deg, #6a8dd4, #a48de8);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 10px;
        padding: 8px 18px;
        transition: background 0.3s ease;
        display: block;
        margin: 0 auto;
    }
    div.stButton > button:hover {
        background: linear-gradient(45deg, #5a7cc4, #9277d8);
        cursor: pointer;
    }

    /* Input box */
    input[type="text"] {
        background-color: #f0f3f8 !important;
        border-radius: 8px !important;
        border: 1.5px solid #c1c7d0 !important;
        color: #222 !important;
        padding: 8px 12px !important;
        font-size: 16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)



# Title
st.markdown("<h1 class='center-title'>🎨 Poem & AI Art Generator</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Enter a topic and let AI create a <b>beautiful poem</b> and <b>matching artwork</b>.</p>", unsafe_allow_html=True)

# Input
topic = st.text_input("", placeholder="e.g., Moonlit ocean waves")

poem = None
img_base64 = None

if st.button("✨ Generate"):
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        with st.spinner("Generating poem..."):
            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            data = {
                "model": POEM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a creative poet."},
                    {"role": "user", "content": f"Write exactly 10 lines of a short, creative poem about: {topic}. Format it line by line."}
                ],
                "temperature": 0.8
            }
            response = requests.post(groq_url, headers=headers, json=data)
            if response.status_code == 200:
                poem = response.json()["choices"][0]["message"]["content"]
            else:
                st.error(f"Poem generation failed: {response.text}")

        if poem:
            with st.spinner("Generating image..."):
                hf_url = f"https://api-inference.huggingface.co/models/{IMAGE_MODEL}"
                headers = {"Authorization": f"Bearer {HF_API_KEY}"}
                payload = {"inputs": f"An artistic, detailed illustration for: {topic}"}
                img_response = requests.post(hf_url, headers=headers, json=payload)

                if img_response.status_code == 200:
                    image = Image.open(BytesIO(img_response.content))
                    img_base64 = image_to_base64(image)
                else:
                    st.error(f"Image generation failed: {img_response.text}")

if poem and img_base64:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
            <div class="card">
                <h3>📜 Your Poem</h3>
                <div class="poem-text">{poem}</div>
                <div class="card-footer">Poem for: {topic}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="card">
                <h3>🖼️ Generated Artwork</h3>
                <img src="data:image/png;base64,{img_base64}" alt="Generated Artwork"/>
                <div class="card-footer">Artwork for: {topic}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
