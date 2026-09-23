#!/usr/bin/env python3
"""
Filter USPTO PatentsView bulk data to Utah-university software patents.

Streams the disambiguated bulk TSVs (inside their .zip, no full extraction):
  g_assignee_disambiguated.tsv.zip  -> patent -> university assignee
  g_patent.tsv.zip                  -> title + date
  g_inventor_disambiguated.tsv.zip  -> faculty inventors

Output: utah_patents.json (recent university software patents, Utah's four schools),
plus a national university-patent count for context. Free, keyless, authoritative,
clean assignee names (fixes the identity problem Spencer flagged).
"""
import csv, io, json, os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
U = os.path.join(HERE, "uspto")
RECENT_YEAR = 2021   # last ~5 grant years = current commercialization signal

UTAH_FRAGS = ("university of utah", "utah state university", "brigham young", "utah valley")
# Universities, excluding obvious non-US-research-university noise.
UNIV_RE = re.compile(r"\buniversit|\bcollege\b|institute of technology|polytechnic", re.I)
NOT_UNIV_RE = re.compile(r"community college|college of the|,?\s*inc\.?$|\bllc\b|corporation|company", re.I)
SOFTWARE_RE = re.compile(
    r"software|algorithm|machine learning|neural network|artificial intelligence|"
    r"computer-implemented|computer implemented|data processing|computing|database|"
    r"encryption|network|digital|computer program|computer-readable|predictive|"
    r"analytics|simulation|autonomous|virtual reality|augmented reality", re.I)


def stream(zipname):
    """Yield dict rows from the single TSV inside a .zip, streamed."""
    zf = zipfile.ZipFile(os.path.join(U, zipname))
    name = zf.namelist()[0]
    with zf.open(name) as raw:
        txt = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
        for row in csv.DictReader(txt, delimiter="\t", quotechar='"'):
            yield row


FOREIGN = ("université", "universität", "jiangsu", "tsinghua", "zhejiang")


def is_university(org):
    return bool(UNIV_RE.search(org)) and not NOT_UNIV_RE.search(org)


def us_fallback(org):
    try:
        org.encode("ascii")
    except UnicodeEncodeError:
        return False
    low = org.lower()
    return not any(f in low for f in FOREIGN)


def main():
    # Load location table (small): location_id -> (state, country).
    loc = {}
    for r in stream("g_location_disambiguated.tsv.zip"):
        loc[r["location_id"]] = (r.get("disambig_state", ""), r.get("disambig_country", ""))
    print(f"locations loaded: {len(loc):,}", file=sys.stderr)

    # Pass 1: assignee -> every US university patent, with state (via location join).
    univ = {}            # patent_id -> (organization, state)
    for i, r in enumerate(stream("g_assignee_disambiguated.tsv.zip")):
        org = (r.get("disambig_assignee_organization", "") or "").strip()
        if not (org and is_university(org)):
            continue
        state, country = loc.get(r.get("location_id", ""), ("", ""))
        if country and country != "US":
            continue                       # exact drop of non-US
        if not country and not us_fallback(org):
            continue                       # missing location -> heuristic
        univ[r["patent_id"]] = (org, state)
        if i % 2_000_000 == 0:
            print(f"  assignee rows {i:,} | US university patents {len(univ):,}", file=sys.stderr)
    print(f"US university patents (all years): {len(univ):,}", file=sys.stderr)

    # Pass 2: patent -> title + date, keep ALL recent US university patents
    # (software is decided by CPC next, not by the title).
    recs = {}
    for r in stream("g_patent.tsv.zip"):
        pid = r["patent_id"]
        if pid not in univ:
            continue
        year = (r.get("patent_date") or "")[:4]
        try:
            if int(year) < RECENT_YEAR:
                continue
        except ValueError:
            continue
        org, state = univ[pid]
        recs[pid] = {"id": pid, "university": org, "state": state,
                     "title": r.get("patent_title", "").strip(),
                     "date": r.get("patent_date", ""), "inventors": [],
                     "category": "", "software": False,
                     "is_utah": any(f in org.lower() for f in UTAH_FRAGS)}
    print(f"recent ({RECENT_YEAR}+) US university patents (pre-CPC): {len(recs)}", file=sys.stderr)

    # Pass 2.5: CPC classification -> the authoritative software signal.
    # subclass -> category; presence of any = software patent.
    CPC_CAT = {"G06N": "AI / machine learning", "G06T": "Computer vision / imaging",
               "G06V": "Computer vision / imaging", "G06Q": "Data-processing methods",
               "G06F": "Computing / data processing", "G06K": "Computing / data processing",
               "H04L": "Networking / security", "G16H": "Health informatics",
               "G16B": "Bioinformatics"}
    def cpc_cat(sub):
        if sub in CPC_CAT:
            return CPC_CAT[sub]
        if sub.startswith("G16"):
            return "Domain informatics"
        if sub.startswith("G06"):
            return "Computing / data processing"
        return None
    for r in stream("g_cpc_current.tsv.zip"):
        pid = r["patent_id"]
        rec = recs.get(pid)
        if not rec:
            continue
        cat = cpc_cat(r.get("cpc_subclass", ""))
        if cat:
            rec["software"] = True
            if not rec["category"]:
                rec["category"] = cat
    recs = {k: v for k, v in recs.items() if v["software"]}
    print(f"recent US university SOFTWARE patents (by CPC): {len(recs)}", file=sys.stderr)

    # Pass 3: inventors for those patents
    for r in stream("g_inventor_disambiguated.tsv.zip"):
        pid = r["patent_id"]
        if pid in recs:
            nm = (r.get("disambig_inventor_name_first", "") + " " +
                  r.get("disambig_inventor_name_last", "")).strip()
            if nm:
                recs[pid]["inventors"].append(nm)

    out = sorted(recs.values(), key=lambda x: x["date"], reverse=True)
    for r in out:
        r["inventors"] = ", ".join(r["inventors"][:4])
        r["url"] = f"https://patents.google.com/patent/US{r['id']}"
    universities = sorted(set(r["university"] for r in out))
    states = sorted(set(r["state"] for r in out if r["state"]))
    payload = {
        "source": "USPTO PatentsView disambiguated data (bulk), US universities",
        "recent_since": RECENT_YEAR,
        "total_software_patents": len(out),
        "distinct_universities": len(universities),
        "distinct_states": len(states),
        "utah_software": sum(1 for r in out if r["is_utah"]),
        "records": out,
    }
    json.dump(payload, open(os.path.join(HERE, "patents_national.json"), "w"), indent=1)
    print(f"wrote {len(out)} recent university software patents "
          f"from {len(universities)} universities to patents_national.json", file=sys.stderr)


if __name__ == "__main__":
    main()
