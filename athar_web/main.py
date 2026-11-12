import csv
from io import StringIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .history_db import get_analyses, get_analysis, initialize, save_analysis
from .predict import MAX_BYTES, parse_spectrum
from .registry import Registry
from .spectrum_trace import trace_path

BASE_DIR = Path(__file__).resolve().parent
SPECIES = "Escherichia coli"

app = FastAPI(
    title="ATHAR",
    description="Antibiotic resistance prediction from E. coli MALDI-TOF spectra",
    version="0.3.0",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["trace_path"] = trace_path

registry = Registry()
initialize()


def page(request, name, title, **context):
    return templates.TemplateResponse(request=request, name=name, context={"page_title": title, **context})


# ---------------------------------------------------------------- pages

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return page(request, "predict.html", "Analyze",
                antibiotics=registry.catalogue(), installed_count=len(registry.installed))


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return page(request, "history.html", "History")


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return page(request, "about.html", "About", antibiotics=registry.catalogue())


# ---------------------------------------------------------------- API

@app.get("/api/antibiotics")
async def antibiotics():
    return {"antibiotics": registry.catalogue(), "installed": len(registry.installed)}


@app.post("/api/predict")
async def predict(
    file: UploadFile = File(...),
    sample_id: str = Form(""),
    species: str = Form(SPECIES),
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file name was provided.")
        if species != SPECIES:
            raise HTTPException(
                status_code=400,
                detail="ATHAR's models were trained on Escherichia coli only, "
                       "so no prediction is made for other species.",
            )
        file_bytes = await file.read(MAX_BYTES + 1)
        try:
            spectrum = parse_spectrum(file_bytes, file.filename)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
    finally:
        await file.close()

    if not registry.installed:
        raise HTTPException(
            status_code=503,
            detail="The spectrum file is valid, but no prediction model is installed yet.",
        )

    sample_id = sample_id.strip()[:40]
    safe_filename = file.filename.replace("\\", "/").split("/")[-1][:200]
    results = registry.predict(spectrum)
    analysis_id = save_analysis(sample_id, species, safe_filename, len(spectrum), results)

    return {
        "analysis_id": analysis_id,
        "sample_id": sample_id,
        "species": species,
        "filename": safe_filename,
        "results": results,
        "not_installed": [a for a in registry.catalogue() if a["status"] != "installed"],
    }


@app.get("/api/history")
async def history_records():
    records = get_analyses()
    return {"records": records, "count": len(records)}


@app.get("/api/history/export")
async def export_history():
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["analysis_id", "created_at_utc", "sample_id", "species", "filename",
                     "antibiotic", "call", "score", "score_type", "threshold", "model_version"])
    for record in get_analyses():
        for r in record["results"]:
            writer.writerow([record["id"], record["created_at"], record["sample_id"], record["species"],
                             record["filename"], r["antibiotic"], r["call"], r["score"], r["score_type"],
                             r["threshold"], r["model_version"]])
    return StreamingResponse(
        iter([buffer.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="athar_history.csv"'},
    )


@app.get("/api/history/{analysis_id}")
async def history_record(analysis_id: int):
    record = get_analysis(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No analysis with this number.")
    return record
