# rag_ui.py
import os
import tempfile
import streamlit as st
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_cohere import CohereEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq

# -------------------------
# Config & API keys
# -------------------------
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not COHERE_API_KEY or not GROQ_API_KEY:
    st.error("Missing API keys in .env file")
    st.stop()

# -------------------------
# Session state defaults
# -------------------------
if "db" not in st.session_state:
    st.session_state.db = None
if "files_processed" not in st.session_state:
    st.session_state.files_processed = []
if "raw_files" not in st.session_state:
    # store uploaded bytes by filename so we can offer downloads later
    st.session_state.raw_files = {}
if "qa_history" not in st.session_state:
    st.session_state.qa_history = []  # list of dicts: {"question","answer","sources_map"}
if "current_question" not in st.session_state:
    st.session_state.current_question = ""
if "auto_generate" not in st.session_state:
    st.session_state.auto_generate = False
if "index_ready" not in st.session_state:
    st.session_state.index_ready = False
if "answer_style" not in st.session_state:
    st.session_state.answer_style = "Concise"

# -------------------------
# Helper: build index and keep metadata clean
# -------------------------
def build_index_from_files(files):
    """
    - Writes uploads to temp files for PyPDFLoader/TextLoader
    - Loads docs and sets metadata['source'] to original filename
    - Sets metadata['page'] to 1-based page number where applicable
    - Splits into chunks, creates Cohere embeddings and FAISS index
    """
    documents = []
    for file in files:
        # read bytes and store in session for later downloads
        data = file.read()
        st.session_state.raw_files[file.name] = data

        # write to a temp file so PyPDFLoader can open it by path
        suffix = os.path.splitext(file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(data)
            tmp_path = tmp_file.name

        # load document(s)
        if file.name.lower().endswith(".pdf"):
            loader = PyPDFLoader(tmp_path)
            loaded = loader.load()  # likely returns page-level Document objects
            # ensure metadata has original filename and 1-based page numbers
            for i, doc in enumerate(loaded):
                # if loader already set page metadata, use it; else assume order
                page_meta = doc.metadata.get("page", None)
                try:
                    page_num = int(page_meta) + 1 if page_meta is not None else i + 1
                except Exception:
                    page_num = i + 1
                doc.metadata["source"] = file.name
                doc.metadata["page"] = page_num
            documents.extend(loaded)
        elif file.name.lower().endswith(".txt"):
            loader = TextLoader(tmp_path, encoding="utf-8")
            loaded = loader.load()
            # set source and page=1 for text files
            for doc in loaded:
                doc.metadata["source"] = file.name
                doc.metadata["page"] = 1
            documents.extend(loaded)
        else:
            continue

    # split into chunks while preserving metadata
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)

    # create Cohere embeddings and FAISS index
    embeddings = CohereEmbeddings(model="embed-english-v3.0", cohere_api_key=COHERE_API_KEY)
    db = FAISS.from_documents(docs, embeddings)
    return db

# -------------------------
# Helper: answer question
# -------------------------
def answer_question(query, db, style="Concise"):
    """
    Returns: (answer_text, source_documents)
      - source_documents is the list of Documents returned by the retriever
      (their metadata should include 'source' and 'page' as set earlier)
    """
    retriever = db.as_retriever()
    # use the retriever.invoke as in your original code to get relevant chunks
    docs = retriever.invoke(query)

    # build prompt with style guidance
    if style == "Concise":
        length_instruction = "Answer briefly in 2-3 sentences."
    else:
        length_instruction = "Provide a detailed, well-structured explanation."

    context = "\n".join([d.page_content for d in docs])
    prompt = f"""
    You are a knowledgeable assistant. {length_instruction}
    Answer the question based on the context below.

    Context:
    {context}

    Question: {query}
    """

    llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="llama3-8b-8192")
    response = llm.invoke(prompt)
    return response.content, docs

# -------------------------
# UI: sidebar history (left panel)
# -------------------------
st.set_page_config(page_title="RAG PDF/TXT QA", layout="wide")
with st.sidebar:
    st.header("📜 History")
    if st.session_state.qa_history:
        # show newest first
        for idx, item in enumerate(list(reversed(st.session_state.qa_history))):
            # idx: 0 is newest here
            cols = st.columns([0.85, 0.15])
            q_key = f"hist_load_{idx}"
            rerun_key = f"hist_rerun_{idx}"
            # clicking the question loads it into input box for editing
            if cols[0].button(item["question"][:60] + ("..." if len(item["question"]) > 60 else ""), key=q_key):
                st.session_state.current_question = item["question"]
            # rerun icon: run the question immediately
            if cols[1].button("🔁", key=rerun_key):
                st.session_state.current_question = item["question"]
                st.session_state.auto_generate = True
    else:
        st.write("No history yet.")
    st.markdown("---")
    if st.button("Clear history"):
        st.session_state.qa_history = []

# -------------------------
# MAIN UI
# -------------------------
st.title("📄 RAG Pipeline: PDF/TXT Question Answering")

# file uploader (auto-build index when uploaded files set changes)
uploaded_files = st.file_uploader("Upload one or more PDF / TXT files", type=["pdf", "txt"], accept_multiple_files=True)

if uploaded_files:
    uploaded_names = [f.name for f in uploaded_files]
    if st.session_state.files_processed != uploaded_names:
        # New upload or changed files -> rebuild index
        with st.spinner("Processing documents and building index... This may take a while ⏳"):
            st.session_state.db = build_index_from_files(uploaded_files)
            st.session_state.files_processed = uploaded_names
            st.session_state.index_ready = True
        # do not show big toast; small subtle indicator is shown below near the Generate button
else:
    # if uploader cleared, keep the index in session memory (user requested this earlier).
    pass

# answer style toggle
st.write("")  # spacing
style_cols = st.columns([0.35, 0.65])
with style_cols[0]:
    st.session_state.answer_style = st.radio("Answer Style:", ["Concise", "Detailed"], index=0 if st.session_state.answer_style == "Concise" else 1, horizontal=True)

# question input area
with style_cols[1]:
    question = st.text_input("Ask a question about the uploaded documents:", value=st.session_state.current_question, key="question_input")

# small status + generate button row
gen_cols = st.columns([0.85, 0.15])
with gen_cols[0]:
    # subtle index-ready indicator
    if st.session_state.index_ready and st.session_state.db is not None:
        st.markdown("<span style='color:green;font-weight:600;'>● Index ready</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span style='color:gray;'>● Index not ready</span>", unsafe_allow_html=True)

with gen_cols[1]:
    # Generate button
    generate_clicked = st.button("Generate Answer")

# If user clicked history re-run, auto_generate flag will be True — run generation immediately
if st.session_state.auto_generate:
    # set generate_clicked to True and then clear the auto flag so the run happens once
    generate_clicked = True
    st.session_state.auto_generate = False

# Run generation only when the user clicks Generate (or clicked rerun)
if generate_clicked:
    if not question or question.strip() == "":
        st.warning("Please enter a question before generating an answer.")
    elif st.session_state.db is None:
        st.warning("Index not ready. Upload files to build the index first.")
    else:
        with st.spinner("Generating answer..."):
            answer_text, docs_used = answer_question(question, st.session_state.db, st.session_state.answer_style)

        # create a compact mapping filename -> set(page numbers)
        sources_map = {}
        for d in docs_used:
            fname = d.metadata.get("source", "Unknown")
            page = d.metadata.get("page", "N/A")
            try:
                page_int = int(page)
            except Exception:
                # attempt to coerce if it's string like "1"
                try:
                    page_int = int(str(page))
                except Exception:
                    page_int = "N/A"
            # keep page as 1-based int if possible
            if isinstance(page_int, int):
                page_display = page_int
            else:
                page_display = page
            sources_map.setdefault(fname, set()).add(page_display)

        # convert sets to sorted lists
        for k in list(sources_map.keys()):
            pages = sorted([p for p in sources_map[k]])
            sources_map[k] = pages

        # Save history (prepend newest)
        entry = {"question": question, "answer": answer_text, "sources_map": sources_map}
        st.session_state.qa_history.append(entry)

        # show styled answer card
        st.markdown(
            f"""
            <div style='background:#f6f8fa;padding:16px;border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,0.06);'>
                <h4 style='margin:4px 0 8px 0;'>💡 Answer</h4>
                <div style='font-size:15px;line-height:1.5;'>{answer_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # sources expander (only visible when user expands)
        if sources_map:
            with st.expander("📚 Sources (click to expand)"):
                for fname, pages in sources_map.items():
                    st.markdown(f"**{fname}** — Pages: {', '.join(str(p) for p in pages)}")
                    # provide download button for the underlying uploaded file (if still in session)
                    if fname in st.session_state.raw_files:
                        st.download_button(
                            label=f"Download {fname}",
                            data=st.session_state.raw_files[fname],
                            file_name=fname,
                            mime="application/pdf" if fname.lower().endswith(".pdf") else "text/plain",
                        )

        # clear the input question (optional) and keep last in current_question
        st.session_state.current_question = question

# end of file
