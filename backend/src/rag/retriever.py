import os
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_community.vectorstores import Chroma
from langchain_google_vertexai import VertexAIEmbeddings
import vertexai

load_dotenv()
logger = logging.getLogger("rag_retriever")

BACKEND_DIR = Path(__file__).resolve().parents[2]
GLOBAL_DB_DIR = str(BACKEND_DIR / "data" / "precedent_db" / "global_chroma")
LICENSEE_DB_BASE = BACKEND_DIR / "data" / "licensee_vaults"

class LegalResearcher:
    def __init__(self, licensee_id: str = "global"):
        self.licensee_id = licensee_id
        key_path = os.path.abspath("vertex_sa.json")
        if not os.path.exists(key_path):
            logger.error("vertex_sa.json not found! LegalResearcher fallback to mock.")
            self.embeddings = None
            return
            
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        vertexai.init(project="triple-cab-488111-f5", location="us-central1")
        
        self.embeddings = VertexAIEmbeddings(model_name="text-embedding-004")
        
        # Paths for Global Store
        self.global_db = None
        if os.path.exists(GLOBAL_DB_DIR):
            self.global_db = Chroma(persist_directory=GLOBAL_DB_DIR, embedding_function=self.embeddings)
            
        # Paths for Licensee Vault
        self.licensee_db = None
        licensee_path = str(LICENSEE_DB_BASE / licensee_id)
        if licensee_id != "global" and os.path.exists(licensee_path):
            self.licensee_db = Chroma(persist_directory=licensee_path, embedding_function=self.embeddings)

    def search_regulations(self, query: str) -> str:
        if not self.embeddings:
            return "Knowledge Engine Offline: vertex_sa.json missing."
            
        results = []
        
        # 1. Search Licensee Vault (Precedents / Past Reasoning)
        if self.licensee_db:
            l_docs = self.licensee_db.similarity_search(query, k=2)
            if l_docs:
                results.append("### PAST LICENSEE PRECEDENTS / REASONING")
                for doc in l_docs:
                    results.append(f"[{doc.metadata.get('source', 'Historical')}] {doc.page_content}")

        # 2. Search Global Regulatory Store (Tariff Orders / Rules)
        if self.global_db:
            g_docs = self.global_db.similarity_search(query, k=3)
            if g_docs:
                results.append("### KSERC GLOBAL REGULATIONS / TARIFF ORDERS")
                for doc in g_docs:
                    results.append(f"[{doc.metadata.get('source', 'Regulation')}] {doc.page_content}")
                    
        return "\n\n".join(results) if results else "No specific regulations or precedents found for this query."

    def store_reasoning(self, item: str, reasoning: str):
        """Saves final AI reasoning into the licensee vault for future semantic retrieval."""
        if not self.embeddings: return
        
        licensee_path = str(LICENSEE_DB_BASE / self.licensee_id)
        db = Chroma(persist_directory=licensee_path, embedding_function=self.embeddings)
        
        from langchain_core.documents import Document
        doc = Document(
            page_content=reasoning,
            metadata={
                "source": "AI_AUDIT_HISTORY",
                "item": item,
                "licensee_id": self.licensee_id,
                "type": "reasoning_semantic"
            }
        )
        db.add_documents([doc])
        logger.info(f"Stored reasoning semantic for {item} in {self.licensee_id} vault.")


    def search(self, topic: str) -> str:
        """Legacy search interface redirected to new segmented search."""
        return self.search_regulations(topic)

# Singleton factory for agents
def get_researcher(licensee_id: str = "global") -> LegalResearcher:
    try:
        return LegalResearcher(licensee_id=licensee_id)
    except Exception as e:
        logger.error(f"Failed to initialize researcher for {licensee_id}: {e}")
        return None

