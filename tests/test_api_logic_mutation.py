import sys
import os
# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

import pytest
import torch
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# 1. Correct Import Path: We import from 'api_rag' folder, not 'julius_etl'
# 2. Mock Heavy Libraries: We prevent PyTorch/Chroma from loading during tests
with patch('api_rag.api_rag.AutoTokenizer'), \
     patch('api_rag.api_rag.AutoModel'), \
     patch('api_rag.api_rag.chromadb'), \
     patch('api_rag.api_rag.ChatGoogleGenerativeAI'):
    from api_rag.api_rag import app, RAGSystem

client = TestClient(app)

# ==============================================================================
# 1. ERROR HANDLING TRAPS (Kills 'if x is None' -> 'if x is not None')
# ==============================================================================

@patch('api_rag.api_rag.rag_system', None) # Force System to be None
@patch('api_rag.api_rag.startup_error', "Init Failed")
def test_api_trap_startup_failure():
    """
    Trap: The code says `if rag_system is None: raise HTTPException`.
    Mutant: `if rag_system is NOT None: raise` (Logic Inversion).
    """
    # Action: Call the endpoint
    response = client.post("/query", json={"query": "Test"})
    
    # Trap: Original logic MUST raise 500 if system is None.
    # A mutant that flips this logic will return 200 OK or crash differently.
    assert response.status_code == 500, "Mutant survived: Failed to catch uninitialized RAG system"
    assert "Init Failed" in response.json()["detail"]

# ==============================================================================
# 2. FORMATTING TRAPS (Kills String Logic Mutants)
# ==============================================================================

def test_retrieve_formatting_trap():
    """
    Trap: The loop formats context as `--- Act {act}, Scene {scene} ...`.
    Mutant: Might drop the `---` or the `Act` keyword or change logic order.
    """
    # Create instance without calling __init__ (avoids loading models)
    rag = RAGSystem.__new__(RAGSystem)
    rag.tokenizer = MagicMock()
    rag.model = MagicMock()
    
    # Mock Collection Query Result (Simulating ChromaDB response)
    rag.collection = MagicMock()
    # Logic requires matching lists of documents and metadatas
    rag.collection.query.return_value = {
        "documents": [["Chunk Text content"]],
        "metadatas": [[{"act": "1", "scene": "2", "speaker": "Cassius"}]]
    }
    
    # Mock Embedder to return dummy array (skips math)
    rag._embed_text = MagicMock(return_value=MagicMock(tolist=lambda: [[0.1]]))

    # Call the method directly
    context, sources = rag.retrieve("Query")
    
    # The Trap: Verify specific string formatting logic
    assert "--- Act 1, Scene 2" in context, "Mutant survived: Formatting logic broken (Act/Scene missing)"
    assert "(Speaker: Cassius)" in context, "Mutant survived: Formatting logic broken (Speaker missing)"
    assert len(sources) == 1

# ==============================================================================
# 3. MATH TRAPS (Kills Pytorch/Math mutants)
# ==============================================================================

def test_embed_text_math_logic():
    """
    Trap: _embed_text uses mean pooling: (hidden * mask).sum(1) / mask.sum(1)
    Mutants: Change * to +, sum(1) to sum(0), division to multiplication.
    """
    rag = RAGSystem.__new__(RAGSystem)
    rag.tokenizer = MagicMock()
    rag.model = MagicMock()
    rag.DEVICE = "cpu"

    # Setup Mock Tensors
    # Shape: Batch=1, Tokens=2, Dim=2
    # Token 1: [1.0, 2.0]
    # Token 2: [3.0, 4.0]
    mock_out = MagicMock()
    mock_out.last_hidden_state = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]]) 
    
    rag.model.return_value = mock_out
    # Mask: Both tokens are valid (1, 1)
    rag.tokenizer.return_value = {"attention_mask": torch.tensor([[1, 1]])} 

    # Execute
    # Expected Math: Mean of [1,2] and [3,4]
    # Token 1 + Token 2 = [4.0, 6.0]
    # Divide by 2 = [2.0, 3.0]
    vector = rag._embed_text("Test")
    
    # Assertions
    assert vector.shape == (2,), "Mutant survived: Wrong output shape"
    assert vector[0] == 2.0, "Mutant survived: Math logic error (First dimension mean wrong)"
    assert vector[1] == 3.0, "Mutant survived: Math logic error (Second dimension mean wrong)"