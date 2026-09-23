#!/usr/bin/env python3
"""Enrich U of Utah TTO inventors with their OpenAlex research profile.

For each technology's lead inventor: resolve to OpenAlex, keep the education
affiliation, works count, and author page. Confirms the U of Utah link and adds
the faculty-research signal to the 'deals like theirs' view.

Usage: SVS_INSECURE=1 python3 tto_enrich.py   # updates tto_utah.json in place
"""
import json, os, re, ssl, sys, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "tto_utah.json")
CACHE = os.path.join(HERE, "openalex_cache.json")
MAILTO = "adrian@verzi.io"
CTX = ssl._create_unverified_context() if os.environ.get("SVS_INSECURE") == "1" else None


def lead_name(inventors):
    """'Rajesh Menon +4' -> 'Rajesh Menon'."""
    return re.sub(r"\s*\+\d+\s*$", "", (inventors or "").split(",")[0]).strip()


def search(name):
    if not name:
        return {}
    url = ("https://api.openalex.org/authors?search=" + urllib.parse.quote(name)
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
    return {"oa_affiliation": inst.get("display_name", ""),
            "oa_affiliation_type": inst.get("type", ""),
            "oa_url": a.get("id", ""), "oa_works": a.get("works_count", 0)}


def main():
    doc = json.load(open(DATA))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    key = lambda s: "tto:" + "".join(c for c in s.lower() if c.isalnum())

    confirmed = 0
    for r in doc["records"]:
        name = lead_name(r.get("inventors", ""))
        r["lead_inventor"] = name
        k = key(name)
        if k not in cache:
            cache[k] = search(name)
            time.sleep(0.12)
        prof = cache[k] or {}
        aff = prof.get("oa_affiliation", "") if prof.get("oa_affiliation_type") == "education" else ""
        r["oa_affiliation"] = aff
        r["oa_url"] = prof.get("oa_url", "")
        r["oa_works"] = prof.get("oa_works", 0)
        r["utah_confirmed"] = "utah" in aff.lower()
        if r["utah_confirmed"]:
            confirmed += 1

    json.dump(cache, open(CACHE, "w"))
    json.dump(doc, open(DATA, "w"), indent=1)
    print(f"enriched {len(doc['records'])} TTO inventors; "
          f"OpenAlex confirms U of Utah for {confirmed}", file=sys.stderr)


if __name__ == "__main__":
    main()
