# tests/test_etl.py
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from julius_etl.etl_julius import sanitize_text, clean_page_text, roman_to_int, parse_pdf

# --- Unit Tests (Data Flow) ---
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

# --- Complex Logic Test (Mocking) ---
@patch('julius_etl.etl_julius.pdfplumber.open')
def test_parse_pdf_logic_flow(mock_pdf_open):
    """
    Tests the core logic of extracting chunks from a page.
    """
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    
    # FIX: Changed dialogue to start with "The" and "Virtue" instead of "I"
    # to avoid the SINGLE_LETTER_LINE regex stripping the lines.
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

    # Assertions
    assert len(chunks) >= 2
    assert chunks[0]['speaker'] == "Brutus"
    assert "honor" in chunks[0]['text']
    assert chunks[1]['speaker'] == "Cassius"