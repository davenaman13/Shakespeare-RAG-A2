import sys
import os
# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

import pytest
import requests
from unittest.mock import MagicMock, patch
import sys

# Mock Streamlit BEFORE importing frontend
sys.modules['streamlit'] = MagicMock()
import streamlit as st
# Correct Import: frontend_ui.frontend
from frontend_ui.frontend import query_rag_api, main

def test_query_rag_api_success():
    """Unit: Ensure correct JSON is returned on 200 OK."""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Success"}
        mock_post.return_value = mock_response
        
        result = query_rag_api("Hello", "http://fake-url")
        assert result["answer"] == "Success"

def test_main_layout_calls():
    """Unit: Ensure title and text input are rendered."""
    main()
    st.title.assert_called_with("🎓 The Shakespearean Scholar")
    st.text_input.assert_called()