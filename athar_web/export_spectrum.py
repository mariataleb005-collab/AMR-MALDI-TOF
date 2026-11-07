from pathlib import Path
import json
import numpy as np

# Original DRIAMS-A E. coli spectra
SOURCE = Path(
    r"C:\Users\maria\OneDrive\Desktop\ATHAR\data\raw\spectra_ecoli_A.npy"
)

# Website output
OUTPUT = (
    Path(__file__).resolve().parent
    / "static"
    / "data"
    / "representative_spectrum.json"
)

EXPECTED_BINS = 6000
SPECTRUM_INDEX = 0

def main():
    spectra = np.load(
        SOURCE,
        mmap_mode="r",
        allow_pickle=False
    )

    if spectra.ndim != 2 or spectra.shape[1] != EXPECTED_BINS:
        raise ValueError(
            f"Expected (samples, 6000), got {spectra.shape}"
        )

    spectrum = spectra[SPECTRUM_INDEX]

    # Bin centers: 2000 + (bin_index + 0.5) * 3 Da
    mz = [
        2000 + (i + 0.5) * 3
        for i in range(EXPECTED_BINS)
    ]

    output = {
        "source": "DRIAMS-A E. coli",
        "spectrum_index": SPECTRUM_INDEX,
        "representation": "Preprocessed 6000-bin spectrum",
        "mz": mz,
        "intensity": spectrum.astype(float).tolist()
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(output, file, separators=(",", ":"))

    print("Spectrum exported successfully.")
    print("Output:", OUTPUT)
    print("Number of bins:", len(mz))
    print("Maximum intensity:", float(spectrum.max()))


if __name__ == "__main__":
    main()
