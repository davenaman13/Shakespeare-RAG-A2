import sys
import os
# --- PATH FIX: Add parent directory so Python finds julius_etl ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# -----------------------------------------------------------------

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from julius_etl.etl_julius import sanitize_text, clean_page_text, roman_to_int, parse_pdf

# ==============================================================================
# 1. LOGIC TRAPS (Kills 'or -> and' / 'and -> or')
# ==============================================================================

def test_sanitize_logic_trap_act():
    """
    Trap: `sanitize_text` regex replacement order.
    Mutant: Changing order or logic of replacements.
    """
    # This specific string targets ACT_SC_WORDS_RE
    # Original: Replaces "Act 1 Scene 2" -> ""
    # Mutant (Logic Flip): Might fail to replace if regex conditions change.
    assert sanitize_text("Brutus. Act 1 Scene 2") == "Brutus.", "Mutant survived: Act/Scene regex logic broken"

def test_clean_text_logic_trap_header_list():
    """
    Trap: `clean_page_text` iterates over `HEADER_LINE_REs`.
    Mutant: `if r.match(s): skip=True` -> `skip=False` or `break` logic change.
    """
    # Input contains FTLN (in the list) and normal text.
    # If the loop logic is broken, FTLN might persist.
    res = clean_page_text("FTLN 1234\nValid Line.")
    assert "FTLN" not in res, "Mutant survived: Header skipping logic broken"
    assert "Valid Line" in res

def test_intro_filtering_trap():
    """
    Trap: `if INTRO_RE.search(s): continue`
    Mutant: `if not INTRO_RE.search(s): continue` (Logic Inversion)
    """
    # "Barbara Mowat" is in INTRO_MARKERS
    res = clean_page_text("Barbara Mowat\nValid Text")
    assert "Barbara Mowat" not in res, "Mutant survived: Intro filtering logic broken"
    assert "Valid Text" in res

# ==============================================================================
# 2. BOUNDARY TRAPS (Kills '< -> <=' / '900 -> 901')
# ==============================================================================

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_splitting_boundary_exactness(mock_pdf_open):
    """
    Trap: WORD_SPLIT_THRESHOLD = 900.
    """
    mock_pdf = MagicMock()
    
    # Case A: 850 Words (Under Limit) - Should be 1 Chunk
    page1 = MagicMock()
    page1.extract_text.return_value = f"SPEAKER_A\n{'word ' * 850}"
    page1.extract_tables.return_value = None

    # Case B: 950 Words (Over Limit) - Should be >1 Chunk
    page2 = MagicMock()
    page2.extract_text.return_value = f"SPEAKER_B\n{'word ' * 950}"
    page2.extract_tables.return_value = None

    mock_pdf.pages = [page1, page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    
    chunks_a = [c for c in chunks if c['speaker'] == 'Speaker_a' or c['speaker'] == 'SPEAKER_A']
    chunks_b = [c for c in chunks if c['speaker'] == 'Speaker_b' or c['speaker'] == 'SPEAKER_B']

    assert len(chunks_a) == 1, "Mutant survived: Logic split a text under the limit (< became <=)"
    assert len(chunks_b) > 1,  "Mutant survived: Logic failed to split a text over the limit (> became >=)"

# ==============================================================================
# 3. HEURISTIC TRAPS (Speaker Correction)
# ==============================================================================

@patch('julius_etl.etl_julius.pdfplumber.open')
# Patch clean_page_text to allow "THE" to reach the parser logic
@patch('julius_etl.etl_julius.clean_page_text', side_effect=lambda x: x) 
def test_bad_speaker_logic_trap(mock_clean, mock_pdf_open):
    """
    Trap: `is_bad_speaker(name)` logic.
    Mutant: Logic flip in the `if is_bad_speaker` check.
    """
    mock_pdf = MagicMock()
    page = MagicMock()
    
    # "THE" is in the bad speaker set {"A","I","W","Y","THE"}
    # Original: Should identify "THE" as bad and reassign to "BRUTUS"
    # Mutant: If logic fails, "THE" remains as speaker.
    page.extract_text.return_value = (
        "BRUTUS\n"
        "Valid speech.\n"
        "\n"
        "THE\n"
        "Another speech."
    )
    page.extract_tables.return_value = None
    mock_pdf.pages = [page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    
    # Find the second chunk
    chunk2 = chunks[1]
    assert chunk2['speaker'] == "Brutus", f"Mutant survived: Bad speaker 'THE' was not corrected. Got: {chunk2['speaker']}"

# ==============================================================================
# 4. TYPE TRAPS (Kills 'True -> False' / Type Errors)
# ==============================================================================

def test_roman_logic_trap_none():
    """
    Trap: Ensure None input is handled gracefully.
    """
    # Code: s = str(s).upper() -> "NONE"
    result = roman_to_int(None)
    assert result == "NONE", "Mutant survived: roman_to_int failed to handle None"
    
    # Code: try: return int(s)
    assert roman_to_int("5") == 5
    
    # Code: return roman_map.get(s, s)
    assert roman_to_int("I") == 1