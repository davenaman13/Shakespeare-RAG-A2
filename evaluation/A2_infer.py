import json
import requests
from tqdm import tqdm as tqdm_standard

# --- Configuration ---
API_ENDPOINT = "http://localhost:8000/query"
TESTBED_PATH = "evaluation/evaluation.json"
OUTPUT_PATH = "evaluation_results.json"
# ---------------------

def load_testbed(path):
    """Loads the evaluation questions JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Testbed file not found at {path}. Please create it first.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Testbed file is not valid JSON at {path}.")
        return []

def run_evaluation():
    """Runs the full set of questions against the RAG API."""
    testbed = load_testbed(TESTBED_PATH)
    if not testbed:
        return

    print(f"Loaded {len(testbed)} questions. Starting inference...")
    results = []

    for item in tqdm_standard(testbed, desc="Running Queries"):
        query = item["question"]
        
        # Prepare the request body
        payload = {"query": query}
        
        try:
            # Call the live containerized API
            response = requests.post(
                API_ENDPOINT,
                json=payload,
                timeout=30 # Set a reasonable timeout for LLM generation
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            api_result = response.json()
            
            # Structure the final result for the report
            results.append({
                "question": query,
                "ideal_answer": item.get("ideal_answer", "N/A"),
                "generated_answer": api_result.get("answer"),
                "sources": api_result.get("sources"),
                "status_code": response.status_code
            })
            
        except requests.exceptions.RequestException as e:
            # Handle connection or HTTP errors
            print(f"\n[ERROR] Query failed for: {query[:50]}... Error: {e}")
            results.append({
                "question": query,
                "ideal_answer": item.get("ideal_answer", "N/A"),
                "generated_answer": f"API FAILED: {e}",
                "sources": [],
                "status_code": getattr(e.response, 'status_code', 500) if e.response else 500
            })

    # Save all results
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    print(f"\nInference complete! Results saved to {OUTPUT_PATH}")
    print(f"Successfully generated {len([r for r in results if r['status_code'] == 200])} answers.")

if __name__ == "__main__":
    run_evaluation()