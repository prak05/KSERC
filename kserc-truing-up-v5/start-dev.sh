#!/usr/bin/env bash
# ============================================================
# KSERC Truing-Up v5 — Development Startup Script
# Starts both the Python backend (FastAPI) and Next.js frontend
# ============================================================

set -e
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    KSERC Truing-Up v5 — Starting Services        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Check Python environment ──────────────────────────────
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "Activating Python venv..."
source .venv/bin/activate
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Copy vertex_sa.json from adwaith if it exists
ADWAITH_KEY="/home/prak05/Desktop/ProductionKSERC/adwaith/vertex_sa.json"
if [ -f "$ADWAITH_KEY" ] && [ ! -f "$BACKEND_DIR/vertex_sa.json" ]; then
    echo "Copying vertex_sa.json from adwaith project..."
    cp "$ADWAITH_KEY" "$BACKEND_DIR/vertex_sa.json"
fi

# ── 2. Start Python FastAPI backend in background ────────────
echo ""
echo "▶  Starting Python backend on http://localhost:8000 ..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"
sleep 2

# ── 3. Start Next.js frontend ───────────────────────────────
cd "$PROJECT_DIR"
echo ""
echo "▶  Starting Next.js frontend on http://localhost:3000 ..."
npm run dev &
FRONTEND_PID=$!
echo "   PID: $FRONTEND_PID"

echo ""
echo "✓  Both services started!"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services."
echo ""

# ── Cleanup on exit ─────────────────────────────────────────
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Services stopped.'" EXIT
wait
