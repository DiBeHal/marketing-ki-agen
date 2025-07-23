#!/bin/bash
echo "✅ Starte Streamlit über Port 8080 für Railway"
streamlit run streamlit_app.py --server.port=8080 --server.address=0.0.0.0
