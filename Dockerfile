FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy CRE analyzer first (dependency)
COPY cre-analyzer/requirements.txt /tmp/cre-req.txt
RUN pip install --no-cache-dir -r /tmp/cre-req.txt || true

# Copy app requirements
COPY cre-analyzer-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY cre-analyzer/src/ /app/cre-analyzer/src/
COPY cre-analyzer-app/api/ /app/api/
COPY cre-analyzer-app/templates/ /app/templates/
COPY cre-analyzer-app/static/ /app/static/

# Create output dirs
RUN mkdir -p /tmp/cre-uploads /tmp/cre-results

ENV PYTHONPATH=/app/cre-analyzer/src:$PYTHONPATH

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
