import os
import logging
import pickle
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_community.vectorstores import Chroma
from langchain_google_vertexai import VertexAIEmbeddings
import vertexai

load_dotenv()
logger = logging.getLogger("rag_retriever")

DB_DIR = r"c:\Users\adwai\OneDrive\Desktop\K-Project\kserc_sdl_truing_up\chroma_db"
BM25_PATH = r"c:\Users\adwai\OneDrive\Desktop\K-Project\kserc_sdl_truing_up\bm25_retriever.pkl"
DOC_STORE_PATH = r"c:\Users\adwai\OneDrive\Desktop\K-Project\kserc_sdl_truing_up\doc_store.pkl"

class LegalResearcher:
    def __init__(self):
        key_path = os.path.abspath("vertex_sa.json")
        if not os.path.exists(key_path):
            raise FileNotFoundError("vertex_sa.json not found! Cannot initialize VertexAI.")
            
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        vertexai.init(project="triple-cab-488111-f5", location="us-central1")
        
        self.embeddings = VertexAIEmbeddings(model_name="text-embedding-004")
        
        # Load existing Vector DB, BM25, and DocStore
        if not os.path.exists(DB_DIR) or not os.path.exists(DOC_STORE_PATH) or not os.path.exists(BM25_PATH):
            raise FileNotFoundError("RAG indices not found. Run ingestion.py first.")
            
        self.db = Chroma(persist_directory=DB_DIR, embedding_function=self.embeddings)
        self.vector_retriever = self.db.as_retriever(search_kwargs={"k": 4})
        
        with open(BM25_PATH, "rb") as f:
            self.bm25_retriever = pickle.load(f)
            self.bm25_retriever.k = 3 # Fetch top 3 keywords
            
        with open(DOC_STORE_PATH, "rb") as f:
            self.doc_store = pickle.load(f)

    def query_regulations(self, topic: str) -> str:
        """
        Retrieves the exact legal text from KSERC regulations relevant to the given topic.
        Uses Hybrid Search (BM25 + Chroma) and Parent-Child chunking.
        """
        logger.info(f"[LegalResearcher] Searching Hybrid RAG for: {topic}")
        
        # 1. Semantic Search (Child Chunks)
        vector_docs = self.vector_retriever.invoke(topic)
        vector_parent_ids = [doc.metadata.get("doc_id") for doc in vector_docs if "doc_id" in doc.metadata]
        
        # 2. Keyword Search (Parent Chunks)
        bm25_docs = self.bm25_retriever.invoke(topic)
        bm25_ids = [doc.metadata.get("doc_id") for doc in bm25_docs if "doc_id" in doc.metadata]
        
        # 3. Merge & Deduplicate
        unique_parent_ids = list(dict.fromkeys(vector_parent_ids + bm25_ids))
        
        if not unique_parent_ids:
            return "No relevant KSERC regulations found for this topic."
            
        # 4. Fetch Full Parent Contexts
        context = []
        for doc_id in unique_parent_ids:
            if doc_id in self.doc_store:
                parent_doc = self.doc_store[doc_id]
                source = parent_doc.metadata.get("source", "Unknown Document")
                page = parent_doc.metadata.get("page", "Unknown Page")
                context.append(f"--- Document: {source}, Page: {page} ---\n{parent_doc.page_content}\n")
            
        return "\n\n".join(context)

# Singleton instance to be used by the LangGraph agents
try:
    legal_researcher = LegalResearcher()
except Exception as e:
    logger.error(f"Failed to initialize LegalResearcher: {e}")
    legal_researcher = None

