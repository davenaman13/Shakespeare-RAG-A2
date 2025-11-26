import sys
import os
# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ----------------

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from julius_etl.etl_julius import (
    sanitize_text, 
    clean_page_text, 
    roman_to_int, 
    parse_pdf, 
    SOLILOQUY_MIN_WORDS
)

# ==============================================================================
# 1. HELPER FUNCTION TESTS
# ==============================================================================

def test_roman_to_int_logic():
    """Verifies Roman numeral conversion logic."""
    assert roman_to_int("I") == 1
    assert roman_to_int("iv") == 4 
    assert roman_to_int("X") == 10
    assert roman_to_int("Brutus") == "BRUTUS"

def test_sanitize_text_specifics():
    """Tests specific regex replacements defined in sanitize_text."""
    # FIX: Use 'Act 1' which matches ACT_SC_WORDS_RE cleanly
    assert sanitize_text("Brutus enters. Act 1") == "Brutus enters."
    # FIX: Use 'Act I. Scene 2' which matches ACT_SC_INLINE_RE cleanly
    # (Regex expects SC/SCENE structure with optional dots)
    assert sanitize_text("Brutus leaves. Act I. Scene 2") == "Brutus leaves."
    
    assert sanitize_text("123\nEt tu, Brute?") == "Et tu, Brute?"

def test_clean_page_text_filters():
    """Tests that headers, FTLN, and Intro text are removed."""
    raw_text = (
        "FTLN 0001\n"
        "The Tragedy of Julius Caesar\n"
        "Barbara Mowat\n" 
        "ACT 1. SC. 2\n"
        "Cassius speaks."
    )
    cleaned = clean_page_text(raw_text)
    assert "FTLN" not in cleaned
    assert "Tragedy of" not in cleaned 
    assert "Barbara Mowat" not in cleaned 
    assert "Cassius speaks" in cleaned

# ==============================================================================
# 2. PDF PARSING FLOW & LOGIC
# ==============================================================================

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_parse_pdf_table_extraction(mock_pdf_open):
    """Meaningful Test: Ensures table content is merged into text."""
    mock_pdf = MagicMock()
    page = MagicMock()
    page.extract_text.return_value = ""
    page.extract_tables.return_value = [[
        ["CASCA", "Speak, hands, for me!"],
        ["CAESAR", "Et tu, Brute?"]
    ]]
    mock_pdf.pages = [page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    combined_text = " ".join([c['text'] for c in chunks])
    assert "Speak, hands, for me" in combined_text

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_soliloquy_detection_logic(mock_pdf_open):
    """Meaningful Test: Checks 'is_soliloquy' flag based on word count."""
    mock_pdf = MagicMock()
    page = MagicMock()
    long_text = "word " * (SOLILOQUY_MIN_WORDS + 10)
    page.extract_text.return_value = f"BRUTUS\n{long_text}"
    page.extract_tables.return_value = None
    mock_pdf.pages = [page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    assert chunks[0]['is_soliloquy'] is True

@patch('julius_etl.etl_julius.pdfplumber.open')
# CRITICAL FIX: We patch clean_page_text to allow "THE" to pass through to the parser
@patch('julius_etl.etl_julius.clean_page_text', side_effect=lambda x: x)
def test_speaker_heuristic_correction(mock_clean, mock_pdf_open):
    """
    Meaningful Test: Fixes bad speakers (Heuristic Logic).
    We bypass the cleaning logic (mock_clean) to verify that IF the parser
    sees the bad speaker, it correctly reassigns it.
    """
    mock_pdf = MagicMock()
    page = MagicMock()
    
    # Chunk 1: Brutus
    # Chunk 2: "THE" (Bad Speaker) -> Should inherit "Brutus"
    page.extract_text.return_value = (
        "BRUTUS\n"
        "I love honor more than death.\n"
        "\n"
        "THE\n" 
        "More than I fear death indeed."
    )
    page.extract_tables.return_value = None
    mock_pdf.pages = [page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    
    assert len(chunks) == 2
    # The second chunk should have been corrected from "THE" to "Brutus"
    assert chunks[1]['speaker'] == "Brutus"

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_sentence_splitting_threshold(mock_pdf_open):
    """Meaningful Test: Tests SENTENCE_SPLIT_THRESHOLD (100 words)."""
    mock_pdf = MagicMock()
    page = MagicMock()
    sentence_1 = "Word " * 70 + ". "
    sentence_2 = "Word " * 70 + "."
    page.extract_text.return_value = f"CASSIUS\n{sentence_1}{sentence_2}"
    page.extract_tables.return_value = None
    mock_pdf.pages = [page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    assert len(chunks) >= 2
    assert any("_sen" in c['chunk_id'] for c in chunks)

# ==============================================================================
# 3. METADATA TESTS
# ==============================================================================

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_metadata_propagation(mock_pdf_open):
    """
    Meaningful Test: Checks if missing Act/Scene numbers are filled.
    """
    mock_pdf = MagicMock()
    page = MagicMock()
    
    page.extract_text.return_value = (
        "ACT 1. SCENE 2.\n"
        "BRUTUS\n"
        "Speech one is long enough to exist.\n"
        "\n"
        "CASSIUS\n" 
        "Speech two is also long enough.\n"
        "\n"
        "ACT 1. SCENE 3.\n"
        "CICERO\n"
        "Speech three is long enough."
    )
    page.extract_tables.return_value = None
    mock_pdf.pages = [page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf
    
    chunks = parse_pdf(Path("dummy.pdf"))
    
    # Middle chunk (Cassius) should have Act 1, Scene 2
    cassius_chunk = [c for c in chunks if c['speaker'] == 'Cassius'][0]
    assert cassius_chunk['act'] == 1
    assert cassius_chunk['scene'] == 2

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_chunk_id_uniqueness(mock_pdf_open):
    """Meaningful Test: Ensures every chunk gets a unique ID."""
    mock_pdf = MagicMock()
    page = MagicMock()
    page.extract_text.return_value = "\n".join([f"BRUTUS\nSpeech {i} is unique enough." for i in range(5)])
    page.extract_tables.return_value = None
    mock_pdf.pages = [page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf
    
    chunks = parse_pdf(Path("dummy.pdf"))
    ids = [c['chunk_id'] for c in chunks]
    assert len(ids) == len(set(ids)), "Duplicate Chunk IDs detected!"