from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import uuid
import json
import sys
from datetime import datetime

# Add existing CRE analyzer to path
CRE_DIR = Path(__file__).parent.parent / "cre-analyzer"
SRC_DIR = CRE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

app = FastAPI(title="CRE Deal Analyzer", version="1.0.0")

# Setup directories
UPLOAD_DIR = Path("/tmp/cre-uploads")
RESULTS_DIR = Path("/tmp/cre-results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Mount static files
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent.parent / "static")), name="static")

# In-memory job store (use Redis in production)
jobs = {}


@app.get("/", response_class=HTMLResponse)
async def root():
    return templates.TemplateResponse("index.html", {"request": {}})


@app.post("/api/analyze")
async def analyze_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a PDF investment memorandum and start analysis."""
    job_id = str(uuid.uuid4())
    
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files accepted")
    
    # Save upload
    upload_path = UPLOAD_DIR / f"{job_id}.pdf"
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Initialize job
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "filename": file.filename,
        "uploaded_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
    }
    
    # Start background analysis
    background_tasks.add_task(run_analysis, job_id, upload_path)
    
    return {"job_id": job_id, "status": "queued", "check_url": f"/api/results/{job_id}"}


@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    """Get analysis results for a job."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    
    job = jobs[job_id]
    
    if job["status"] == "completed":
        return {
            "job_id": job_id,
            "status": "completed",
            "result": job["result"],
            "report_url": f"/api/reports/{job_id}/report",
            "satellite_url": f"/api/reports/{job_id}/satellite",
        }
    elif job["status"] == "failed":
        return {"job_id": job_id, "status": "failed", "error": job["error"]}
    else:
        return {"job_id": job_id, "status": job["status"]}


@app.get("/api/reports/{job_id}/report")
async def get_report(job_id: str):
    """Download the generated markdown report."""
    report_path = RESULTS_DIR / job_id / "report.md"
    if not report_path.exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(report_path, media_type="text/markdown", filename=f"CRE_Analysis_{job_id}.md")


@app.get("/api/reports/{job_id}/satellite")
async def get_satellite(job_id: str):
    """View satellite imagery."""
    satellite_dir = RESULTS_DIR / job_id
    satellite_files = list(satellite_dir.glob("satellite_*.jpg"))
    if not satellite_files:
        raise HTTPException(404, "Satellite image not found")
    # Return the annotated one if available, otherwise the raw
    annotated = [f for f in satellite_files if "annotated" in f.name]
    target = annotated[0] if annotated else satellite_files[0]
    return FileResponse(target, media_type="image/jpeg")


def run_analysis(job_id: str, pdf_path: Path):
    """Background task to run CRE analysis."""
    try:
        jobs[job_id]["status"] = "processing"
        
        # Create output directory
        output_dir = RESULTS_DIR / job_id
        output_dir.mkdir(exist_ok=True)
        
        # Import and run analyzer
        from analyzer import CREAnalyzer
        
        analyzer = CREAnalyzer(str(pdf_path))
        result = analyzer.analyze()
        
        # Copy outputs to results dir
        cre_output = CRE_DIR / "output"
        if cre_output.exists():
            for f in cre_output.iterdir():
                if f.is_file():
                    shutil.copy2(f, output_dir)
        
        # Parse report for key metrics
        report_path = output_dir / "report.md"
        summary = extract_summary(report_path) if report_path.exists() else {}
        
        # Load analysis.json if available
        analysis_json = output_dir / "analysis.json"
        analysis_data = {}
        if analysis_json.exists():
            with open(analysis_json) as f:
                analysis_data = json.load(f)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "summary": summary,
            "analysis": analysis_data,
            "files": {
                "report": f"/api/reports/{job_id}/report",
                "satellite": f"/api/reports/{job_id}/satellite",
            }
        }
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def extract_summary(report_path: Path) -> dict:
    """Extract key metrics from generated report."""
    summary = {}
    try:
        with open(report_path, 'r') as f:
            content = f.read()
        
        # Extract verdict
        if "Verdict:" in content:
            verdict_match = content.split("Verdict:")[1].split("\n")[0].strip()
            summary["verdict"] = verdict_match
        
        # Extract score
        if "Score:" in content:
            score_match = content.split("Score:")[1].split("/")[0].strip()
            summary["score"] = score_match
        
        # Extract key metrics
        lines = content.split('\n')
        for line in lines:
            if '| Asking Price |' in line:
                summary["asking_price"] = line.split('|')[2].strip()
            elif '| Price / sq ft |' in line:
                summary["price_psf"] = line.split('|')[2].strip()
            elif '| Net Initial Yield |' in line:
                summary["niy"] = line.split('|')[2].strip()
            elif '| Tenant |' in line:
                summary["tenant"] = line.split('|')[2].strip()
                
    except Exception:
        pass
    
    return summary


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
