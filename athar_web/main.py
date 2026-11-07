from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import csv
from pathlib import PurePath
from io import StringIO
from fastapi.responses import StreamingResponse
from .history_db import initialize, save_analysis, get_analyses
from .predict import parse_spectrum, predict_resistance

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="ATHAR",
    description="Antimicrobial Resistance Prediction from MALDI-TOF Spectra",
    version="0.2.0",
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")

initialize()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="predict.html",
        context={"page_title": "Predict"},
    )


@app.post("/api/predict")
async def predict(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    try:
        # Read at most 2 MB + 1 byte.
        file_bytes = await file.read(2_000_001)

        spectrum = parse_spectrum(file_bytes, file.filename)
        predictions = predict_resistance(spectrum)
        # Store only the safe filename, never the uploaded spectrum itself.
        safe_filename = file.filename.replace('\\', '/').split('/')[-1][:200]
        analysis_id = save_analysis(safe_filename, len(spectrum), predictions)

        return {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "feature_count": len(spectrum),
            "mode": "simulation",
            "predictions": predictions,
            "disclaimer": (
                "Simulated results only. Not a validated "
                "machine learning or clinical prediction."
            ),
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    finally:
        await file.close()


ANTIBIOTICS = [
    "Ciprofloxacin",
    "Ceftriaxone",
    "Cefepime",
    "Piperacillin-Tazobactam",
    "Tobramycin",
    "Ampicillin-Amoxicillin",
]

RESULTS_DIR = BASE_DIR.parent / "results"


@app.get("/regions", response_class=HTMLResponse)
async def regions_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="regions.html",
        context={"page_title": "Regions"},
    )


@app.get("/api/regions/{antibiotic}")
async def get_regions(antibiotic: str):
    if antibiotic not in ANTIBIOTICS:
        raise HTTPException(
            status_code=404,
            detail="Unknown antibiotic."
        )

    csv_path = RESULTS_DIR / f"step3_regions_{antibiotic}.csv"

    if not csv_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Region results are not available."
        )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    return {
        "antibiotic": antibiotic,
        "regions": [
            {
                "region": int(row["region"]),
                "mz_from": float(row["mz_from"]),
                "mz_to": float(row["mz_to"]),
                "peak_mz": float(row["peak_mz"]),
                "ra_pso_seeds": int(row["RA-PSO_seeds"]),
                "importance": float(row["dAUPRC_if_removed"]),
                "direction": row["direction"],
            }
            for row in rows
        ],
    }


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"page_title": "History"},
    )


@app.get("/api/history")
async def history_records():
    records = get_analyses()
    return {"records": records, "count": len(records)}


@app.get("/api/history/export")
async def export_history():
    records = get_analyses()
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["analysis_id", "created_at_utc", "filename", "mode", "antibiotic", "result"])
    for record in records:
        for antibiotic, result in record["predictions"].items():
            writer.writerow([record["id"], record["created_at"], record["filename"],
                             record["mode"], antibiotic, result])
    return StreamingResponse(
        iter([buffer.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="athar_demo_history.csv"'},
    )

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"page_title": "About"},
    )