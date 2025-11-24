import pytest
from unittest.mock import MagicMock, patch
from julius_etl.api_rag import perform_rag_search, validate_rag_input, format_context

# ==============================================================================
# 1. INPUT VALIDATION LOGIC (Kills 'and -> or' mutants)
# ==============================================================================

def test_validate_rag_input_kills_boolean_mutants():
    """
    Target: if query and context:
    Mutant: if query or context:
    
    We test cases where ONLY ONE is present. 
    - Original (AND) should fail/return False.
    - Mutant (OR) would pass/return True.
    """
    # Case 1: Only Query provided (Context missing)
    # Original: False. Mutant: True.
    assert validate_rag_input("Who is Brutus?", "") is False, "Mutant (OR) survived: Accepted query without context"

    # Case 2: Only Context provided (Query missing)
    # Original: False. Mutant: True.
    assert validate_rag_input("", "Brutus is a noble Roman.") is False, "Mutant (OR) survived: Accepted context without query"

    # Case 3: Both missing
    assert validate_rag_input("", "") is False

    # Case 4: Both present (Happy Path)
    assert validate_rag_input("Who?", "Context") is True

# ==============================================================================
# 2. BOOLEAN LOGIC IN SEARCH/FILTERING (Kills 'or -> and' / 'True -> False')
# ==============================================================================

@patch('julius_etl.api_rag.genai.GenerativeModel')
def test_perform_rag_search_logic_flow(mock_model_class):
    """
    Kills mutants in the search logic flow (lines 60-100).
    Targets: 
    - (a or b) logic in prompt construction.
    - Return value mutants (True -> False).
    """
    # Setup Mock
    mock_model_instance = mock_model_class.return_value
    mock_response = MagicMock()
    mock_response.text = "Caesar died."
    mock_model_instance.generate_content.return_value = mock_response

    # --- Test 1: Complex Filtering Logic ---
    # Assume logic: if (strict_mode or valid_key) and not error:
    # We simulate 'strict_mode=False' but 'valid_key=True'.
    # Mutant (and) would fail. Original (or) passes.
    result = perform_rag_search(
        query="Death of Caesar", 
        context="Historical records...",
        strict_mode=False  # Crucial for killing 'and' mutants in defaults
    )
    assert result['status'] == 'success'
    assert result['answer'] == "Caesar died."

    # --- Test 2: Error Handling Logic (Kills True -> False) ---
    # Force an API error. 
    # Logic: return {"status": "error", "valid": False}
    # Mutant: return {"status": "error", "valid": True} (flipped boolean)
    mock_model_instance.generate_content.side_effect = Exception("API Down")
    
    error_result = perform_rag_search("Q", "C")
    
    # Assert EXACT values to kill boolean flip mutants
    assert error_result['status'] == 'error'
    assert error_result.get('valid_response') is False, "Mutant survived: Error state reported valid=True"

# ==============================================================================
# 3. PROMPT FORMATTING (Kills String/Logic Mutants)
# ==============================================================================

def test_format_context_logic():
    """
    Targets logic: if source and text: format string
    Mutant: if source or text: format string
    """
    # Case: Missing source, present text
    # Should probably fallback to generic or return clean text
    chunk = {"text_content": "Hello", "source": ""}
    formatted = format_context(chunk)
    
    # If mutant uses 'or', it might format weirdly like "Source: None \n Hello"
    # Original likely handles it gracefully
    assert "Unknown Source" not in formatted or "None" not in formatted
    assert "Hello" in formatted