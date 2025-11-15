# Use a standard Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY frontend.py .

# Streamlit runs on port 8501 by default
EXPOSE 8501