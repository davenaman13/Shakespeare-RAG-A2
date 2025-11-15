# 🎓 The Shakespearean Scholar: Containerized RAG System

## 1. Project Overview

This project implements a full-stack, containerized **Retrieval-Augmented Generation (RAG)** system designed to function as an expert AI tutor on William Shakespeare's *The Tragedy of Julius Caesar*.

The system's final persona is the "**Expert Shakespearean Scholar**," dedicated to providing academically rigorous, insightful, and clear answers suitable for an **ICSE Class 10 student** audience. All answers are generated **exclusively** from the provided Folger Edition PDF and include explicit textual citations.

## 2. System Architecture

The application is deployed using Docker Compose, orchestrating three services connected via an internal Docker network:

                                        +----------+
                                        |  User    |
                                        | (Student)|
                                        +----+-----+
                                            | (Query via Browser)
                                            |
                                        +----v-----+
                                        | Streamlit| (Service 1: Frontend)
                                        | (Port 8501)|
                                        +----+-----+
                                            | (Internal API Call)
                                            |
                                        +----v-----+
                                        | FastAPI  | (Service 2: Backend/Orchestrator)
                                        | (Port 8000)|
                                        +----+-----+
                                            | 1. Embed Query (BGE-1.5)
                                            | 2. Retrieve Context
                                        +----v-----+  +-----------------+
                                        | ChromaDB |  | Gemini-2.5-Flash| (External LLM Service)
                                        | (Vector Store)|  +-------^---------+
                                        +----------+          | 3. Send Context + Prompt
                                            ^              |
                                            +--------------+
                                            | 4. Final Answer Generation
                                        +----+-----+
                                        | FastAPI  |
                                        +----+-----+
                                            | (Structured JSON Response)
                                        +----v-----+
                                        | Streamlit|
                                        +----+-----+
                                            | (Rendered Answer)
                                        +----v-----+
                                        |  User    |
                                        +----------+

## 3. Design Justification

Our design choices were made to optimize for **semantic accuracy**, **containerization simplicity**, and **context preservation**.

### A. Data ETL & Chunking Strategy (Phase 1)

* **Strategy:** **Hybrid Logical/Semantic Chunking.** The primary chunking method identifies logical play units (speeches and soliloquies) to ensure that the complete rhetorical argument of a character is preserved.
* **Refinement for Accuracy:** An aggressive sentence-level split was implemented for medium-sized dialogue chunks ($\text{>100}$ words). This ensures high **precision** for retrieving short, critical facts or famous one-line quotes (e.g., "Beware the Ides of March"), which are often diluted in large, scene-level chunks.
* **Tools:** `pdfplumber` was chosen for its robust ability to handle the non-trivial **table-based dialogue** and complex formatting of the Folger Edition PDF.

### B. Indexing Model Choices (Phase 2)

* **Embedding Model:** **`BAAI/bge-base-en-v1.5`**. Chosen over baseline models for its superior performance in semantic similarity benchmarks, which is essential for accurately mapping complex, analytical questions (like those on themes or character motivations) to relevant chunks of text.
* **Vector Store:** **`ChromaDB`** (Persistent Client). Selected for its ease of containerization. The index is built once locally and then mounted into the Docker container, fulfilling the requirement without needing to run an external database service inside the container.
* **Retrieval:** Top-$\text{K}=8$ chunks are retrieved to provide a large context window, enabling the LLM to synthesize complex answers from scattered information.

### C. Generation Model (Phase 4)

* **LLM:** **Google `Gemini-2.5-flash`**. Chosen for its combination of high performance, large context window, and rapid generation speed. This model is highly effective at executing the detailed System Prompt, maintaining the academic persona, and performing the required internal **re-ranking** of retrieved chunks.

## 4. Run Instructions

### Prerequisites

1.  **Docker Desktop** must be installed and running.
2.  An active **Gemini API Key** must be available.

### Setup and Launch

1.  **Clone the repository:**
    ```bash
    git clone YOUR_REPOSITORY_URL
    cd AdvNLP_Assignment2
    ```
2.  **Set Credentials:** Create a file named **`.env`** in the root directory and paste your API key:
    ```
    GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```
3.  **Launch the System:** The entire stack is brought up with one command. The `--build` flag ensures the latest code and dependencies (including the `torch/numpy` fixes) are used.
    ```bash
    docker-compose up --build -d
    ```

### Access

* **Frontend UI:** Access the chat interface at: **`http://localhost:8501`**
* **API Documentation:** Access the raw FastAPI `/query` endpoint documentation at: **`http://localhost:8000/docs`**

---

## 5. Evaluation & Analysis

*(Note: The full content for this section will be in the separate EVALUATION.md file.)*

To generate the required evaluation output:
1. Ensure the system is running (`docker-compose up -d`).
2. Run the inference script: `python evaluation/A2_infer.py`

This will generate the `evaluation_results.json` file needed for the final report.