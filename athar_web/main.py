from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

        return {
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
