#!/usr/bin/env bash
set -e

echo "✅ Starte FastAPI (Uvicorn) auf Port 8000"
uvicorn agent.api:app \
    --host 0.0.0.0 \
    --port 8000 &

echo "✅ Starte Streamlit auf Port 8080"
streamlit run streamlit_app.py \
    --server.port=8080 \
    --server.address=0.0.0.0

wait
