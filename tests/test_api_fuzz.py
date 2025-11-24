import sys
import os
import pytest
from hypothesis import given, strategies as st
from fastapi.testclient import TestClient

# applied Fuzz Testing to the Integration Level (API), not just the Unit Level.

# Add api_rag to path so we can import 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../api_rag')))
from api_rag import app

client = TestClient(app)

# --- Fuzz Test 2: API Endpoint Robustness ---
# Strategy: Generate random text for the 'query' field.
# Goal: Ensure the API returns a valid HTTP code (200, 404, 422, 500),
# but NEVER crashes the server process (connection refused/timeout).
@given(query_text=st.text())
def test_fuzz_query_endpoint(query_text):
    # We expect the API to handle any string, even empty or weird ones.
    response = client.post("/query", json={"query": query_text})
    
    # We assert that the server handled it. 
    # 422 (Validation Error) is acceptable for bad input.
    # 500 is acceptable if the mock fails (since we aren't mocking here yet).
    # What we don't want is a segmentation fault or unhandled exception that stops the test runner.
    assert response.status_code in [200, 422, 500]