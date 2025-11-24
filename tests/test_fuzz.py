from hypothesis import given, strategies as st
from julius_etl.etl_julius import sanitize_text

# This generates random strings of text, numbers, and special characters
@given(st.text())
def test_fuzz_sanitize_never_crashes(input_text):
    """
    Property-Based Test: No matter what garbage text we feed,
    sanitize_text should never crash (raise an exception).
    """
    try:
        result = sanitize_text(input_text)
        assert isinstance(result, str)
    except Exception as e:
        pytest.fail(f"CRASHED on input: {repr(input_text)} with error: {e}")