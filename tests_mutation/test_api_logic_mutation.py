import sys
import os
# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

import pytest
import torch
from unittest.mock import MagicMock, patch, ANY
from fastapi.testclient import TestClient

# 1. Correct Import Path
# 2. Mock Heavy Libraries BEFORE import
with patch('api_rag.api_rag.AutoTokenizer'), \
     patch('api_rag.api_rag.AutoModel'), \
     patch('api_rag.api_rag.chromadb'), \
     patch('api_rag.api_rag.ChatGoogleGenerativeAI'):
    from api_rag.api_rag import app, RAGSystem

client = TestClient(app)

# ==============================================================================
# 1. ERROR HANDLING TRAPS (Startup Logic)
# ==============================================================================

@patch('api_rag.api_rag.rag_system', None) 
@patch('api_rag.api_rag.startup_error', "Init Failed")
def test_api_trap_startup_failure():
    """
    Trap: `if rag_system is None: raise`
    Mutant: `if rag_system is not None: raise`
    """
    response = client.post("/query", json={"query": "Test"})
    assert response.status_code == 500, "Mutant survived: Failed to catch uninitialized RAG system"
    assert "Init Failed" in response.json()["detail"]

# ==============================================================================
# 2. RETRIEVAL LOGIC & CONSTANT TRAPS
# ==============================================================================

def test_retrieve_k_chunks_trap():
    """
    Trap: `n_results=K_CHUNKS` (where K_CHUNKS=8)
    Mutant: Changes K_CHUNKS to 5, 10, or removes the argument.
    """
    rag = RAGSystem.__new__(RAGSystem)
    rag.tokenizer = MagicMock()
    rag.model = MagicMock()
    rag.collection = MagicMock()
    
    # Mock Embedder
    rag._embed_text = MagicMock(return_value=MagicMock(tolist=lambda: [[0.1]]))
    
    # Helper to mock the return of query so logic doesn't crash
    rag.collection.query.return_value = {
        "documents": [[]], "metadatas": [[]]
    }

    rag.retrieve("Query")
    
    # The Trap: We assert called_with to ensure K_CHUNKS was passed exactly as 8
    # If a mutant changes K_CHUNKS = 1, this assertion fails.
    rag.collection.query.assert_called_with(
        query_embeddings=ANY,
        n_results=8, # K_CHUNKS trap
        include=['documents', 'metadatas']
    )

def test_retrieve_formatting_trap():
    """
    Trap: Context string formatting logic `--- Act {act}...`
    """
    rag = RAGSystem.__new__(RAGSystem)
    rag.tokenizer = MagicMock()
    rag.model = MagicMock()
    rag.collection = MagicMock()
    rag._embed_text = MagicMock(return_value=MagicMock(tolist=lambda: [[0.1]]))
    
    # Mock DB Return
    rag.collection.query.return_value = {
        "documents": [["Chunk Text content"]],
        "metadatas": [[{"act": "1", "scene": "2", "speaker": "Cassius"}]]
    }

    context, sources = rag.retrieve("Query")
    
    assert "--- Act 1, Scene 2" in context, "Mutant survived: Formatting logic broken (Act/Scene missing)"
    assert "(Speaker: Cassius)" in context, "Mutant survived: Formatting logic broken (Speaker missing)"

# ==============================================================================
# 3. PIPELINE & CONFIGURATION TRAPS
# ==============================================================================

def test_llm_configuration_trap():
    """
    Trap: `temperature=0.0` inside _setup_llm
    Mutant: `temperature=1.0` or argument removed.
    """
    with patch('api_rag.api_rag.ChatGoogleGenerativeAI') as MockLLM:
        rag = RAGSystem.__new__(RAGSystem)
        rag._setup_llm()
        
        # The Trap: Ensure strict temperature control
        # If mutant removes this or changes to 0.7, test fails.
        _, kwargs = MockLLM.call_args
        assert kwargs.get('temperature') == 0.0, "Mutant survived: LLM Temperature logic changed"

def test_full_pipeline_flow_trap():
    """
    Trap: `answer = self.generate(context, query)`
    Mutant: `answer = context` (Bypass generation) or `answer = None`
    """
    rag = RAGSystem.__new__(RAGSystem)
    # Retrieve returns (Context, Sources)
    rag.retrieve = MagicMock(return_value=("Retrieved Context", ["Src"]))
    # Generate returns Answer
    rag.generate = MagicMock(return_value="Generated Answer")
    
    result = rag.full_pipeline("Query")
    
    # The Trap:
    # Original: Answer is "Generated Answer"
    # Mutant (Bypass): Answer might be "Retrieved Context" or None
    assert result['answer'] == "Generated Answer", "Mutant survived: Generation step bypassed or altered"
    rag.generate.assert_called_with("Retrieved Context", "Query")

# ==============================================================================
# 4. MATH TRAPS (Embedding)
# ==============================================================================

def test_embed_text_math_logic():
    """
    Trap: Mean pooling logic.
    """
    rag = RAGSystem.__new__(RAGSystem)
    rag.tokenizer = MagicMock()
    rag.model = MagicMock()
    rag.DEVICE = "cpu"

    # Mock Tensors: 1 Batch, 2 Tokens, 2 Dim
    # Token 1: [1.0, 2.0], Token 2: [3.0, 4.0]
    mock_out = MagicMock()
    mock_out.last_hidden_state = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]]) 
    
    rag.model.return_value = mock_out
    rag.tokenizer.return_value = {"attention_mask": torch.tensor([[1, 1]])} 

    vector = rag._embed_text("Test")
    
    # Expected: Mean of [1,2] and [3,4] -> [2.0, 3.0]
    assert vector.shape == (2,), "Mutant survived: Wrong output shape"
    assert vector[0] == 2.0, "Mutant survived: Math logic error (First dim)"
    assert vector[1] == 3.0, "Mutant survived: Math logic error (Second dim)"