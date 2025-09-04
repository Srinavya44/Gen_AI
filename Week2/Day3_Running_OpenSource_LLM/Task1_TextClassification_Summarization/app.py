import streamlit as st
from transformers import pipeline

st.set_page_config(page_title="Fake News Detector", page_icon="📰", layout="centered")
st.title("📰 Fake News Detector")
st.write("Paste a headline or article to check if it’s **Fake** or **Real** using AI.")
# ---- Sidebar ----
st.sidebar.title("ℹ️ How to Use")
st.sidebar.write("Enter a news headline or short article, then click **Check News**.")
st.sidebar.write("Or try one of the sample inputs below:")

# Sample inputs
sample = st.sidebar.selectbox(
    "Choose a sample:",
    [
        "",
        "NASA confirms the sun will rise from the west starting in 2026.",  # Fake
        "India successfully lands Chandrayaan-3 on the lunar south pole.",  # Real
        "Chocolate may help improve memory, researchers suggest."           # Ambiguous
    ]
)

# Load Fake News model
@st.cache_resource
def load_model():
    return pipeline(
        "text-classification",
        model="Pulk17/Fake-News-Detection",
        tokenizer="Pulk17/Fake-News-Detection",
        truncation=True
    )

classifier = load_model()

# Input
news_text = st.text_area("Enter news text:", height=200, value=sample if sample else "")

# Custom button styling
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #2b8a3e;
        color: white;
        font-size: 16px;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 20px;
        transition: all 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #1e6b2d;
        transform: scale(1.02);
    }
    </style>
""", unsafe_allow_html=True)
if "history" not in st.session_state:
    st.session_state.history = []

if st.button("Check News"):
    if not news_text.strip():
        st.warning("Please enter some text to analyze.")
    else:
        # AI Classification
        with st.spinner("Checking with AI model…"):
            result = classifier(news_text)[0]

        label = "FAKE NEWS" if result["label"] == "LABEL_0" else "REAL NEWS"
        score = result["score"]

        # 🎨 Result Card
        st.subheader("Prediction")
        if "Fake" in label or "FAKE" in label:
            st.error("❌ Fake News Detected!")
        else:
            st.success("✅ Real News")

        # 📊 Confidence Progress Bar
        st.write(f"**Confidence:** {score:.2%}")
        st.progress(int(score * 100))

        # ⚠️ Low Confidence Warning
        if score < 0.6:
            st.warning("⚠️ The model is uncertain about this prediction. Please verify with trusted sources.")

        # 📝 Human-readable explanation
        st.markdown("### Explanation")
        if "Fake" in label or "FAKE" in label:
            st.write(
                f"The model predicts this text is **likely fake** with a confidence of **{score:.2%}**. "
                f"This means the AI detected patterns often found in misleading or fabricated news."
            )
        else:
            st.write(
                f"The model predicts this text is **likely real** with a confidence of **{score:.2%}**. "
                f"This suggests the writing style and content resemble authentic news sources."
            )

        # Save to history (max 5 items)
        st.session_state.history.insert(0, {
            "text": news_text[:80] + ("..." if len(news_text) > 80 else ""),
            "label": label,
            "score": f"{score:.2%}"
        })
        st.session_state.history = st.session_state.history[:5]

# ---- History Section ----
if st.session_state.history:
    st.sidebar.subheader("🕘 Recent Checks")
    for item in st.session_state.history:
        if "Fake" in item["label"]:
            st.sidebar.error(f"❌ {item['label']} ({item['score']})\n\n> {item['text']}")
        else:
            st.sidebar.success(f"✅ {item['label']} ({item['score']})\n\n> {item['text']}")