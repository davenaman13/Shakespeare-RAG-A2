import sys
import os
# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

import pytest
import requests
from unittest.mock import MagicMock, patch
import sys

# 1. Mock Streamlit BEFORE import
sys.modules['streamlit'] = MagicMock()
import streamlit as st

# 2. Correct Import from frontend_ui/frontend.py
from frontend_ui.frontend import query_rag_api, main

# ==============================================================================
# 1. API WRAPPER TRAPS (query_rag_api)
# ==============================================================================

def test_query_api_logic_inversion_trap():
    """
    Target: `if not user_query: return None`
    Mutant: `if user_query: return None` (Logic Inversion via 'not' removal)
    or `if True: return None` (Force exit)
    """
    with patch('requests.post') as mock_post:
        # Setup success
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {}
        
        # Input: Valid string
        result = query_rag_api("Valid Query", "http://url")
        
        # Trap: If logic is inverted, it returns None instead of calling API
        assert result is not None, "Mutant survived: Valid query blocked by logic inversion"

def test_api_timeout_trap():
    """
    Target: `requests.post(..., timeout=90)`
    Mutant: Argument `timeout` removed.
    """
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        query_rag_api("Test", "http://url")
        
        # Trap: Check kwargs for timeout
        args, kwargs = mock_post.call_args
        assert 'timeout' in kwargs, "Mutant survived: Timeout argument removed"
        assert kwargs['timeout'] == 90, "Mutant survived: Timeout value changed"

# ==============================================================================
# 2. UI LOGIC TRAPS (main)
# ==============================================================================

def test_main_button_bypass_trap():
    """
    Target: `if st.button(...):`
    Mutant: `if True:` (Forces logic to run without click)
    """
    # Setup: Button returns FALSE (Not clicked)
    st.button.return_value = False
    st.text_input.return_value = "Valid Question"
    
    with patch('frontend_ui.frontend.query_rag_api') as mock_query:
        main()
        
        # Trap: The API should NOT be called.
        # If mutant changes `if button` to `if True`, this fails.
        mock_query.assert_not_called(), "Mutant survived: Logic ran without button click (Flow Control Break)"

def test_main_validation_inversion_trap():
    """
    Target: `if not question: st.warning`
    Mutant: `if question: st.warning` (Logic Inversion)
    """
    # Setup: Button Clicked, Question Exists
    st.button.return_value = True
    st.text_input.return_value = "Valid Question"
    
    with patch('frontend_ui.frontend.query_rag_api') as mock_query:
        main()
        
        # Trap: Should call API.
        # If mutant inverts logic, it shows warning and skips API.
        mock_query.assert_called(), "Mutant survived: Valid question triggered warning"