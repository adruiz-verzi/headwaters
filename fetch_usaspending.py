#!/usr/bin/env python3
"""
Fetch all-agency SBIR/STTR software awards from USAspending.gov.

SBIR.gov's own API is Forbidden even from a residential IP, but USAspending.gov
(the federal award database) carries the same SBIR/STTR awards, has a public API
with no key, and IS reachable. This is how we reach DoD, DOE, and NASA SBIR
software, the agencies NIH RePORTER and NSF don't cover.

This is the "deals you're missing" expansion net: grant/contract-funded software
companies outside SVS's university tech-transfer relationships.

    python3 fetch_usaspending.py            # writes usaspending_sbir.json
"""
import json, os, re, ssl, sys, urllib.request

# The Claude Code sandbox proxies TLS with its own CA; skip verification there.
_CTX = ssl._create_unverified_context() if os.environ.get("SVS_INSECURE") == "1" else None

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
SOFTWARE = re.compile(r"software|machine learning|artificial intelligence|\bai\b|algorithm|"
                      r"platform|analytics|cyber|autonom|data|digital|model|simulation|network", re.I)
# SBIR/STTR at DoD/NASA are contracts (A-D); at NIH/NSF/DOE they are assistance (02-05).
AWARD_TYPES = ["A", "B", "C", "D"]


def post(body):
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45, context=_CTX) as r:
        return json.load(r)


def main():
    out, page = [], 1
    while page <= 20:   # up to ~2000 awards
        body = {
            "filters": {
                "award_type_codes": AWARD_TYPES,
                "keywords": ["SBIR", "STTR"],
                "time_period": [{"start_date": "2024-01-01", "end_date": "2026-09-22"}],
            },
            "fields": ["Award ID", "Recipient Name", "Awarding Agency",
                       "Awarding Sub Agency", "Award Amount", "Description",
                       "Start Date", "Place of Performance State Code"],
            "limit": 100, "page": page,
        }
        try:
            data = post(body)
        except Exception as e:
            print(f"  page {page}: {e}", file=sys.stderr)
            break
        rows = data.get("results") or []
        if not rows:
            break
        for a in rows:
            desc = a.get("Description") or ""
            if not SOFTWARE.search(desc):
                continue
            out.append({
                "source": "USAspending", "id": a.get("Award ID", ""),
                "firm": a.get("Recipient Name", ""),
                "agency": a.get("Awarding Agency", ""),
                "subagency": a.get("Awarding Sub Agency", ""),
                "amount": a.get("Award Amount", 0),
                "title": desc[:160], "abstract": desc[:400],
                "year": (a.get("Start Date") or "")[:4],
                "state": a.get("Place of Performance State Code", ""),
            })
        print(f"  page {page}: {len(rows)} awards, {len(out)} software kept", file=sys.stderr)
        if not data.get("page_metadata", {}).get("hasNext"):
            break
        page += 1
    json.dump({"source": "USAspending all-agency SBIR/STTR software awards", "records": out},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "usaspending_sbir.json"), "w"), indent=1)
    print(f"wrote {len(out)} all-agency software SBIR/STTR awards", file=sys.stderr)


if __name__ == "__main__":
    main()
