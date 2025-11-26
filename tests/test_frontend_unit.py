import sys
import os
# --- PATH FIX: Add parent directory so Python finds frontend_ui ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ------------------------------------------------------------------

import pytest
import requests
from unittest.mock import MagicMock, patch, call
import sys

# 1. Mock Streamlit BEFORE importing frontend
# We use a MagicMock so we can track calls like st.title(), st.error()
mock_st = MagicMock()
sys.modules['streamlit'] = mock_st

# 2. Correct Import
from frontend_ui.frontend import query_rag_api, main

# Fixture to clean up mock state between tests
@pytest.fixture(autouse=True)
def reset_st_mock():
    mock_st.reset_mock()

# ==============================================================================
# 1. LOGIC FUNCTION TESTS (query_rag_api)
# ==============================================================================

def test_query_rag_api_success():
    """Unit: Ensure correct JSON is returned on 200 OK."""
    with patch('requests.post') as mock_post:
        # Setup successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Success", "sources": []}
        mock_post.return_value = mock_response
        
        # Execute
        result = query_rag_api("Hello", "http://fake-url")
        
        # Assertions
        assert result["answer"] == "Success"
        # Verify exact arguments passed to requests (Payload check)
        mock_post.assert_called_once_with(
            "http://fake-url", 
            json={"query": "Hello"}, 
            timeout=90
        )

def test_query_rag_api_empty_input():
    """Unit: Ensure empty input returns None immediately (saves API calls)."""
    with patch('requests.post') as mock_post:
        result = query_rag_api("", "http://fake-url")
        assert result is None
        mock_post.assert_not_called()

def test_query_rag_api_http_error():
    """Unit: Ensure HTTP errors (404/500) are re-raised properly."""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        # Simulate raise_for_status() behavior
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Internal Error")
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            query_rag_api("Crash", "http://fake-url")

def test_query_rag_api_connection_error():
    """Unit: Ensure connection errors (No Internet) propagate."""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("DNS Failure")
        
        with pytest.raises(requests.exceptions.ConnectionError):
            query_rag_api("Crash", "http://fake-url")

# ==============================================================================
# 2. UI FLOW TESTS (main)
# ==============================================================================

def test_main_initial_render():
    """Unit: Ensure static UI elements (Title, Input) render on startup."""
    # Setup: Button NOT clicked
    mock_st.button.return_value = False
    
    main()
    
    mock_st.set_page_config.assert_called()
    mock_st.title.assert_called_with("🎓 The Shakespearean Scholar")
    mock_st.text_input.assert_called()
    # API should NOT be called
    mock_st.spinner.assert_not_called()

def test_main_empty_question_warning():
    """Unit: Ensure warning is shown if button clicked but text is empty."""
    mock_st.text_input.return_value = ""
    mock_st.button.return_value = True # Clicked
    
    main()
    
    mock_st.warning.assert_called_with("Please enter a question.")
    # Ensure we didn't try to hit the API
    with patch('frontend_ui.frontend.query_rag_api') as mock_api:
        main() 
        mock_api.assert_not_called()

@patch('frontend_ui.frontend.query_rag_api')
def test_main_success_flow_with_sources(mock_api):
    """Unit: Full Happy Path - Question -> API -> Answer + Sources Display."""
    # Setup UI Inputs
    mock_st.text_input.return_value = "Valid Question"
    mock_st.button.return_value = True
    
    # Setup API Data
    mock_api.return_value = {
        "answer": "Et tu, Brute?",
        "sources": [
            {"chunk": "Chunk Text", "metadata": {"act": 3, "scene": 1}}
        ]
    }
    
    main()
    
    # Assert Spinner Usage
    mock_st.spinner.assert_called()
    
    # Assert Answer Display
    mock_st.subheader.assert_any_call("Scholar's Answer")
    mock_st.markdown.assert_any_call("Et tu, Brute?")
    
    # Assert Source Rendering
    mock_st.subheader.assert_any_call("Textual Evidence (Sources)")
    mock_st.expander.assert_called_with("Source 1: Act 3, Scene 1")
    mock_st.text.assert_called_with("Chunk Text")

@patch('frontend_ui.frontend.query_rag_api')
def test_main_success_flow_no_sources(mock_api):
    """Unit: Happy Path but NO sources found (should skip expander)."""
    mock_st.text_input.return_value = "Valid Question"
    mock_st.button.return_value = True
    
    mock_api.return_value = {
        "answer": "Just an answer.",
        "sources": [] # Empty list
    }
    
    main()
    
    mock_st.markdown.assert_any_call("Just an answer.")
    # Expander should NOT be called if sources list is empty
    mock_st.expander.assert_not_called()

@patch('frontend_ui.frontend.query_rag_api')
def test_main_handle_http_error(mock_api):
    """Unit: Ensure API HTTP errors are caught and displayed as st.error."""
    mock_st.text_input.return_value = "Valid Question"
    mock_st.button.return_value = True
    
    mock_api.side_effect = requests.exceptions.HTTPError("404 Not Found")
    
    main()
    
    # Verify st.error was called with the exception message
    args, _ = mock_st.error.call_args
    assert "API Error" in args[0]
    assert "404 Not Found" in args[0]

@patch('frontend_ui.frontend.query_rag_api')
def test_main_handle_generic_error(mock_api):
    """Unit: Ensure unexpected crashes are caught safely."""
    mock_st.text_input.return_value = "Valid Question"
    mock_st.button.return_value = True
    
    mock_api.side_effect = Exception("Random Crash")
    
    main()
    
    args, _ = mock_st.error.call_args
    assert "An unexpected error occurred" in args[0]
    assert "Random Crash" in args[0]