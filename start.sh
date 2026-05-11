#!/bin/bash
# CRE Deal Analyzer App - Startup Script

cd "$(dirname "$0")"

# Check if venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Also need the CRE analyzer dependencies
cd ../cre-analyzer
pip install -r requirements.txt 2>/dev/null || true
cd ../cre-analyzer-app

echo "Starting CRE Deal Analyzer API..."
echo "Open http://localhost:8000 in your browser"
echo ""

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
