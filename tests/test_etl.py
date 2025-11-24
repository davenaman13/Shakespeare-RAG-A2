# tests/test_etl.py
import pytest
from julius_etl.etl_julius import sanitize_text, clean_page_text, roman_to_int

# --- Data Flow Test 1: Variable Definition & Sanitization ---
# Target: clean_page_text function (Unit for full page cleaning)
def test_clean_page_text_removes_ftln():
    input_text = "FTLN 1234\nBrutus speaks."
    # clean_page_text handles FTLN removal
    assert clean_page_text(input_text) == "Brutus speaks."

# Target: sanitize_text function (Unit for chunk cleaning)
def test_sanitize_text_removes_headers():
    # This failed before because '1' was stripped before 'ACT' was matched.
    # Now with the Fix in Step 1, this should PASS.
    input_text = "ACT 1. SC. 2\nCaesar enters."
    assert sanitize_text(input_text) == "Caesar enters."

def test_sanitize_text_keeps_clean_text():
    input_text = "Et tu, Brute?"
    assert sanitize_text(input_text) == "Et tu, Brute?"

# --- Data Flow Test 2: Loop & Branching Logic ---
def test_roman_to_int_valid():
    assert roman_to_int("III") == 3
    assert roman_to_int("X") == 10

def test_roman_to_int_invalid_returns_input():
    # This tests the 'except' block path. 
    # FIX: The code does str(s).upper(), so 'Unknown' becomes 'UNKNOWN'.
    assert roman_to_int("Unknown") == "UNKNOWN"