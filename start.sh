#!/bin/bash

echo "🚀 Démarrage de DocFlow..."

# Vérification du backend
if [ ! -d "backend/.venv" ]; then
    echo "📦 Initialisation du backend..."
    cd backend && uv sync && cd ..
fi

# Vérification du frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Initialisation du frontend..."
    cd frontend && npm install && cd ..
fi

# Démarrage du backend en arrière-plan
echo "🔥 Lancement du Backend (Port 8000)..."
cd backend && uv run uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Démarrage du frontend
echo "💻 Lancement du Frontend (Port 5173)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

function cleanup {
    echo "🛑 Arrêt des services..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit
}

trap cleanup SIGINT

echo "✅ DocFlow est prêt !"
echo "👉 Frontend : http://localhost:5173"
echo "👉 API Docs : http://localhost:8000/docs"

wait
