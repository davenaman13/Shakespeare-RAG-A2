import sys
import os
import pytest
from unittest.mock import MagicMock, patch, ANY
from fastapi.testclient import TestClient

# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

# 1. MOCK HEAVY DEPENDENCIES BEFORE IMPORT
# We patch sys.modules to prevent the actual import of heavy libraries
# This ensures the tests run fast and don't download models
mock_torch = MagicMock()
mock_torch.cuda.is_available.return_value = False
sys.modules["torch"] = mock_torch
sys.modules["chromadb"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()

# Now we can import the module safely
# We use patch.dict to ensure GEMINI_API_KEY exists so the module-level check passes
with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
    from api_rag.api_rag import app, RAGSystem, QueryRequest

client = TestClient(app)

# ==============================================================================
# 1. RAG SYSTEM INITIALIZATION TESTS
# ==============================================================================

def test_rag_system_init_success():
    """
    Unit: Verifies that __init__ calls all loading methods correctly.
    """
    with patch.object(RAGSystem, '_load_embedding_model') as mock_load_emb, \
         patch.object(RAGSystem, '_load_vector_store') as mock_load_vec, \
         patch.object(RAGSystem, '_setup_llm') as mock_setup:
        
        system = RAGSystem()
        
        mock_load_emb.assert_called_once()
        mock_load_vec.assert_called_once()
        mock_setup.assert_called_once()

def test_load_embedding_model_failure():
    """
    Unit: Ensures RuntimeError is raised if Tokenizer/Model fails to load.
    """
    # Create system but bypass __init__
    system = RAGSystem.__new__(RAGSystem)
    
    with patch('api_rag.api_rag.AutoTokenizer') as mock_tok:
        mock_tok.from_pretrained.side_effect = Exception("Download failed")
        
        with pytest.raises(RuntimeError) as exc:
            system._load_embedding_model()
        assert "Failed to load embedding model" in str(exc.value)

# ==============================================================================
# 2. EMBEDDING & MATH LOGIC TESTS
# ==============================================================================

def test_embed_text_logic():
    """
    Unit: Tests the mean pooling logic (tensor operations) via mocks.
    """
    system = RAGSystem.__new__(RAGSystem)
    system.tokenizer = MagicMock()
    system.model = MagicMock()
    system.DEVICE = "cpu" # Force CPU for test logic

    # Mock Tokenizer Output
    # Returns a dict with 'input_ids' and 'attention_mask'
    system.tokenizer.return_value = {
        "attention_mask": MagicMock()
    }
    
    # Mock Model Output
    mock_model_output = MagicMock()
    mock_model_output.last_hidden_state = MagicMock()
    # Simulate size() call for expansion
    mock_model_output.last_hidden_state.size.return_value = (1, 5, 768) 
    system.model.return_value = mock_model_output
    
    # Execute
    # We mock the tensor math operations because we mocked 'torch' at the top
    # This verifies the sequence of calls: model() -> last_hidden_state -> sum -> div
    
    with patch('api_rag.api_rag.torch') as patch_torch:
        # We need to allow the context manager 'with torch.no_grad()'
        patch_torch.no_grad.return_value.__enter__.return_value = None
        
        result = system._embed_text("Query")
        
        # Verify model was called
        system.model.assert_called_once()
        # Verify result is numpy (cpu().numpy() is called at end)
        assert result is not None

# ==============================================================================
# 3. RETRIEVAL LOGIC TESTS
# ==============================================================================

def test_retrieve_formatting_logic():
    """
    Unit: Verifies that retrieval combines chunks into the specific string format required.
    """
    system = RAGSystem.__new__(RAGSystem)
    system._embed_text = MagicMock(return_value=MagicMock(tolist=lambda: [[0.1, 0.2]]))
    
    # Mock Collection Query Response
    system.collection = MagicMock()
    system.collection.query.return_value = {
        "documents": [["Chunk Text 1", "Chunk Text 2"]],
        "metadatas": [[
            {"act": 1, "scene": 1, "speaker": "Brutus"},
            {"act": 3, "scene": 2, "speaker": "Antony"}
        ]]
    }
    
    context, sources = system.retrieve("Test Query")
    
    # Verify String Formatting
    assert "--- Act 1, Scene 1 (Speaker: Brutus) ---" in context
    assert "Chunk Text 1" in context
    assert "--- Act 3, Scene 2 (Speaker: Antony) ---" in context
    
    # Verify Source List Structure
    assert len(sources) == 2
    assert sources[0]['metadata']['speaker'] == "Brutus"

# ==============================================================================
# 4. GENERATION & PIPELINE TESTS
# ==============================================================================

def test_generate_chain_invocation():
    """
    Unit: Ensures the LangChain pipeline is invoked with correct keys.
    """
    system = RAGSystem.__new__(RAGSystem)
    system.prompt = MagicMock()
    system.llm = MagicMock()
    
    # Mock the pipe operator behavior: chain = prompt | llm
    mock_chain = MagicMock()
    # When prompt | llm happens, return mock_chain
    system.prompt.__or__.return_value = mock_chain
    
    mock_chain.invoke.return_value = MagicMock(content="Final Answer")
    
    answer = system.generate("Context string", "User Question")
    
    # Assert invoke called with correct dict
    mock_chain.invoke.assert_called_with({
        "context": "Context string",
        "question": "User Question"
    })
    assert answer == "Final Answer"

def test_full_pipeline_integration():
    """
    Unit: Verifies data flow from Retrieve -> Generate -> Return.
    """
    system = RAGSystem.__new__(RAGSystem)
    system.retrieve = MagicMock(return_value=("Ctx", ["Src1"]))
    system.generate = MagicMock(return_value="Ans")
    
    result = system.full_pipeline("Q")
    
    assert result == {"answer": "Ans", "sources": ["Src1"]}
    system.retrieve.assert_called_with("Q")
    system.generate.assert_called_with("Ctx", "Q")

# ==============================================================================
# 5. API ENDPOINT TESTS (FastAPI)
# ==============================================================================

def test_read_root():
    """
    Unit: GET / sanity check.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Shakespearean Scholar" in response.json()["status"]

@patch('api_rag.api_rag.rag_system')
def test_query_endpoint_success(mock_rag):
    """
    Unit: POST /query success path.
    """
    mock_rag.full_pipeline.return_value = {"answer": "Ok", "sources": []}
    
    response = client.post("/query", json={"query": "Hello"})
    
    assert response.status_code == 200
    assert response.json()["answer"] == "Ok"

@patch('api_rag.api_rag.rag_system', None)
@patch('api_rag.api_rag.startup_error', "GPU Error", create=True)
def test_query_endpoint_init_failure():
    """
    Unit: POST /query when RAG system failed to start.
    """
    response = client.post("/query", json={"query": "Hello"})
    
    assert response.status_code == 500
    assert "RAG System failed to initialize" in response.json()["detail"]
    assert "GPU Error" in response.json()["detail"]

@patch('api_rag.api_rag.rag_system')
def test_query_endpoint_processing_exception(mock_rag):
    """
    Unit: POST /query when pipeline raises an exception.
    """
    mock_rag.full_pipeline.side_effect = ValueError("Token limit exceeded")
    
    response = client.post("/query", json={"query": "Hello"})
    
    assert response.status_code == 500
    assert "Token limit exceeded" in response.json()["detail"]