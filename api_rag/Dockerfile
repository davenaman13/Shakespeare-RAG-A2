# Use a lightweight Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .

# ⬇️ 🛠️ CRITICAL FIX FOR MAC M-SERIES HANGS 🛠️ ⬇️
# Install specific, stable CPU versions of torch and numpy first to avoid architecture issues.
# This prevents silent crashes/hangs in the embedding model loading.
RUN pip install --no-cache-dir "torch==2.3.1" "numpy==1.26.4"

# Install the remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the uvicorn server
CMD ["uvicorn", "api_rag:app", "--host", "0.0.0.0", "--port", "8000"]