# tests/test_etl.py
import pytest
from julius_etl.etl_julius import sanitize_text, roman_to_int

# --- Data Flow Test 1: Variable Definition & Sanitization ---
# Target: sanitize_text function
# Variable 'txt' is defined, modified (re-defined), and used in return.
def test_sanitize_text_removes_ftln():
    input_text = "FTLN 1234\nBrutus speaks."
    # This asserts that the 'FTLN' regex path is executed
    assert sanitize_text(input_text) == "Brutus speaks."

def test_sanitize_text_removes_headers():
    input_text = "ACT 1. SC. 2\nCaesar enters."
    # This asserts the header removal path
    assert sanitize_text(input_text) == "Caesar enters."

def test_sanitize_text_keeps_clean_text():
    input_text = "Et tu, Brute?"
    # This asserts the 'no-change' path
    assert sanitize_text(input_text) == "Et tu, Brute?"

# --- Data Flow Test 2: Loop & Branching Logic ---
# Target: roman_to_int helper
def test_roman_to_int_valid():
    assert roman_to_int("III") == 3
    assert roman_to_int("X") == 10

def test_roman_to_int_invalid_returns_input():
    # This tests the 'except' block path (Exception Handling)
    assert roman_to_int("Unknown") == "Unknown"