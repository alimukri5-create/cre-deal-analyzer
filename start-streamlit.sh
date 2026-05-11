#!/bin/bash
# CRE Deal Analyzer — Streamlit App

cd "$(dirname "$0")"

# Check if venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install Streamlit + deps if not present
pip install -q streamlit 2>/dev/null || pip install streamlit

# Install CRE analyzer deps
cd ../cre-analyzer
pip install -q -r requirements.txt 2>/dev/null || true
cd ../cre-analyzer-app

echo ""
echo "🚀 Starting CRE Deal Analyzer (Streamlit)..."
echo "Local URL: http://localhost:8501"
echo ""

streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
