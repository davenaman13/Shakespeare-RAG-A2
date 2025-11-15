import os
import chromadb
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np

# Load environment variables from .env file (one level up)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# --- Configuration ---
# PATH: Assumes chroma_db is in the parent directory (AdvNLP_Assignment2)
PERSIST_DIR = "/app/chroma_db"
COLLECTION_NAME = "julius_caesar"
MODEL_NAME = "BAAI/bge-base-en-v1.5" # Your chosen embedding model
GENERATION_MODEL = "gemini-2.5-flash"
K_CHUNKS = 8 # Number of chunks to retrieve
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Check for API Key
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY not found. Please check your .env file.")

# --- RAG Components ---
class RAGSystem:
    def __init__(self):
        print("Initializing RAG System...")
        self._load_embedding_model()
        self._load_vector_store()
        self._setup_llm()
        print(f"RAG System initialized. Using device: {DEVICE}")

    def _load_embedding_model(self):
        """Load BGE embedding model for query embedding."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
            self.model = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True).to(DEVICE)
            self.model.eval()
        except Exception as e:
            raise RuntimeError(f"Failed to load embedding model: {e}")

    def _load_vector_store(self):
        """Load Chroma PersistentClient."""
        try:
            client = chromadb.PersistentClient(path=PERSIST_DIR)
            self.collection = client.get_collection(COLLECTION_NAME)
            print(f"Loaded Chroma collection with {self.collection.count()} documents.")
        except Exception as e:
            raise RuntimeError(f"Failed to load ChromaDB from {PERSIST_DIR}: {e}")

    def _setup_llm(self):
        """Setup LangChain LLM and System Prompt (Phase 4)."""
        # --- Phase 4: System Prompt (Critical) ---
        SYSTEM_PROMPT = (
            "You are an **Expert Shakespearean Scholar** specializing in William Shakespeare's "
            "The Tragedy of Julius Caesar. Your target audience is an ICSE Class 10 student. "
            "Your answer must be insightful, academically rigorous, clear, and based **ONLY** on the context provided below. "
            
            "**CRITICAL INSTRUCTION FOR ACCURACY:** Before synthesizing the final answer, you must carefully read and evaluate all retrieved chunks. "
            "You must first identify and prioritize the 3-5 source chunks that contain the most **direct quotes or factual evidence** needed to answer the question. "
            "**Ignore** any retrieved context that is purely descriptive, repetitive, or irrelevant stage direction. "
            
            "You must try your best to construct an answer by combining details from the prioritized sources. "
            "You **MUST** only abstain from answering if the context contains absolutely no relevant factual evidence. "
            "You must cite textual evidence by including the full text of the relevant source chunk(s) at the end of your response, formatted as instructed."
        )

        HUMAN_PROMPT = (
            "CONTEXT:\n{context}\n\n"
            "QUESTION: {question}"
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ])
        
        # Initialize LangChain LLM using the key from .env
        self.llm = ChatGoogleGenerativeAI(
            model=GENERATION_MODEL, 
            temperature=0.0 # Keep temperature low for factual RAG
        )
        
    def _embed_text(self, txt):
        """Generates the query embedding using the BGE model and mean pooling."""
        enc = self.tokenizer([txt], padding=True, truncation=True, max_length=1024, return_tensors="pt")
        enc = {k: v.to(DEVICE) for k, v in enc.items()}
        with torch.no_grad():
            out = self.model(**enc, return_dict=True)
            # BGE-style Mean Pooling
            mask = enc["attention_mask"].unsqueeze(-1).expand(out.last_hidden_state.size()).float()
            pooled = (out.last_hidden_state * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        return pooled.cpu().numpy()

    def retrieve(self, query: str):
        """Embeds query and retrieves top-k chunks from Chroma."""
        q_emb = self._embed_text(query)
        res = self.collection.query(
            query_embeddings=[q_emb.tolist()[0]],
            n_results=K_CHUNKS,
            include=['documents', 'metadatas']
        )
        # Combine results into structured format
        sources = []
        context_text = []
        for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
            sources.append({"chunk": doc, "metadata": meta})
            # Format context for the LLM
            context_text.append(f"--- Act {meta['act']}, Scene {meta['scene']} (Speaker: {meta['speaker']}) ---\n{doc}\n")
        
        return "\n".join(context_text), sources

    def generate(self, context: str, question: str):
        """Calls the LLM to generate the final answer."""
        chain = self.prompt | self.llm 
        
        response = chain.invoke({
            "context": context,
            "question": question
        })
        
        return response.content

    def full_pipeline(self, query: str):
        """Runs the full RAG pipeline."""
        context, sources = self.retrieve(query)
        answer = self.generate(context, query)
        
        # Phase 3: Response Body structure
        return {"answer": answer, "sources": sources}

# --- FastAPI App Setup ---
app = FastAPI(title="The Shakespearean Scholar RAG API")
# Initialize RAG System when the app starts
try:
    rag_system = RAGSystem()
except Exception as e:
    # If RAGSystem initialization fails (e.g., Chroma error), we'll raise an error later
    # but keep the app defined to be able to run uvicorn
    rag_system = None
    startup_error = str(e)


class QueryRequest(BaseModel):
    query: str


@app.get("/")
def read_root():
    """Returns a simple message confirming the API is running."""
    return {"status": "Shakespearean Scholar API is running", "docs_link": "/docs"}

# Phase 3: POST /query Endpoint
@app.post("/query")
async def query_rag_system(request: QueryRequest):
    """
    Submits a question to the Shakespearean Scholar RAG system.
    """
    if rag_system is None:
        raise HTTPException(status_code=500, detail=f"RAG System failed to initialize: {startup_error}")
    try:
        result = rag_system.full_pipeline(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))