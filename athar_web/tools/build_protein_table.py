"""Build athar_web/data/uniprot_candidates.csv: candidate E. coli K-12 proteins for all 600 m/z regions.

Run once from the repository root (needs internet, takes about 10-20 minutes):
    python -m athar_web.tools.build_protein_table

It sends two UniProtKB queries per region (see athar_web/proteins.py for the mass windows) and writes
one row per region and matching protein. The table does not depend on the model, so it never has to be
rebuilt when a model changes. Re-running it overwrites the file.
"""
import csv
import io
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from athar_web.proteins import TABLE, mass_windows, uniprot_query

API = "https://rest.uniprot.org/uniprotkb/search"
FIELDS = "accession,id,protein_name,gene_primary,mass"
N_REGIONS = 600
MAX_PER_WINDOW = 50


def fetch(query, tries=4):
    params = urllib.parse.urlencode({"query": query, "fields": FIELDS, "format": "tsv", "size": MAX_PER_WINDOW})
    request = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": "ATHAR-protein-table/1.0"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == tries - 1:
                raise
            wait = 2 ** attempt
            print(f"  retrying in {wait} s ({error})", flush=True)
            time.sleep(wait)


def parse(tsv):
    rows = list(csv.DictReader(io.StringIO(tsv), delimiter="\t"))
    return [{"accession": r["Entry"], "entry_name": r["Entry Name"], "protein": r["Protein names"],
             "gene": r.get("Gene Names (primary)", ""), "mass": r["Mass"]} for r in rows]


def main():
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    columns = ["region", "mz_from", "mz_to", "ion", "accession", "entry_name", "protein", "gene", "mass"]
    total = 0
    with TABLE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for region in range(N_REGIONS):
            mz_from, mz_to = 2000 + 30 * region, 2000 + 30 * (region + 1)
            for ion, low, high in mass_windows(region):
                for hit in parse(fetch(uniprot_query(low, high))):
                    # UniProt rounds masses to whole daltons, so keep only exact window matches.
                    if low <= float(hit["mass"]) < high:
                        writer.writerow({"region": region, "mz_from": mz_from, "mz_to": mz_to, "ion": ion, **hit})
                        total += 1
                time.sleep(0.1)
            if region % 50 == 0:
                print(f"region {region} of {N_REGIONS}, {total} matches so far", flush=True)
    print(f"Done: {total} matches written to {TABLE}")


if __name__ == "__main__":
    sys.exit(main())
