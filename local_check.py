import torch
import numpy as np
import chromadb
from transformers import AutoTokenizer, AutoModel
from pathlib import Path

# --- Configuration (Must match your Kaggle setup) ---
MODEL_NAME = "BAAI/bge-base-en-v1.5"
PERSIST_DIR = Path("./chroma_db") # The folder where Chroma persisted the index
COLLECTION_NAME = "julius_caesar"
# ----------------------------------------------------

# Set device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

# Load tokenizer & model
print(f"Loading embedding model: {MODEL_NAME}...")
try:
    # Use BgeTokenizer or a standard AutoTokenizer if BAAI/bge-base-en-v1.5 is already downloaded
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True).to(DEVICE)
    model.eval()
except Exception as e:
    print(f"Error loading model: {e}")
    print("Please ensure 'transformers', 'sentence-transformers' and 'torch' are installed.")
    exit()

def embed_text(txt):
    """Generates the query embedding using the BGE model and mean pooling."""
    enc = tokenizer([txt], padding=True, truncation=True, max_length=1024, return_tensors="pt")
    enc = {k: v.to(DEVICE) for k, v in enc.items()}
    with torch.no_grad():
        out = model(**enc, return_dict=True)
        # BGE-style Mean Pooling
        mask = enc["attention_mask"].unsqueeze(-1).expand(out.last_hidden_state.size()).float()
        pooled = (out.last_hidden_state * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
    return pooled.cpu().numpy()

# --- ChromaDB Interaction ---
print(f"Attempting to connect to ChromaDB at: {PERSIST_DIR.resolve()}...")
try:
    client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    col = client.get_collection(COLLECTION_NAME)
    print(f"Successfully loaded collection '{COLLECTION_NAME}' with {col.count()} documents.")
except Exception as e:
    print(f"Error loading ChromaDB: {e}")
    print("Ensure the 'chroma_db' folder exists and has all persisted files.")
    exit()

# Embed and query
query = "What does Calpurnia dream about the assassination of Caesar?"
print(f"\n--- Running Sample Query: '{query}' ---")
q_emb = embed_text(query)

res = col.query(
    query_embeddings=[q_emb.tolist()[0]],
    n_results=3,
    include=['documents', 'metadatas', 'distances']
)

# Display results
for i, (doc, meta, dist) in enumerate(zip(res["documents"][0], res["metadatas"][0], res["distances"][0])):
    print(f"\n===== Result {i+1} (Distance: {dist:.4f}) =====")
    print(f"Metadata: Act {meta['act']}, Scene {meta['scene']}, Speaker: {meta['speaker']}, ID: {meta['chunk_id']}")
    print(f"Text Snippet: {doc[:350].replace('\n', ' ')}...")
    print("...")