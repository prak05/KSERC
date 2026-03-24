# ============================================================
# KSERC Truing-Up Engine — Cloud Run Dockerfile
# Multi-stage: Build React frontend → Serve with Python FastAPI
# ============================================================

# ── Stage 1: Build React Frontend ─────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --production=false

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python Backend + Static Frontend ─────────────────
FROM python:3.11-slim

# Install system dependencies for WeasyPrint and general use
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    libcairo2-dev \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

# Create necessary directories
RUN mkdir -p uploads output_orders data

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV DOCUMENTS_DIR=/app/Documents
ENV GCS_BUCKET=kserc-regulatory-docs-v2

# Expose Cloud Run port
EXPOSE 8080

# Start the server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
