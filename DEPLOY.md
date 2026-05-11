# 🏢 CRE Deal Analyzer

**Institutional-grade commercial real estate analysis, deployed on Streamlit Cloud.**

Upload a PDF investment memorandum → get tenant research, market comparables, satellite imagery analysis, and risk scoring.

---

## Deploy to Streamlit Cloud (Public URL)

### Step 1: Push to GitHub

Create a new public GitHub repo (e.g. `cre-deal-analyzer`), then push this code:

```bash
# From your local machine after cloning/downloading this folder:
cd cre-analyzer-app
git init
git add .
git commit -m "Initial deploy"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/cre-deal-analyzer.git
git push -u origin main
```

### Step 2: Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**
4. Select your `cre-deal-analyzer` repo
5. **Main file path:** `streamlit_app.py`
6. Click **Deploy**

Streamlit Cloud will auto-install dependencies from `requirements.txt` and system packages from `packages.txt`.

Your app will be live at:
```
https://cre-deal-analyzer-YOUR_USERNAME.streamlit.app
```

---

## Run Locally

```bash
cd cre-analyzer-app
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open http://localhost:8501

---

## Architecture

```
cre-analyzer-app/
├── streamlit_app.py          # Main Streamlit UI
├── cre_analyzer/             # Analysis engine (self-contained)
│   ├── pdf_ingestor.py       # PDF extraction
│   ├── tenant_research.py    # DDG-based tenant research
│   ├── market_comp.py        # DDG-based market comparables
│   ├── satellite_analyzer.py # ESRI satellite imagery
│   ├── risk_scorer.py        # Risk scoring engine
│   └── report_generator.py   # Markdown report output
├── requirements.txt          # Python deps
├── packages.txt              # System deps (libgl1 for OpenCV)
└── .streamlit/config.toml    # Dark theme
```

---

## Data Sources

- **Tenant Research:** Web search (DuckDuckGo) for store counts, parent companies, financials
- **Market Comps:** Web search for rent psf, vacancy rates, demand indicators
- **Satellite Imagery:** ESRI World Imagery tiles (free, no API key)
- **Geocoding:** Nominatim OpenStreetMap

---

## Notes

- PDFs with scanned pages (images) won't extract text — use OCR-first PDFs
- Satellite analysis is heuristic (parking lot detection via OpenCV)
- Market rent data is web-scraped; verify against actual transactions
