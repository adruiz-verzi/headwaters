#!/usr/bin/env python3
"""Re-score svs_data.json in place with a tightened wet-lab/therapeutic penalty.

Spencer's teardown: therapeutics were buying a fit-8 because "platform"/"algorithm"
in the title scored software points and the sector classifier missed the biology.
This applies a hard penalty on any record whose title OR abstract shows wet-lab /
therapeutic / device signal, regardless of what the sector said. Done in place so
the LLM summaries (keyed by position) stay aligned.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WETLAB = re.compile(
    r"\b(therapeutic|therapy|vaccine|antibody|antigen receptor|chimeric antigen|\bcar-?t\b|"
    r"organoid|xenograft|gene therapy|gene[- ]edit|crispr|oligonucleotide|antisense|peptide|"
    r"small molecule|inhibitor|monoclonal|immunotherap|\bdrug\b|compound|heparin|cell therapy|"
    r"stem cell|\bassay\b|reagent|\benzyme\b|in vivo|in vitro|mouse model|zebrafish|"
    r"fatty acid|nanoparticle|microfluidic|electrochemical|biomarker discovery|"
    r"\btissue\b|bionic|electrophysiolog|biosensor|regenerative|engineered heart|"
    r"cardiac tissue|cell quality|cell identit|cell line|organ-on|spheroid|\bculture\b)\b", re.I)

data = json.load(open(os.path.join(HERE, "svs_data.json")))
demoted = 0
for r in data["records"]:
    text = (r.get("title", "") + " " + r.get("abstract", "")).lower()
    if WETLAB.search(text) and "wet-lab" not in (r.get("why", "") or "").lower():
        r["score"] = r.get("score", 0) - 6
        r["why"] = (r.get("why", "") + "; PENALTY: wet-lab/therapeutic signal").lstrip("; ")
        r["sector"] = "Therapeutics & biotech"
        demoted += 1

json.dump(data, open(os.path.join(HERE, "svs_data.json"), "w"), indent=1)
print(f"re-scored; demoted {demoted} wet-lab/therapeutic records")
