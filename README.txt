README.txt
Project: Shakespearean Scholar RAG System - Testing Strategy & Reliability Audit
Submission Date: November 26, 2025

================================================================================
1. TEAM MEMBERS & CONTRIBUTION
================================================================================

Team Members:
- Naman Dave (MT2024097)
- Tanvi Kulkarni (MT2024160)

Contribution Statement:
This project was completed by both of us with equal contribution and there was 
nothing done by either of us explicitly; everything was done in collaboration.

================================================================================
2. CODE REPOSITORY
================================================================================

The complete source code and test suite for this project can be accessed at:
https://github.com/davenaman13/Shakespeare-RAG-A2.git


================================================================================
3. TEST STRATEGY: THE "DEFENSE-IN-DEPTH" APPROACH
================================================================================

We implemented a rigorous "Defense-in-Depth" testing strategy comprising three 
distinct layers to ensure the reliability of the RAG System.

Layer 1: Verification (Unit Testing)
- Goal: Validate functional correctness of individual components.
- Scope: ETL Pipeline (Text Sanitization), API Logic, Frontend Error Handling.
- Key Result: Detected and fixed the "Aggressive Cleaning Bug" where single-
  letter speaker names were incorrectly removed.

Layer 2: Robustness (Mutation Testing)
- Goal: Verify the quality of the test suite by injecting artificial bugs.
- Scope: Retrieval Ranking Logic, Boundary Conditions.
- Tooling: Custom AST-based Mutation Engine.
- Key Result: Achieved >85% Mutation Score, validating that the tests are 
  sensitive to logic inversions.

Layer 3: Resilience (Fuzz Testing)
- Goal: Ensure system stability under unexpected inputs.
- Scope: Malformed JSON payloads, Unicode garbage, corrupted metadata.
- Tooling: Hypothesis (Property-based testing).
- Key Result: Verified graceful degradation without system crashes.

================================================================================
4. OPEN SOURCE TOOLS USED
================================================================================

- pytest: Primary test runner and framework.
- unittest.mock: Standard library for mocking dependencies (ChromaDB, Torch).
- Hypothesis: Library for property-based fuzz testing.
- ast (Python Standard Lib): Used to build the custom Mutation Engine.
- Streamlit: Used for the frontend UI.

================================================================================
5. FILE MANIFEST (INCLUDED IN COMPRESSED FOLDER)
================================================================================

A. Source Code
   - julius_etl/etl_julius.py: Data ingestion and cleaning logic.
   - api_rag/api_rag.py: Backend retrieval and inference API.
   - frontend_ui/frontend.py: Streamlit user interface.

B. Unit Tests
   - tests/test_etl_unit.py: Verifies regex and integer conversion logic.
   - tests/test_api_logic_unit.py: Verifies retrieval flow and context limits.
   - tests/test_frontend_unit.py: Verifies UI error rendering.

C. Mutation Tests
   - auto_mutate.py: Custom AST-based Mutation Engine script.
   - tests/test_mutation_traps.py: "Trap tests" for specific logic bugs.

D. Fuzz Tests
   - tests/test_fuzzing.py: Hypothesis strategies for random input generation.

================================================================================
6. EXECUTION INSTRUCTIONS
================================================================================

To replicate the test results, run the following commands from the root directory:

Step 1: Run Unit Tests
$ pytest tests/test_*_unit.py

Step 2: Run Mutation Analysis
$ python auto_mutate.py --target api_rag.py --test tests/test_api_logic_unit.py

Step 3: Run Fuzz Testing
$ pytest tests/test_fuzzing.py

Results and logs are available in the 'results/' folder.