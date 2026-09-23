#!/usr/bin/env python3
"""
SVS spinout scanner (proof build).

Finds university-linked software spinout signals from federal grant data and
ranks them by fit with Summit Venture Studio's thesis:
  - university-developed software (professors/researchers, not students)
  - pre-seed / early stage
  - STTR is the strongest signal, because STTR requires a university partner

Sources (all free, no key, server-side):
  - NIH RePORTER  (SBIR/STTR activity codes R41-R44)
  - NSF Awards API (SBIR/STTR software awards)

SBIR.gov is intentionally omitted: it blocks automated traffic at the IP level,
and NIH + NSF already carry the two agencies SVS cares about most.

Usage:
  python3 svs_scan.py                 # default run, FY2025-2026
  python3 svs_scan.py --years 2026    # single year
  python3 svs_scan.py --csv out.csv   # also write a ranked CSV
"""

import argparse
import csv
import json
import os
import re
import ssl
import sys
import urllib.request
import urllib.parse

NIH_URL = "https://api.reporter.nih.gov/v2/projects/search"
NSF_URL = "https://api.nsf.gov/services/v1/awards.json"

# In a proxied/sandboxed environment the system CA may not trust the proxy's
# cert. Set SVS_INSECURE=1 to skip verification. Do not use in production.
_SSL_CTX = ssl._create_unverified_context() if os.environ.get("SVS_INSECURE") == "1" else None

# Software title search text for NIH. SVS wants software, not wet-lab science.
NIH_SOFTWARE_QUERY = ("software platform algorithm machine learning artificial intelligence "
                      "app digital analytics computational automation cybersecurity")

# Signals SVS explicitly wants. One term, one meaning.
SOFTWARE_TERMS = [
    "software", "algorithm", "platform", "machine learning", "artificial intelligence",
    "ai-", "ai ", "digital", "analytics", "computational", "automation", "cyber", "saas",
]
# Wet-lab / therapeutic terms. SVS is software-only, so these are disqualifiers.
WETLAB_TERMS = [
    "vaccine", "therapeutic", "antibody", "crispr", "heparin", "molecule", "compound",
    "drug", "oligonucleotide", "antisense", "peptide", "assay", "reagent", "protein",
    "genome edit", "gene therapy", "small molecule", "inhibitor", "monoclonal",
]
UNIVERSITY_TERMS = [
    "universit", "college", "institute of technology", "school of medicine",
    "state universit", "polytechnic",
]
STTR_CODES = {"R41", "R42"}   # STTR: university partner required
SBIR_CODES = {"R43", "R44"}   # SBIR: small business

# Sector classification. Ordered: the first matching sector wins, so off-thesis
# physical categories (therapeutics, devices) are tested before generic software.
# This is what lets a "microfluidic platform with machine learning" land in
# Medical device, not AI software, which is the distinction SVS cares about.
SECTOR_RULES = [
    ("Therapeutics & biotech", ["vaccine", "therapeutic", "antibody", "crispr", "gene therap",
        "oligonucleotide", "antisense", "peptide", "small molecule", "inhibitor", "monoclonal",
        "immunotherap", "drug screen", "compound", "heparin", "car-t", "cart ", "preclinical"]),
    ("Medical device & hardware", ["microfluidic", "implant", "wearable", "catheter", "prosthe",
        "electrode", "needle", "hardware", "instrument", "cartridge", "reagent", "assay",
        "lateral flow", "biosensor", "3d print", "actuator"]),
    ("Imaging & radiology", ["imaging", "radiolog", " mri", "ct scan", "ultrasound", "microscop",
        "tomograph", "endoscop"]),
    ("Diagnostics & screening", ["diagnostic", "screening", "detection", "biomarker", "point-of-care",
        "point of care"]),
    ("Mental & behavioral health", ["mental health", "behavioral", "depression", "anxiety", "opioid",
        "substance use", "addiction", "cognitive", "psychiatr", "suicide", "ptsd"]),
    ("EdTech & learning", ["learning platform", "education", "curriculum", "literacy", "student",
        "classroom", "teach", "training platform", "tutor"]),
    ("Cybersecurity & data", ["cybersecurity", "cyber ", "encryption", "malware", "threat detection",
        "authentication", "privacy-preserv"]),
    ("Clinical & digital health", ["clinical decision", "patient", "care ", "telehealth",
        "health record", "ehr", "workflow", "hospital", "provider", "caregiver", "clinician",
        "remote monitoring", "adherence"]),
    ("AI & software infrastructure", ["machine learning", "artificial intelligence", "algorithm",
        "platform", "software", "analytics", "large language", "digital twin", "automation",
        "natural language", "agentic"]),
]


def classify(rec):
    """Assign a sector by first matching rule, on the title only.

    SBIR/STTR titles are descriptive and clean. The abstract adds noise: a
    software company mentioning a 'sensor' once would be miscoded as hardware.
    """
    title = rec["title"].lower()
    for sector, terms in SECTOR_RULES:
        if any(t in title for t in terms):
            return sector
    # Title was inconclusive. Fall back to the abstract. This only affects rows
    # that had no signal in the title, so it cannot override a clean title match.
    abstract = (rec.get("abstract", "") or "").lower()
    for sector, terms in SECTOR_RULES:
        if any(t in abstract for t in terms):
            return sector
    return "Other"


# Sectors that fall outside SVS's software-only, professor-invented thesis.
OFF_THESIS_SECTORS = {"Therapeutics & biotech", "Medical device & hardware"}


# Best-effort university extraction from abstract prose. The partner university
# is NOT a structured field in NIH/NSF data, so coverage is only ~10%. We show it
# only where a clean match is found; otherwise the row simply omits it.
_NAMED = ("Johns Hopkins University|Stanford University|Harvard University|Yale University|"
          "Princeton University|California Institute of Technology|Carnegie Mellon University|"
          "Massachusetts Institute of Technology|Duke University|Cornell University|"
          "Columbia University|Northwestern University|Vanderbilt University")
_UNIV_RE = re.compile(
    r"\b(University of [A-Z][A-Za-z]+(?:,? [A-Z][A-Za-z]+){0,2}"
    r"|[A-Z][A-Za-z]+(?:[ &][A-Z][A-Za-z]+){0,3} State University"
    r"|[A-Z][A-Za-z]+(?:[ &][A-Z][A-Za-z]+){0,3} University"
    r"|" + _NAMED + r")\b")
_UNIV_GENERIC = {"Science University", "State University", "The University",
                 "This University", "A University", "Our University", "Its University"}


def extract_university(text):
    """Return a clean university name from abstract prose, or '' if none."""
    for m in _UNIV_RE.finditer(text or ""):
        name = re.sub(r"\s+(NIA|NIH|NCI|USA|LLC|Inc)$", "", m.group(1)).strip()
        if name not in _UNIV_GENERIC and len(name) > 6:
            return name
    return ""


def clean_summary(text):
    """Tidy a grant abstract for display: rejoin PDF line-break hyphenation,
    flatten newlines, and strip the boilerplate 'PROJECT SUMMARY' header so the
    preview starts on the real content."""
    t = text or ""
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)          # "con-\ntributes" -> "contributes"
    t = re.sub(r"\s*\n\s*", " ", t)                        # newlines -> spaces
    t = re.sub(r"^\s*(modified\s+)?project\s+summary\s*/?\s*(and\s+)?(abstract)?"
               r"(\s+section)?[:.\-\s]*", "", t, flags=re.I)
    t = re.sub(r"^\s*abstract[:.\-\s]*", "", t, flags=re.I)
    return re.sub(r"\s{2,}", " ", t).strip()


def nih_core(project_num):
    """NIH core project id: strip the application-type digit and the year suffix.
    '5R44ES035349-03' and '2R44ES035349-02A1' both reduce to 'R44ES035349'."""
    return re.sub(r"^\d+", "", (project_num or "")).split("-")[0]


def http_get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
        return json.load(r)


def http_post_json(url, payload, timeout=30):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
        return json.load(r)


def fetch_nih(years, limit=500):
    """NIH SBIR/STTR awards (R41-R44) for the given fiscal years."""
    payload = {
        "criteria": {
            "activity_codes": sorted(STTR_CODES | SBIR_CODES),
            "fiscal_years": years,
            "advanced_text_search": {
                "operator": "or",
                "search_field": "projecttitle",
                "search_text": NIH_SOFTWARE_QUERY,
            },
        },
        "include_fields": [
            "ProjectNum", "ProjectTitle", "Organization", "ContactPiName",
            "AwardAmount", "FiscalYear", "ActivityCode", "AbstractText",
            "OrgName", "ApplId",
        ],
        "limit": limit,
    }
    data = http_post_json(NIH_URL, payload)
    out = []
    for r in data.get("results", []):
        organization = r.get("organization") or {}
        org = organization.get("org_name", "") or ""
        out.append({
            "source": "NIH",
            "id": r.get("project_num", ""),
            "appl_id": r.get("appl_id", ""),
            "code": r.get("activity_code", ""),
            "pi": r.get("contact_pi_name", "") or "",
            "org": org,
            "state": organization.get("org_state", "") or "",
            "city": organization.get("org_city", "") or "",
            "email": "",   # NIH RePORTER does not publish PI email
            "amount": r.get("award_amount") or 0,
            "year": r.get("fiscal_year", ""),
            "title": (r.get("project_title") or "").strip(),
            "abstract": (r.get("abstract_text") or "")[:600],
            # Extract from the FULL abstract: the university is often named deep
            # in the text, past any truncation point.
            "university": extract_university(r.get("abstract_text") or ""),
        })
    # Dedup by NIH core project id, keeping the latest fiscal year. NIH returns
    # one row per budget year, so a renewal and its continuation both appear.
    best = {}
    for r in out:
        key = nih_core(r["id"])
        if key not in best or (r["year"] or 0) > (best[key]["year"] or 0):
            best[key] = r
    return list(best.values())


def fetch_nsf(years, pages=16):
    """NSF SBIR/STTR awards.

    The NSF public award API has no program filter. But every SBIR/STTR abstract
    contains the phrase "Small Business Innovation Research", and every such
    award's title starts with "SBIR" or "STTR". So we page on that phrase and
    keep the SBIR/STTR titles. This is the title-prefix crawl.
    """
    out = []
    start = f"01/01/{min(years)}"
    # NSF wants the phrase quoted (%22) with + between words. Pre-encode it.
    kw = "%22" + "+".join("Small Business Innovation Research".split()) + "%22"
    for i in range(pages):
        offset = 1 + i * 25   # NSF returns 25 rows per page
        params = {
            "keyword": kw,
            "printFields": "id,title,awardeeName,piFirstName,piLastName,piEmail,"
                           "fundsObligatedAmt,startDate,fundProgramName,"
                           "awardeeStateCode,awardeeCity,abstractText",
            "dateStart": start,
            "offset": offset,
        }
        url = NSF_URL + "?" + urllib.parse.urlencode(params, safe="%+")
        try:
            data = http_get_json(url)
        except Exception as e:
            print(f"  NSF page {offset} failed: {e}", file=sys.stderr)
            continue
        awards = data.get("response", {}).get("award", [])
        if not awards:
            break   # ran off the end of the result set
        for a in awards:
            title = (a.get("title") or "").strip()
            prog = (a.get("fundProgramName") or "")
            if not title.upper().startswith(("SBIR", "STTR")):
                continue
            code = "STTR" if title.upper().startswith("STTR") or "STTR" in prog.upper() else "SBIR"
            pi = f"{a.get('piLastName','')}, {a.get('piFirstName','')}".strip(", ")
            out.append({
                "source": "NSF",
                "id": a.get("id", ""),
                "code": code,
                "pi": pi,
                "org": a.get("awardeeName", "") or "",
                "state": a.get("awardeeStateCode", "") or "",
                "city": a.get("awardeeCity", "") or "",
                "email": a.get("piEmail", "") or "",   # NSF publishes PI email
                "amount": int(a.get("fundsObligatedAmt") or 0),
                "year": (a.get("startDate", "") or "")[-4:],
                "title": title,
                "abstract": (a.get("abstractText") or "")[:600],
                "university": extract_university(a.get("abstractText") or ""),
            })
    # de-dup by id
    seen, dedup = set(), []
    for r in out:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        dedup.append(r)
    return dedup


def score(rec):
    """SVS-fit score. Higher = closer to their thesis. Transparent, additive."""
    s, why = 0, []
    title = rec["title"].lower()
    text = (rec["title"] + " " + rec["abstract"] + " " + rec["org"]).lower()

    is_sttr = rec["code"] in STTR_CODES or rec["code"] == "STTR"

    # Software signal must come from the title, not a stray abstract word.
    if any(t in title for t in SOFTWARE_TERMS):
        s += 3; why.append("software in title")
    if is_sttr:
        s += 3; why.append("STTR: university partner required")
    # A named university adds signal mainly for non-STTR awards, where the
    # university tie is not already guaranteed. On STTR it just double-counts.
    elif any(t in text for t in UNIVERSITY_TERMS):
        s += 2; why.append("names a university")
    is_phase2 = "phase ii" in title or rec["code"] in {"R42", "R44"}
    if not is_phase2:
        s += 1; why.append("Phase I: early")
    # prefer smaller early checks (SVS writes pre-seed/seed)
    if 0 < rec["amount"] <= 500_000:
        s += 1; why.append("small early award")

    # Disqualifier: sectors outside SVS's software-only thesis. This catches
    # both therapeutics and physical devices (a microfluidic chip is hardware,
    # even when it uses machine learning).
    sector = classify(rec)
    rec["sector"] = sector
    if sector in OFF_THESIS_SECTORS:
        s -= 5; why.append(f"PENALTY: {sector.lower()}")

    rec["score"] = s
    rec["why"] = "; ".join(why)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", type=int, default=[2025, 2026])
    ap.add_argument("--csv", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()

    print(f"Scanning NIH + NSF for FY {args.years} ...", file=sys.stderr)
    recs = []
    try:
        nih = fetch_nih(args.years)
        print(f"  NIH SBIR/STTR: {len(nih)} awards", file=sys.stderr)
        recs += nih
    except Exception as e:
        print(f"  NIH failed: {e}", file=sys.stderr)
    nsf = fetch_nsf(args.years)
    print(f"  NSF SBIR/STTR: {len(nsf)} awards", file=sys.stderr)
    recs += nsf

    ranked = sorted((score(r) for r in recs), key=lambda r: r["score"], reverse=True)

    print(f"\nTop {args.top} SVS-fit spinout signals ({len(ranked)} total)\n")
    print(f"{'SCORE':>5} {'SRC':<4} {'CODE':<5} {'AMOUNT':>10}  PI / ORG / TITLE")
    print("-" * 100)
    for r in ranked[:args.top]:
        print(f"{r['score']:>5} {r['source']:<4} {r['code']:<5} ${r['amount']:>9,}  "
              f"{r['pi']} | {r['org'][:32]} | {r['title'][:44]}")
        print(f"{'':>27}why: {r['why']}")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "score", "source", "code", "pi", "org", "amount", "year",
                "title", "why", "id",
            ], extrasaction="ignore")
            w.writeheader()
            w.writerows(ranked)
        print(f"\nWrote {len(ranked)} rows to {args.csv}", file=sys.stderr)

    if args.json:
        keep = ("score", "source", "code", "pi", "org", "state", "city", "amount",
                "year", "title", "why", "id", "sector", "email")

        def to_rec(r):
            d = {k: r.get(k, "") for k in keep}
            d["university"] = r.get("university", "")
            d["abstract"] = clean_summary(r.get("abstract", ""))[:300]
            if r.get("source") == "NSF" and r.get("id"):
                d["url"] = f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={r['id']}"
            elif r.get("appl_id"):
                d["url"] = f"https://reporter.nih.gov/project-details/{r['appl_id']}"
            else:
                d["url"] = "https://reporter.nih.gov/"
            # Contact-enrichment links. The email is a real value only for NSF;
            # for NIH we give search links, never a fabricated address.
            person = urllib.parse.quote_plus(f"{r.get('pi','')} {r.get('org','')}")
            d["linkedin"] = f"https://www.linkedin.com/search/results/people/?keywords={person}"
            d["google"] = f"https://www.google.com/search?q={person}"
            return d

        recs = [to_rec(r) for r in ranked]
        payload = {
            "generated_years": args.years,
            "total": len(recs),
            "by_source": {
                "NIH": sum(1 for r in recs if r["source"] == "NIH"),
                "NSF": sum(1 for r in recs if r["source"] == "NSF"),
            },
            "records": recs,
        }
        with open(args.json, "w") as f:
            json.dump(payload, f, indent=1)
        print(f"Wrote {len(recs)} rows to {args.json}", file=sys.stderr)


if __name__ == "__main__":
    main()
