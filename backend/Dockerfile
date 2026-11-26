FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Optional sentence-transformers CPU support
RUN pip install --no-cache-dir sentence-transformers --extra-index-url https://download.pytorch.org/whl/cpu || true

RUN useradd --create-home --uid 1000 appuser

COPY backend /app/backend
COPY database /app/database
COPY data_warehouse /app/data_warehouse
COPY ingestion /app/ingestion
COPY ml /app/ml
COPY research_assistant /app/research_assistant
COPY analytics /app/analytics
COPY evaluation /app/evaluation
COPY scripts /app/scripts

RUN mkdir -p /app/data /app/data_warehouse/duckdb /app/evaluation/results /app/.cache/huggingface \
    && chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app
ENV HF_HOME=/app/.cache/huggingface
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-graceful-shutdown", "15"]
