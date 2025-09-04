import os
import re
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Folder where files are stored
DATA_FOLDER = "data"

# Find all .pdf and .txt files in the folder
files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith((".pdf", ".txt"))]

if not files:
    print("No PDF or TXT files found in the data folder.")
    exit()

# Splitter configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # characters
    chunk_overlap=100
)

total_chunks_all = 0  # Counter for all chunks

# Process each file
for file_name in files:
    file_path = os.path.join(DATA_FOLDER, file_name)
    
    # Select loader based on file type
    if file_name.lower().endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path)
    
    # Load and split
    docs = loader.load()
    for doc in docs:
        doc.page_content = re.sub(r'\s+', ' ', doc.page_content).strip()
    chunks = text_splitter.split_documents(docs)
    
    total_chunks_all += len(chunks)  # Accumulate total

# Print only the grand total
print(f"📊 Total chunks created: {total_chunks_all}")
