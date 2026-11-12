import csv
import io
import math

EXPECTED_FEATURES = 6000
MAX_BYTES = 2_000_000


def parse_spectrum(file_bytes: bytes, filename: str) -> list[float]:
    """Read a preprocessed DRIAMS-style spectrum: 6,000 binned intensities (3 Da bins, 2,000-20,000 Da)."""
    extension = filename.lower().rsplit(".", 1)[-1]

    if extension not in {"csv", "txt"}:
        raise ValueError("Only .csv and .txt files are supported.")

    if not file_bytes or len(file_bytes) > MAX_BYTES:
        raise ValueError("The file must be non-empty and smaller than 2 MB.")

    try:
        content = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("The file must contain UTF-8 text.")

    try:
        rows = list(csv.reader(io.StringIO(content)))
        values = [float(cell.strip()) for row in rows for cell in row if cell.strip()]
    except (ValueError, csv.Error):
        raise ValueError("The spectrum must contain numeric intensity values only.")

    if len(values) != EXPECTED_FEATURES:
        raise ValueError(f"Expected {EXPECTED_FEATURES} intensity values, but the file has {len(values)}.")

    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Intensity values must be finite and non-negative.")

    return values
