#!/usr/bin/env python3
"""
OpenAlex enrichment for the Headwaters dataset.

Adds a PI research profile to each record from OpenAlex (free scholarly graph):
the PI's affiliation, scholarly output, and a clickable author page. It also
CONFIRMS a grant-named university when the two agree.

Design note on precision: resolving a PI to an institution by name alone is
unreliable (a more-cited namesake often ranks first, and the PI's listed
affiliation is frequently their company, not a university). Measured agreement
with grant-named universities is only ~35%. So this enrichment does NOT assert
the OpenAlex affiliation as "the university." It is labeled as the PI's profile,
a verification aid the user can click through. The grant-named university (parsed
from the abstract, high precision) remains the asserted value.

Usage: SVS_INSECURE=1 python3 enrich_openalex.py   # updates svs_data.json in place
Re-run is cheap: results are cached per PI in openalex_cache.json.
"""
import json, os, re, ssl, sys, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "svs_data.json")
CACHE = os.path.join(HERE, "openalex_cache.json")
MAILTO = "adrian@verzi.io"   # OpenAlex polite pool
CTX = ssl._create_unverified_context() if os.environ.get("SVS_INSECURE") == "1" else None


def norm(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


def search_pi(piname):
    """Return an OpenAlex profile dict for a PI name, or None."""
    parts = [p.strip() for p in piname.split(",")]
    q = (parts[1] + " " + parts[0]) if len(parts) > 1 else piname
    url = ("https://api.openalex.org/authors?search=" + urllib.parse.quote(q)
           + "&per-page=1&mailto=" + MAILTO)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            data = json.load(r)
    except Exception as e:
        return {"error": str(e)[:40]}
    res = data.get("results") or []
    if not res:
        return {}
    a = res[0]
    insts = a.get("last_known_institutions") or []
    edu = [i for i in insts if i.get("type") == "education"]
    inst = (edu[0] if edu else (insts[0] if insts else {})) or {}
    return {
        "oa_url": a.get("id", "").replace("https://openalex.org/", "https://openalex.org/"),
        "oa_name": a.get("display_name", ""),
        "oa_affiliation": inst.get("display_name", ""),
        "oa_affiliation_type": inst.get("type", ""),
        "oa_works": a.get("works_count", 0),
        "oa_cited": a.get("cited_by_count", 0),
    }


def main():
    data = json.load(open(DATA))
    recs = data["records"]
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

    uniq = {}
    for r in recs:
        k = norm(r.get("pi", ""))
        if k and k not in uniq:
            uniq[k] = r["pi"]

    todo = [k for k in uniq if k not in cache]
    print(f"{len(recs)} records, {len(uniq)} unique PIs, {len(todo)} to query", file=sys.stderr)
    for i, k in enumerate(todo):
        cache[k] = search_pi(uniq[k])
        if i % 25 == 0:
            print(f"  {i}/{len(todo)} ...", file=sys.stderr)
            json.dump(cache, open(CACHE, "w"))
        time.sleep(0.12)   # polite pacing (in-process, not a shell sleep)
    json.dump(cache, open(CACHE, "w"))

    confirmed = enriched = 0
    for r in recs:
        prof = cache.get(norm(r.get("pi", "")), {}) or {}
        # Only keep an education-type affiliation as the shown profile institution;
        # a company affiliation is dropped (it is not the university signal).
        aff = prof.get("oa_affiliation", "") if prof.get("oa_affiliation_type") == "education" else ""
        r["oa_affiliation"] = aff
        r["oa_url"] = prof.get("oa_url", "")
        r["oa_works"] = prof.get("oa_works", 0)
        if aff:
            enriched += 1
        # Confirm the grant-named university when OpenAlex agrees.
        g, o = norm(r.get("university", "")), norm(aff)
        r["university_confirmed"] = bool(g and o and (g in o or o in g))
        if r["university_confirmed"]:
            confirmed += 1

    json.dump(data, open(DATA, "w"), indent=1)
    print(f"enriched with education affiliation: {enriched}/{len(recs)} | "
          f"grant universities confirmed by OpenAlex: {confirmed}", file=sys.stderr)


if __name__ == "__main__":
    main()
