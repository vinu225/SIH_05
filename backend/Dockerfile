# ==============================================================================
# AICTE Scrutiny Backend Dockerfile
# Production-ready multi-platform container for FastAPI Regulatory Engine
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    HOST=0.0.0.0 \
    AICTE_DATASET_DIR=/app/data/synthetic_scenarios

# Install system dependencies:
# - curl: Container healthchecks
# - libglib2.0-0, libgomp1: Native shared libraries for PyMuPDF & OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for optimal Docker layer caching
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source code, seed data, and test suite
COPY backend/app /app/app
COPY backend/data /app/data
COPY backend/tests /app/tests
COPY test_data /app/test_data

# Create non-root system user and configure file permissions
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Continuous health monitoring against API status endpoint
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Launch production ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
