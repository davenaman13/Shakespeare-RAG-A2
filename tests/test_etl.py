# tests/test_etl.py
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import textwrap
from julius_etl.etl_julius import sanitize_text, clean_page_text, roman_to_int, parse_pdf

# --- 1. Killing Mutant 3 (SDL): Test Sanitization of Isolated Numbers ---
def test_sanitize_removes_isolated_numbers():
    # Mutant 3 deletes the line that removes isolated numbers.
    # This test asserts that "123" MUST be removed.
    input_text = "123\nBrutus speaks."
    # If mutant is active (line deleted), this returns "123\nBrutus speaks." and fails.
    assert sanitize_text(input_text) == "Brutus speaks."

# --- 2. Killing Mutant 2 (LCR): Test Roman-to-Int with Digits ---
def test_roman_to_int_digits():
    # Mutant 2 changes "return int(s)" to "return int(s) + 1".
    # This test asserts that "5" must return 5, not 6.
    assert roman_to_int("5") == 5

# --- Existing Unit Tests ---
def test_clean_page_text_removes_ftln():
    input_text = "FTLN 1234\nBrutus speaks."
    assert clean_page_text(input_text) == "Brutus speaks."

def test_sanitize_text_removes_headers():
    input_text = "ACT 1. SC. 2\nCaesar enters."
    assert sanitize_text(input_text) == "Caesar enters."

def test_sanitize_text_keeps_clean_text():
    input_text = "Et tu, Brute?"
    assert sanitize_text(input_text) == "Et tu, Brute?"

def test_roman_to_int_valid():
    assert roman_to_int("III") == 3
    assert roman_to_int("X") == 10

def test_roman_to_int_invalid_returns_input():
    assert roman_to_int("Unknown") == "UNKNOWN"

# --- 3. Killing Mutant 1 (AOR): Test Chunk Splitting Logic ---
@patch('julius_etl.etl_julius.pdfplumber.open')
def test_parse_pdf_splitting(mock_pdf_open):
    """
    Tests that large chunks are split. 
    Kills the mutant that increases split threshold to 999999.
    """
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    
    # Generate a long speech (> 900 words)
    long_speech = "word " * 950 
    fake_page_text = f"BRUTUS\n{long_speech}"
    
    mock_page.extract_text.return_value = fake_page_text
    mock_page.extract_tables.return_value = None
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))

    # If threshold is normal (900), this splits into 2 parts.
    # If mutant is active (999999), this remains 1 part and assertion fails.
    assert len(chunks) > 1 

# --- Existing Logic Test ---
@patch('julius_etl.etl_julius.pdfplumber.open')
def test_parse_pdf_logic_flow(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    fake_page_text = (
        "ACT 1. SC. 2\n"
        "FTLN 0001\n"
        "\n"
        "BRUTUS\n"
        "The name of honor is dearer than death.\n"
        "\n"
        "CASSIUS\n"
        "Virtue is within you, Brutus."
    )
    mock_page.extract_text.return_value = fake_page_text
    mock_page.extract_tables.return_value = None
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    assert len(chunks) >= 2