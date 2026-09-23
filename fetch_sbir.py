#!/usr/bin/env python3
"""
Fetch SBIR/STTR awards from ALL 11 agencies via SBIR.gov.

RUN THIS ON YOUR MAC OR THE HETZNER BOX, not the Claude Code sandbox: SBIR.gov
blocks datacenter/proxy IPs (HTTP 403). From a residential IP it works with no
key. This widens the grant net far beyond the NIH+NSF that svs_scan.py already
covers — most importantly DoD, DOE, and NASA software SBIRs.

    python3 fetch_sbir.py                    # writes sbir_all_agency.json

Note: SBIR.gov is the "deals you're missing" net (grant-funded companies), NOT
the primary net for SVS's realized deals (those come from TTO licensing). Keep it
as the expansion feed that surfaces companies outside SVS's TTO relationships.
"""
import json, os, sys, time, urllib.parse, urllib.request

BASE = "https://api.www.sbir.gov/public/api/awards"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
AGENCIES = ["DOD", "HHS", "NSF", "DOE", "NASA", "USDA", "EPA", "DOC", "ED", "DOT", "DHS"]
SOFTWARE = ["software", "machine learning", "artificial intelligence", "algorithm",
            "platform", "analytics", "cyber", "autonomy", "data"]


def is_software(a):
    t = ((a.get("award_title") or "") + " " + (a.get("abstract") or "")).lower()
    return any(w in t for w in SOFTWARE)


def fetch_agency(agency, year_from=2023):
    out, start = [], 0
    while True:
        params = {"agency": agency, "start": start, "rows": 100}
        url = BASE + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                rows = json.load(r)
        except Exception as e:
            print(f"  {agency} @ {start}: {e}", file=sys.stderr)
            break
        if not rows:
            break
        for a in rows:
            try:
                yr = int(str(a.get("award_year") or a.get("proposal_award_date", "0"))[:4])
            except ValueError:
                yr = 0
            if yr and yr < year_from:
                continue
            if not is_software(a):
                continue
            out.append({
                "source": "SBIR", "agency": agency,
                "firm": a.get("firm", ""), "title": a.get("award_title", ""),
                "phase": a.get("phase", ""), "program": a.get("program", ""),
                "amount": a.get("award_amount", ""), "year": a.get("award_year", ""),
                "pi": a.get("pi_name", ""), "state": a.get("firm_state", ""),
                "abstract": (a.get("abstract") or "")[:300],
                "url": a.get("award_link", ""),
            })
        start += 100
        if len(rows) < 100:
            break
        time.sleep(0.3)
    print(f"  {agency}: {len(out)} software awards", file=sys.stderr)
    return out


def main():
    allrecs = []
    for ag in AGENCIES:
        allrecs += fetch_agency(ag)
    json.dump({"source": "SBIR.gov all-agency software awards", "records": allrecs},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "sbir_all_agency.json"), "w"), indent=1)
    print(f"wrote {len(allrecs)} software SBIR/STTR awards across {len(AGENCIES)} agencies",
          file=sys.stderr)


if __name__ == "__main__":
    main()
