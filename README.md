# CRE Deal Analyzer App

Web application for institutional-grade commercial real estate deal analysis.

## Features

- 📄 **PDF Upload** — Drag-and-drop investment memorandums
- 🔍 **Automatic Analysis** — Extracts metrics, researches tenant, finds market comps
- 🛰️ **Satellite Imagery** — Aerial view + parking lot analysis via OpenCV
- 📊 **Risk Scoring** — Multi-factor deal scoring with verdict
- 📄 **Markdown Reports** — Downloadable full analysis reports

## Quick Start

```bash
cd cre-analyzer-app
./start.sh
```

Open http://localhost:8000 in your browser.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/api/analyze` | POST | Upload PDF, start analysis |
| `/api/results/{id}` | GET | Poll for results |
| `/api/reports/{id}/report` | GET | Download markdown report |
| `/api/reports/{id}/satellite` | GET | View satellite imagery |

## Architecture

```
Frontend (HTML/JS)
    ↓
FastAPI Backend
    ↓
CRE Analyzer Pipeline (existing Python modules)
    ├── PDF Ingestor
    ├── Tenant Research (kimi_search)
    ├── Market Comps (kimi_search)
    ├── Satellite Analyzer (ESRI + OpenCV)
    └── Risk Scorer
```

## Data Flow

1. User uploads PDF via web UI
2. Backend extracts deal metrics
3. `kimi_search` researches tenant financials
4. `kimi_search` gathers market comparables
5. Satellite imagery downloaded and analyzed
6. Risk score calculated
7. Results displayed in dashboard + downloadable report

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Frontend**: Vanilla HTML/JS (dark theme)
- **Analysis**: Existing CRE analyzer pipeline
- **Search**: kimi_search (instead of broken DDG scraping)
- **Imagery**: ESRI World Imagery tiles + OpenCV

## Docker (Optional)

```bash
docker build -t cre-analyzer .
docker run -p 8000:8000 cre-analyzer
```

## Development

The app reuses the existing `cre-analyzer/` pipeline. Key integration points:

- `api/main.py` imports from `cre-analyzer/src/`
- `injected_data.json` bridges kimi_search results into the pipeline
- Satellite images saved to `/tmp/cre-results/{job_id}/`

## Known Limitations

- Rightmove/Zoopla scraping blocked (403) — using kimi_search instead
- DDG search unreliable for UK CRE data — kimi_search is primary engine
- Requires internet access for satellite tiles and web search
