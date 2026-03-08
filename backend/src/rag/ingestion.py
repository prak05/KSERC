import os
import logging
import pickle
import uuid
from typing import List
from dotenv import load_dotenv

import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_community.retrievers import BM25Retriever
import vertexai

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("rag_ingestion")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(BACKEND_DIR, "data", "documents")
DB_DIR = os.path.join(BACKEND_DIR, "data", "precedent_db", "global_chroma")
BM25_PATH = os.path.join(BACKEND_DIR, "data", "precedent_db", "bm25_retriever.pkl")
DOC_STORE_PATH = os.path.join(BACKEND_DIR, "data", "precedent_db", "doc_store.pkl")

REGULATION_FILES = [
    "Master Tariff Order (OP 18 2023).pdf",
    "First Amendment, 2023.pdf",
    "secondAmendment, 2024.pdf",
    "Third Amendment, 2025.pdf",
    "Kerala Electricity Duty Act, 1963.pdf",
    "Kerala Electricity Duty Rules, 1963.pdf",
    "Technopark MYT Order OP 12 2023.pdf",
    "Infopark MYT Order (OP 09 2023).pdf",
    "CSEZA MYT Order 19 1 24.pdf",
    "Kannan Devan Hills Plantations MYT Order 26-11-25.pdf",
    "Technopark True-Up 2022-23 (OP 84 2023).pdf",
    "Infopark True-Up 2022-23 (OP 82 2023).pdf",
    "Kannan Devan Hills Plantations Company FY 2022-23 Truing Up Order.pdf",
    "Kannan Devan Hills Plantations Company FY 2021-22 Truing Up Order.pdf",
    "Cochin Special Economic Zone Authority FY 2020-21 Truing Up Order.pdf",
    "Cochin Special Economic Zone Authority FY 2019-20 Truing Up Order.pdf",
    "Cochin Special Economic Zone Authority FY 2018-19 Truing Up Order.pdf"
]

def load_pdfs() -> List[Document]:
    docs = []
    for filename in REGULATION_FILES:
        filepath = os.path.join(DOCS_DIR, filename)
        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filename}")
            continue
            
        logger.info(f"Loading {filename}...")
        try:
            doc = fitz.open(filepath)
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={
                            "source": filename,
                            "page": page_num + 1
                        }
                    ))
            doc.close()
        except Exception as e:
            logger.error(f"Failed to read {filename}: {e}")
    return docs

def execute_ingestion():
    key_path = os.path.abspath("vertex_sa.json")
    if not os.path.exists(key_path):
        logger.error("vertex_sa.json not found! Cannot initialize VertexAI.")
        return
        
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    vertexai.init(project="triple-cab-488111-f5", location="us-central1")
    
    logger.info("1. Loading PDFs...")
    documents = load_pdfs()
    logger.info(f"Loaded {len(documents)} total pages.")
    
    if not documents:
        logger.warning("No documents loaded. Exiting.")
        return

    logger.info("2. Splitting text into Parent chunks...")
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    parent_docs = parent_splitter.split_documents(documents)
    
    # Give every parent document a unique UUID
    for doc in parent_docs:
        doc.metadata["doc_id"] = str(uuid.uuid4())
        
    logger.info(f"Generated {len(parent_docs)} parent chunks.")

    logger.info("3. Saving Parent Documents to DocStore...")
    doc_store = {doc.metadata["doc_id"]: doc for doc in parent_docs}
    with open(DOC_STORE_PATH, "wb") as f:
        pickle.dump(doc_store, f)

    logger.info("4. Creating BM25 Index (Hybrid Keyword Search)...")
    bm25_retriever = BM25Retriever.from_documents(parent_docs)
    bm25_retriever.k = 3
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25_retriever, f)
    logger.info("BM25 Retreiver pickled to disk.")

    logger.info("5. Splitting Parents into Child chunks...")
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    child_docs = []
    for parent in parent_docs:
        children = child_splitter.split_documents([parent])
        for child in children:
            # Ensure the child has the exact same doc_id as the parent
            child.metadata["doc_id"] = parent.metadata["doc_id"]
            child_docs.append(child)
            
    logger.info(f"Generated {len(child_docs)} child chunks for Vector Search.")

    logger.info("6. Embedding Child chunks into ChromaDB...")
    embeddings = VertexAIEmbeddings(model_name="text-embedding-004")
    db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    
    batch_size = 100
    for i in range(0, len(child_docs), batch_size):
        batch = child_docs[i:i + batch_size]
        logger.info(f"   -> Adding batch {i//batch_size + 1}/{len(child_docs)//batch_size + 1} ({len(batch)} chunks)...")
        db.add_documents(batch)
        
    logger.info("Ingestion complete! Hybrid Native RAG Vector DB & DocStore ready.")

if __name__ == "__main__":
    execute_ingestion()
