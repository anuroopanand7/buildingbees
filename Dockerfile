# BuildingBees on Google Cloud Run
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY web/ ./web/

# Cloud Run sets PORT (8080 by default)
CMD ["sh", "-c", "uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
