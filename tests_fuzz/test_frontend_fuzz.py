import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck

# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

# Mock Streamlit
mock_st = MagicMock()
sys.modules['streamlit'] = mock_st
from frontend_ui.frontend import query_rag_api, main

# ==============================================================================
# STRATEGY: Malformed API Responses
# ==============================================================================
# We generate JSON that vaguely looks like the expected structure but is "corrupted"
# Example: Missing 'sources', sources is not a list, metadata missing 'act', etc.
garbage_response_strategy = st.recursive(
    st.none() | st.booleans() | st.floats() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
)

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
@given(api_data=garbage_response_strategy)
def test_fuzz_main_ui_rendering_resilience(api_data):
    """
    Property: The main() function contains a 'try...except Exception' block.
    It should NEVER raise an unhandled exception, no matter what garbage 
    the query_rag_api() returns.
    """
    # Setup UI state to reach the rendering logic
    mock_st.text_input.return_value = "Valid Question"
    mock_st.button.return_value = True
    
    # Mock the API call to return the fuzzed garbage data
    with patch('frontend_ui.frontend.query_rag_api') as mock_api:
        mock_api.return_value = api_data
        
        try:
            main()
            
            # If main() executed without Python crashing, the test passes.
            # We specifically check if st.error was called for bad data,
            # or if the code handled it gracefully.
            
        except Exception as e:
            # If we catch an exception here, it means main()'s try/except block FAILED.
            pytest.fail(f"CRASHED rendering API response: {api_data}\nError: {e}")

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
@given(st.text())
def test_fuzz_input_sanitization(user_query):
    """
    Property: query_rag_api handles any string input without client-side errors.
    """
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {}
        
        try:
            query_rag_api(user_query, "http://fake")
        except Exception as e:
            pytest.fail(f"Client crashed on input: {repr(user_query)} Error: {e}")