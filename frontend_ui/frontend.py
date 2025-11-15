import streamlit as st
import requests
import json

# --- Configuration ---
# IMPORTANT: Use the Docker service name 'rag-api' as the hostname, 
# not 'localhost' or '0.0.0.0', as services talk to each other inside the Docker network.
API_URL = "http://rag-api:8000/query" 

st.set_page_config(page_title="The Shakespearean Scholar")

# --- UI Setup ---
st.title("🎓 The Shakespearean Scholar")
st.markdown("Retrieval-Augmented Generation (RAG) System for *Julius Caesar*.")

# User Input
question = st.text_input(
    "Ask a question about Julius Caesar:",
    placeholder="e.g., What is Brutus's main motivation for joining the conspiracy?"
)

# Button to submit query
if st.button("Ask the Scholar", type="primary"):
    if not question:
        st.warning("Please enter a question.")
    else:
        with st.spinner("Scholar is retrieving and generating answer..."):
            try:
                # 1. Prepare payload
                payload = {"query": question}
                
                # 2. Call the FastAPI RAG service
                response = requests.post(API_URL, json=payload, timeout=90)
                response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
                
                # 3. Process the response
                result = response.json()
                answer = result.get("answer", "No answer generated.")
                sources = result.get("sources", [])
                
                # --- Display Results ---
                st.subheader("Scholar's Answer")
                st.markdown(answer)
                
                if sources:
                    st.subheader("Textual Evidence (Sources)")
                    for i, source in enumerate(sources):
                        meta = source["metadata"]
                        text = source["chunk"]
                        
                        with st.expander(f"Source {i+1}: Act {meta['act']}, Scene {meta['scene']} (Speaker: {meta['speaker']})"):
                            st.text(text)
                            
            except requests.exceptions.HTTPError as e:
                st.error(f"API Error (Status {e.response.status_code}): Could not retrieve answer. Check container logs.")
            except requests.exceptions.ConnectionError:
                st.error("Connection Error: Could not connect to the RAG API. Ensure the 'rag-api' container is running.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")