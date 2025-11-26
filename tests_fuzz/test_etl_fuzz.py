import sys
import os
# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

import pytest
from hypothesis import given, strategies as st, example, settings, HealthCheck
from julius_etl.etl_julius import sanitize_text, clean_page_text, roman_to_int

# ==============================================================================
# 1. FUZZING roman_to_int
# ==============================================================================

# Strategy: Generate text, integers, floats, or None
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.one_of(st.text(), st.integers(), st.floats(), st.none()))
@example("IV") # Explicitly test standard cases too
@example("L")
def test_fuzz_roman_to_int_properties(input_val):
    """
    Property: roman_to_int must ALWAYS return an int or the original string/input.
    It should NEVER raise an unhandled exception.
    """
    try:
        result = roman_to_int(input_val)
        
        # Property 1: Type Stability
        # Result must be either an int, or the string representation of input, or the input itself
        assert isinstance(result, (int, str)) or result is input_val
        
        # Property 2: Consistency
        # If input is "V", result MUST be 5. 
        if input_val == "V":
            assert result == 5
            
    except Exception as e:
        pytest.fail(f"CRASHED on input: {repr(input_val)} with error: {e}")

# ==============================================================================
# 2. FUZZING clean_page_text (The Cleaner)
# ==============================================================================

# Strategy: Generate text that explicitly contains your "Triggers" mixed with garbage
@given(st.text())
def test_fuzz_clean_page_removes_ftln(garbage):
    """
    Property: No matter what text surrounds it, 'FTLN <number>' MUST be removed.
    """
    # We construct a string that definitely has FTLN
    input_text = f"Some content {garbage} FTLN 1234 {garbage} End content"
    
    result = clean_page_text(input_text)
    
    # Property: The cleaner MUST effectively remove the FTLN header
    # Note: clean_page_text uses regex \bFTLN\s*\d+\b. 
    # If we inject FTLN 1234, it should be gone.
    assert "FTLN 1234" not in result

# ==============================================================================
# 3. FUZZING sanitize_text (Regex Logic)
# ==============================================================================

@given(st.text())
def test_fuzz_sanitize_idempotence(input_text):
    """
    Property: Idempotence.
    Running sanitize_text TWICE should give the same result as running it ONCE.
    (sanitize(sanitize(x)) == sanitize(x))
    If this fails, your regexes are "unstable".
    """
    once = sanitize_text(input_text)
    twice = sanitize_text(once)
    
    assert once == twice

@given(st.text(min_size=1))
def test_fuzz_sanitize_length_property(input_text):
    """
    Property: Sanitize mostly removes things.
    The output should usually not be significantly longer than the input 
    (unless you are expanding whitespace, which your code merges).
    """
    result = sanitize_text(input_text)
    
    # Your code does: collapse whitespace, remove headers.
    # Result logic: Result length <= Input length (roughly).
    # We add a buffer just in case of weird unicode expansion, but generally strict.
    assert len(result) <= len(input_text) + 5 

# ==============================================================================
# 4. FUZZING Intro Logic
# ==============================================================================

@given(st.text())
def test_fuzz_intro_removal(garbage):
    """
    Property: Any line containing 'Barbara Mowat' must be dropped.
    """
    input_text = f"Valid line.\n{garbage} Barbara Mowat {garbage}\nAnother valid line."
    
    result = clean_page_text(input_text)
    
    # Property: The specific intro marker should trigger the line drop
    # Note: Your regex is INTRO_RE.search(s).
    assert "Barbara Mowat" not in result