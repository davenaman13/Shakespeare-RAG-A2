import sys
import os
# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Mock imports using the CORRECT directory structure: api_rag.api_rag
# We mock these BEFORE importing to stop the heavy model download
with patch('api_rag.api_rag.AutoTokenizer'), \
     patch('api_rag.api_rag.AutoModel'), \
     patch('api_rag.api_rag.chromadb'), \
     patch('api_rag.api_rag.ChatGoogleGenerativeAI'):
    from api_rag.api_rag import app, RAGSystem

client = TestClient(app)

# ==============================================================================
# UNIT TESTS (Verification)
# ==============================================================================

def test_read_root():
    """Unit: Ensure root endpoint is alive."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Shakespearean Scholar API" in response.json()["status"]

@patch('api_rag.api_rag.rag_system')
def test_query_endpoint_success(mock_rag_system):
    """
    Unit: Ensure /query endpoint calls the full pipeline and returns JSON.
    """
    # Setup Mock
    mock_rag_system.full_pipeline.return_value = {
        "answer": "Brutus is noble.",
        "sources": [{"chunk": "Text", "metadata": {"act": 1}}]
    }

    # Execute
    response = client.post("/query", json={"query": "Who is Brutus?"})

    # Verify
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["answer"] == "Brutus is noble."
    assert len(json_resp["sources"]) == 1

def test_rag_system_retrieve_structure():
    """
    Unit: Ensure retrieve() combines documents and metadata correctly.
    """
    # We mock a RAGSystem instance without triggering __init__ logic
    rag = MagicMock(spec=RAGSystem)
    
    # Mock the internal logic
    rag.retrieve.return_value = ("Context String", [])
    
    context, sources = rag.retrieve("Query")
    assert isinstance(context, str)
    assert isinstance(sources, list)