"""Write athar_web/static/data/representative_spectrum.json from the DRIAMS-A E. coli spectra.

The site uses this spectrum for the trace on the home page, the mark next to the name and the
"Use an example spectrum" button. Run from the repository root, with the same data folder the
experiment scripts use:

    python -m athar_web.tools.export_example_spectrum "<spectra folder>" --index 0
"""
import argparse
import json
from pathlib import Path

import numpy as np

N_BINS = 6000
OUTPUT = Path(__file__).resolve().parent.parent / "static" / "data" / "representative_spectrum.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data_dir", help="folder that holds spectra_ecoli_A.npy")
    parser.add_argument("--index", type=int, default=0, help="row of the spectrum to export (default 0)")
    args = parser.parse_args()

    spectra = np.load(Path(args.data_dir) / "spectra_ecoli_A.npy", mmap_mode="r", allow_pickle=False)
    if spectra.ndim != 2 or spectra.shape[1] != N_BINS:
        raise SystemExit(f"Expected an array of shape (spectra, {N_BINS}), got {spectra.shape}")

    spectrum = np.asarray(spectra[args.index], dtype=float)
    output = {
        "source": "DRIAMS-A E. coli",
        "spectrum_index": args.index,
        "representation": "Preprocessed 6000-bin spectrum",
        "mz": [2000 + (i + 0.5) * 3 for i in range(N_BINS)],      # bin centres
        "intensity": spectrum.tolist(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, separators=(",", ":")), encoding="utf-8")
    print(f"Spectrum {args.index} written to {OUTPUT} (maximum intensity {spectrum.max():.5f})")


if __name__ == "__main__":
    main()
