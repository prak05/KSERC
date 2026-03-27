#!/bin/bash
# ============================================================
# KSERC SDL Truing-Up Engine — Local Development Startup
# ============================================================
# Starts both the FastAPI backend (port 8000) and
# the Vite/React frontend (port 3000) in parallel.
#
# Usage:  ./start.sh
# App:    http://localhost:3000
# API:    http://localhost:8000/api/health
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   KSERC SDL Truing-Up Engine — Starting...   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Backend (FastAPI) ─────────────────────────────────────
echo "▶  Starting FastAPI backend on http://localhost:8000 ..."
uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Give the backend 3 seconds to boot before starting frontend
sleep 3

# ── Frontend (Vite + React) ───────────────────────────────
echo "▶  Starting React frontend on http://localhost:3000 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✔  Backend  →  http://localhost:8000  (PID: $BACKEND_PID)"
echo "✔  Frontend →  http://localhost:3000  (PID: $FRONTEND_PID)"
echo ""
echo "   Press Ctrl+C to stop both servers."
echo ""

# ── Graceful shutdown ─────────────────────────────────────
cleanup() {
    echo ""
    echo "⏹  Stopping servers..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    echo "✔  Done."
}

trap cleanup EXIT INT TERM
wait
