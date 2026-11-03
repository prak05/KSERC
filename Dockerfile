# KSERC Truing-Up Engine
# Stage 1 builds the React UI; stage 2 serves it and the API from one FastAPI process.

FROM node:22-alpine AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
# WeasyPrint needs Pango/Cairo for PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY src/ src/
COPY builder/ builder/
COPY templates/ templates/
COPY data/ data/
COPY documents/ documents/
COPY --from=ui /ui/dist frontend/dist

RUN useradd --create-home --uid 10001 kserc \
    && mkdir -p uploads output_orders \
    && chown -R kserc:kserc /app
USER kserc

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DOCUMENTS_DIR=/app/documents
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health').status==200 else 1)"
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT} --timeout-keep-alive 75"]
