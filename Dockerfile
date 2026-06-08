# RAG query API image. Geo + AI extras are layered in later phases.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir -e ".[serve]"

# Placeholder until the RAG query service lands (roadmap phase 11).
CMD ["python", "-c", "import aegis; print('aegis', aegis.__version__)"]
