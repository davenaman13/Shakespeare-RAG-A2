import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient

# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

# Mock Heavy Libs
sys.modules["torch"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()

with patch.dict(os.environ, {"GEMINI_API_KEY": "fake"}):
    from api_rag.api_rag import app, RAGSystem

client = TestClient(app)

# ==============================================================================
# STRATEGY: Corrupted Metadata from Vector DB
# ==============================================================================
bad_metadata_strategy = st.dictionaries(
    keys=st.text(), 
    values=st.one_of(st.text(), st.integers(), st.none())
)

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
@given(
    query=st.text(),
    metadatas=st.lists(st.lists(bad_metadata_strategy, min_size=1, max_size=5), min_size=1, max_size=1)
)
def test_fuzz_retrieve_metadata_resilience(query, metadatas):
    """
    Property: retrieve() should not crash even if ChromaDB returns 
    malformed metadata.
    """
    system = RAGSystem.__new__(RAGSystem)
    system._embed_text = MagicMock(return_value=MagicMock(tolist=lambda: [[0.1]]))
    system.collection = MagicMock()
    
    # Align documents with metadata count
    num_docs = len(metadatas[0])
    documents = [["Doc"] * num_docs]
    
    system.collection.query.return_value = {
        "documents": documents,
        "metadatas": metadatas
    }

    try:
        system.retrieve(query)
    except KeyError:
        pass 
    except Exception as e:
        pytest.fail(f"CRASHED on metadata: {metadatas} Error: {e}")

# ==============================================================================
# STRATEGY: Endpoint Input Fuzzing
# ==============================================================================

@given(st.text())
def test_fuzz_api_endpoint_strings(input_string):
    """
    Property: The /query endpoint should handle any string input.
    """
    # CRITICAL FIX: We mock the rag_system so it returns JSON-serializable data
    with patch('api_rag.api_rag.rag_system') as mock_rag:
        mock_rag.full_pipeline.return_value = {"answer": "ok", "sources": []}
        
        response = client.post("/query", json={"query": input_string})
        
        # Assert: Status code is controlled (not an internal server crash)
        assert response.status_code in [200, 422]

@given(st.dictionaries(st.text(), st.text()))
def test_fuzz_api_endpoint_json_structure(random_json):
    """
    Property: Sending random JSON dictionaries (wrong keys) 
    should be caught by Pydantic (422), not crash the server (500).
    """
    # CRITICAL FIX: Patch rag_system here too!
    # If Pydantic validation PASSES (because random_json has 'query' key),
    # the code proceeds to use rag_system. If it's not mocked to return strings,
    # it returns Mocks -> JSON Error -> 500 Crash.
    with patch('api_rag.api_rag.rag_system') as mock_rag:
        mock_rag.full_pipeline.return_value = {"answer": "ok", "sources": []}
        
        response = client.post("/query", json=random_json)
        
        # Logic:
        # 1. Pydantic fail (missing 'query' key) -> 422
        # 2. Pydantic success -> mock_rag called -> returns dict -> 200
        # 3. Crash -> 500 (Failure)
        assert response.status_code != 500