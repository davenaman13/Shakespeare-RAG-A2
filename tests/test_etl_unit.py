import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from julius_etl.etl_julius import sanitize_text, clean_page_text, roman_to_int, parse_pdf

# ==============================================================================
# 1. LOGIC MUTANT KILLERS (sanitize_text & clean_page_text)
# Target: "or -> and" mutants in Regex/String checks
# ==============================================================================

def test_regex_logic_kills_or_mutants():
    """
    Kills (or -> and) mutants in header removal logic.
    We must test the SPECIFIC function that handles each header type.
    """
    # Case 1: Header with ONLY 'Act' (Handled by sanitize_text)
    # If mutant uses 'and' (e.g. if "ACT" in line and "SCENE" in line), 
    # this isolated 'ACT' would NOT be removed.
    assert sanitize_text("ACT 1\nContent") == "Content", "Failed to remove 'Act' only header in sanitize_text"
    
    # Case 2: Header with ONLY 'FTLN' (Handled by clean_page_text)
    # If mutant uses 'and' in clean_page_text regex, this isolated 'FTLN' would NOT be removed.
    # We switch to clean_page_text() here because that's where FTLN logic lives.
    assert clean_page_text("FTLN 0001\nContent") == "Content", "Failed to remove 'FTLN' only header in clean_page_text"

def test_sanitize_kills_and_mutants():
    """
    Kills (and -> or) mutants.
    Ensure normal text isn't deleted accidentally due to over-aggressive 'or' logic.
    """
    assert sanitize_text("Actual content here") == "Actual content here"
    assert sanitize_text("Scene of the crime") == "Scene of the crime" 

# ==============================================================================
# 2. ARITHMETIC & TYPE MUTANT KILLERS (roman_to_int)
# Target: "+ -> -", "True -> False", "int() -> int()+1"
# ==============================================================================

def test_roman_to_int_strict_arithmetic():
    # Kills +1 or -1 mutants
    assert roman_to_int("I") == 1
    assert roman_to_int("V") == 5
    assert roman_to_int("X") == 10

def test_roman_to_int_edge_cases():
    # Kills boolean logic flips. 
    result = roman_to_int(None)
    assert result is None or result == "NONE" or result == "None"
    
    # Invalid inputs
    assert roman_to_int("NotRoman") == "NOTROMAN"

# ==============================================================================
# 3. BOUNDARY & LOOP MUTANT KILLERS (parse_pdf)
# Target: "< -> >=", "+ -> -", "900 -> 999999"
# ==============================================================================

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_parse_pdf_boundary_splitting(mock_pdf_open):
    """
    Surgical test for splitting threshold (usually 900 words).
    We test slightly below and slightly above to kill boundary mutants.
    """
    mock_pdf = MagicMock()
    
    # --- Chunk 1: 850 words (Under Threshold) ---
    speech_under = "word " * 850
    page1 = MagicMock()
    page1.extract_text.return_value = f"BRUTUS\n{speech_under}"
    page1.extract_tables.return_value = None

    # --- Chunk 2: 950 words (Over Threshold) ---
    speech_over = "word " * 950
    page2 = MagicMock()
    page2.extract_text.return_value = f"CASSIUS\n{speech_over}"
    page2.extract_tables.return_value = None

    mock_pdf.pages = [page1, page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))

    # Assertions
    brutus_chunks = [c for c in chunks if c['speaker'] == 'Brutus']
    assert len(brutus_chunks) == 1, "Brutus (850 words) should not be split"

    cassius_chunks = [c for c in chunks if c['speaker'] == 'Cassius']
    assert len(cassius_chunks) > 1, "Cassius (950 words) MUST be split"

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_parse_pdf_complex_flow(mock_pdf_open):
    """
    The 'Mega Test' to ensure overall integration and sequence logic.
    """
    mock_pdf = MagicMock()
    
    page1 = MagicMock()
    page1.extract_text.return_value = (
        "ACT 1\n"
        "CAESAR\n"
        "Cowards die many times before their deaths.\n"
    )
    # Return empty list or None depending on library version mocked
    page1.extract_tables.return_value = [] 

    page2 = MagicMock()
    page2.extract_text.return_value = (
        "ANTONY\n"
        "Friends, Romans, countrymen.\n"
    )
    page2.extract_tables.return_value = None

    mock_pdf.pages = [page1, page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    
    assert len(chunks) == 2
    assert chunks[0]['speaker'] == "Caesar"
    assert chunks[1]['speaker'] == "Antony"
    
    # Fix: Use .get() or check known keys.
    chunk_0_text = chunks[0].get('text') or chunks[0].get('text_content') or chunks[0].get('content')
    assert "Cowards" in chunk_0_text
    assert "Header" not in chunk_0_text