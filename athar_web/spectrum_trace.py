"""SVG path of the example DRIAMS-A spectrum, used as ATHAR's visual identity.

The path is computed once from static/data/representative_spectrum.json, so the
trace on every page is a real measured spectrum, not a drawing.
"""
import json
from functools import lru_cache
from pathlib import Path

SPECTRUM_JSON = Path(__file__).resolve().parent / "static" / "data" / "representative_spectrum.json"


@lru_cache(maxsize=None)
def _intensity():
    with SPECTRUM_JSON.open(encoding="utf-8") as file:
        return json.load(file)["intensity"]


@lru_cache(maxsize=None)
def trace_path(width=1200, height=120, first_bin=0, last_bin=6000, columns=600, gamma=0.75):
    """Return an SVG path 'd' string: one point per column, using the maximum bin in each column.

    gamma < 1 lifts small peaks so the trace stays readable at small sizes.
    """
    values = _intensity()[first_bin:last_bin]
    per_column = max(1, len(values) // columns)
    peaks = [max(values[i:i + per_column]) for i in range(0, len(values), per_column)]
    top = max(peaks) or 1.0
    step = width / (len(peaks) - 1)
    points = []
    for i, value in enumerate(peaks):
        y = height - (value / top) ** gamma * (height - 2)
        points.append(f"{i * step:.1f} {y:.1f}")
    return "M" + " L".join(points)
