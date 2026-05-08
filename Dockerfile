# SARANG Intelligence Swarm — Production Backend
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose the port (Railway uses $PORT env var automatically)
EXPOSE 8000

# Start the FastAPI engine using uvicorn
CMD ["uvicorn", "agents_service.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
