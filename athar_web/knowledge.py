"""Reference information and outside links for each antibiotic.

WHO AWaRe groups are taken from the WHO AWaRe antibiotic list (https://aware.essentialmeds.org/list).
"""
from urllib.parse import quote

AWARE_LIST_URL = "https://aware.essentialmeds.org/list"
EUCAST_BREAKPOINTS_URL = "https://www.eucast.org/clinical_breakpoints"
CARD_URL = "https://card.mcmaster.ca/"
KEGG_BETA_LACTAM_URL = "https://www.kegg.jp/entry/map01501"

# antibiotic: (WHO AWaRe group, PubChem compound names, CARD drug class, beta-lactam?)
INFO = {
    "Ciprofloxacin": ("Watch", ["ciprofloxacin"], "fluoroquinolone antibiotic", False),
    "Cefepime": ("Watch", ["cefepime"], "cephalosporin", True),
    "Cotrimoxazole": ("Access", ["sulfamethoxazole", "trimethoprim"],
                      "sulfonamide antibiotic; diaminopyrimidine antibiotic", False),
    "Levofloxacin": ("Watch", ["levofloxacin"], "fluoroquinolone antibiotic", False),
    "Ceftazidime": ("Watch", ["ceftazidime"], "cephalosporin", True),
    "Ceftriaxone": ("Watch", ["ceftriaxone"], "cephalosporin", True),
    "Tobramycin": ("Watch", ["tobramycin"], "aminoglycoside antibiotic", False),
    "Amikacin": ("Access", ["amikacin"], "aminoglycoside antibiotic", False),
    "Amoxicillin-Clavulanic acid": ("Access", ["amoxicillin", "clavulanic acid"], "penam; beta-lactamase inhibitor", True),
    "Piperacillin-Tazobactam": ("Watch", ["piperacillin", "tazobactam"], "penam; beta-lactamase inhibitor", True),
    "Ampicillin-Amoxicillin": ("Access", ["ampicillin", "amoxicillin"], "penam", True),
    "Cefpodoxime": ("Watch", ["cefpodoxime"], "cephalosporin", True),
    "Norfloxacin": ("Watch", ["norfloxacin"], "fluoroquinolone antibiotic", False),
}

AWARE_MEANING = {
    "Access": "First- or second-choice antibiotic for common infections, with lower resistance potential.",
    "Watch": "Higher resistance potential; WHO recommends prioritising it in stewardship programmes.",
    "Reserve": "Last-resort antibiotic for multidrug-resistant infections.",
}


def slug(antibiotic):
    return antibiotic.lower().replace(" ", "-")


def from_slug(value, antibiotics):
    for name in antibiotics:
        if slug(name) == value:
            return name
    return None


def links(antibiotic):
    aware, compounds, card_class, beta_lactam = INFO[antibiotic]
    out = [{"label": f"PubChem: {c}", "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{quote(c)}",
            "note": "Structure and pharmacology"} for c in compounds]
    if beta_lactam:
        out.append({"label": "KEGG: beta-lactam resistance pathway (map01501)", "url": KEGG_BETA_LACTAM_URL,
                    "note": "Resistance mechanisms for beta-lactam antibiotics"})
    out.append({"label": "CARD: Comprehensive Antibiotic Resistance Database", "url": CARD_URL,
                "note": f"Search for the drug class: {card_class}"})
    out.append({"label": "EUCAST clinical breakpoints", "url": EUCAST_BREAKPOINTS_URL,
                "note": "Breakpoints used to call S, I and R in the laboratory"})
    out.append({"label": "WHO AWaRe antibiotic list", "url": AWARE_LIST_URL,
                "note": f"Listed in the {aware} group"})
    return out


def details(antibiotic):
    aware, compounds, card_class, beta_lactam = INFO[antibiotic]
    return {"aware": aware, "aware_meaning": AWARE_MEANING[aware], "card_class": card_class,
            "beta_lactam": beta_lactam, "links": links(antibiotic), "slug": slug(antibiotic)}
