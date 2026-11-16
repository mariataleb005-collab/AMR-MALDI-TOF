"""Candidate E. coli proteins for each m/z region.

The table athar_web/data/uniprot_candidates.csv is built once with tools/build_protein_table.py, which
queries UniProtKB (reviewed E. coli K-12 entries) by mass for all 600 regions. Without that file the
app still links each region to a live UniProt search over the same mass window.

A MALDI-TOF peak in this range is mostly a singly protonated protein, [M+H]+, so a peak at m/z x comes
from a protein of mass about x - 1.007 Da. Many E. coli proteins also lose their first methionine
(131.04 Da), so a second window looks for full-length entries 131.04 Da heavier. A match is a lead to
follow up, not an identification.
"""
import csv
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

TABLE = Path(__file__).resolve().parent / "data" / "uniprot_candidates.csv"
PROTON = 1.00728
MET = 131.04049
TAXON = 83333            # Escherichia coli K-12


def region_mz(region):
    return 2000 + 30 * region, 2000 + 30 * (region + 1)


def mass_windows(region):
    """(label, low, high) protein-mass windows in Da for one region."""
    lo, hi = region_mz(region)
    return [("[M+H]+", lo - PROTON, hi - PROTON),
            ("[M+H]+ after N-terminal Met removal", lo - PROTON + MET, hi - PROTON + MET)]


def uniprot_query(low, high):
    return f"organism_id:{TAXON} AND reviewed:true AND mass:[{int(low)} TO {int(high) + 1}]"


def uniprot_search_url(region):
    _, low, high = mass_windows(region)[0]
    return "https://www.uniprot.org/uniprotkb?query=" + quote(uniprot_query(low, high))


def entry_links(accession):
    return {
        "uniprot": f"https://www.uniprot.org/uniprotkb/{accession}/entry",
        "alphafold": f"https://alphafold.ebi.ac.uk/entry/{accession}",
        "blast": f"https://blast.ncbi.nlm.nih.gov/Blast.cgi?PAGE_TYPE=BlastSearch&PROGRAM=blastp&QUERY={accession}",
    }


@lru_cache(maxsize=1)
def _table():
    if not TABLE.is_file():
        return None
    out = {}
    with TABLE.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            out.setdefault(int(row["region"]), []).append(row)
    return out


def table_available():
    return _table() is not None


def candidates(region):
    rows = (_table() or {}).get(int(region), [])
    return [dict(row, links=entry_links(row["accession"])) for row in rows]
