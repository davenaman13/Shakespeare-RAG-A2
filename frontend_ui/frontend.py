import streamlit as st
import requests
import json

# --- Configuration ---
API_URL = "http://rag-api:8000/query" 

# 🛠️ REFACTORED: Logic extracted into a function for Unit Testing
def query_rag_api(user_query, api_endpoint):
    """
    Sends the user query to the backend API and returns the JSON response.
    This function is 'Pure Logic' and can be tested/mutated.
    """
    if not user_query:
        return None
    
    try:
        payload = {"query": user_query}
        response = requests.post(api_endpoint, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Re-raise so the UI knows something broke
        raise e

def main():
    st.set_page_config(page_title="The Shakespearean Scholar")
    st.title("🎓 The Shakespearean Scholar")
    st.markdown("Retrieval-Augmented Generation (RAG) System for *Julius Caesar*.")

    question = st.text_input(
        "Ask a question about Julius Caesar:",
        placeholder="e.g., What is Brutus's main motivation for joining the conspiracy?"
    )

    if st.button("Ask the Scholar", type="primary"):
        if not question:
            st.warning("Please enter a question.")
        else:
            with st.spinner("Scholar is retrieving and generating answer..."):
                try:
                    # Call the testable function
                    result = query_rag_api(question, API_URL)
                    
                    answer = result.get("answer", "No answer generated.")
                    sources = result.get("sources", [])
                    
                    st.subheader("Scholar's Answer")
                    st.markdown(answer)
                    
                    if sources:
                        st.subheader("Textual Evidence (Sources)")
                        for i, source in enumerate(sources):
                            meta = source["metadata"]
                            text = source["chunk"]
                            with st.expander(f"Source {i+1}: Act {meta['act']}, Scene {meta['scene']}"):
                                st.text(text)
                                
                except requests.exceptions.HTTPError as e:
                    st.error(f"API Error: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()