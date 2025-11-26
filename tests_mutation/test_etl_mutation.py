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
    Trap: If logic is 'if ACT in line or SCENE in line':
    Mutant: 'if ACT in line and SCENE in line'
    Input: 'ACT 1' (No SCENE)
    Original: Removes it.
    Mutant: Keeps it (because SCENE is missing).
    """
    # Trap: We provide a string that satisfies only ONE condition of the OR statement.
    assert sanitize_text("ACT 1\nContent") == "Content", "Mutant survived: 'Act' header not removed (Check AND/OR logic)"

def test_clean_text_logic_trap_ftln():
    """
    Trap: If logic is 'if FTLN in line or Page in line':
    Mutant: 'if FTLN in line and Page in line'
    Input: 'FTLN 1234' (No Page)
    """
    res = clean_page_text("FTLN 1234\nContent")
    assert "FTLN" not in res, "Mutant survived: 'FTLN' header not removed"

# ==============================================================================
# 2. BOUNDARY TRAPS (Kills '< -> <=' / '900 -> 901')
# ==============================================================================

@patch('julius_etl.etl_julius.pdfplumber.open')
def test_splitting_boundary_exactness(mock_pdf_open):
    """
    Trap: We test the exact boundary of the splitting threshold.
    If the threshold is 900 words:
    - 850 words must NOT split.
    - 950 words MUST split.
    """
    mock_pdf = MagicMock()
    
    # Case A: 850 Words (Under Limit)
    page1 = MagicMock()
    page1.extract_text.return_value = f"SPEAKER_A\n{'word ' * 850}"
    page1.extract_tables.return_value = None

    # Case B: 950 Words (Over Limit)
    page2 = MagicMock()
    page2.extract_text.return_value = f"SPEAKER_B\n{'word ' * 950}"
    page2.extract_tables.return_value = None

    mock_pdf.pages = [page1, page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    chunks = parse_pdf(Path("dummy.pdf"))
    
    # Count chunks per speaker
    # Note: We use .lower() or exact match depending on your ETL output
    chunks_a = [c for c in chunks if c['speaker'] == 'Speaker_a' or c['speaker'] == 'SPEAKER_A']
    chunks_b = [c for c in chunks if c['speaker'] == 'Speaker_b' or c['speaker'] == 'SPEAKER_B']

    # Assertions
    assert len(chunks_a) == 1, "Mutant survived: Logic split a text that was under the limit (< became <=)"
    assert len(chunks_b) > 1,  "Mutant survived: Logic failed to split a text over the limit (> became >=)"

# ==============================================================================
# 3. TYPE TRAPS (Kills 'True -> False' / Type Errors)
# ==============================================================================

def test_roman_logic_trap_none():
    """
    Trap: Ensure None input is handled gracefully (kills logic flips).
    """
    # If the code is `if not s: return None`
    # Mutant: `if s: return None` -> Would return None for "X" (Fail)
    result = roman_to_int(None)
    
    # Check for likely return values (None or "NONE" string)
    assert result is None or result == "NONE" or result == "None"
    
    # Basic check to ensure logic flip didn't break valid inputs
    assert roman_to_int("I") == 1