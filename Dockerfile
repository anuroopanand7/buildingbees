# Dockerfile for BuildingBees - Google Cloud Run Deployment
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY pyproject.toml requirements.txt* ./

# Install python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    networkx \
    httpx

# Copy source code and web frontend
COPY src/ ./src/
COPY web/ ./web/

# Set environment variables
ENV PORT=8080
ENV PYTHONPATH=/app

EXPOSE 8080

# Run FastAPI production server
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
