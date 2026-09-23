#!/usr/bin/env python3
"""
Fetch recent university-assignee software patents from PatentsView.

RUN THIS ON YOUR MAC OR THE HETZNER BOX, not the Claude Code sandbox: the
sandbox proxy blocks PatentsView (HTTP 000/403). PatentsView's current API also
requires a free key: request one at https://patentsview.org/apis and export it:

    export PATENTSVIEW_API_KEY=...          # required
    python3 fetch_patents.py                # writes patents_university.json

What it captures: patents granted since 2022 whose assignee is a university and
whose title/abstract is software-flavored, with inventors (the faculty) and the
assignee institution. This is the "TTO already protected it" signal, and it is
the one source that catches the SegoEd-type deal (patented university software).
"""
import json, os, sys, urllib.request

API = "https://search.patentsview.org/api/v1/patent/"
KEY = os.environ.get("PATENTSVIEW_API_KEY", "")
SOFTWARE = ["software", "machine learning", "artificial intelligence", "algorithm",
            "platform", "neural network", "analytics", "computer-implemented"]


def query(page_after=None):
    q = {"_and": [
        {"_gte": {"patent_date": "2022-01-01"}},
        {"_text_any": {"assignees.assignee_organization": "University College Institute"}},
        {"_text_any": {"patent_title": " ".join(SOFTWARE)}},
    ]}
    body = {
        "q": q,
        "f": ["patent_id", "patent_title", "patent_date", "patent_abstract",
              "assignees.assignee_organization",
              "inventors.inventor_name_first", "inventors.inventor_name_last"],
        "s": [{"patent_id": "asc"}],
        "o": {"size": 100},
    }
    if page_after:
        body["o"]["after"] = page_after
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Api-Key": KEY})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def is_university(org):
    o = (org or "").lower()
    return any(w in o for w in ("univ", "college", "institute of technology"))


def main():
    if not KEY:
        sys.exit("Set PATENTSVIEW_API_KEY (free from patentsview.org/apis). See header.")
    out, after = [], None
    while True:
        data = query(after)
        pats = data.get("patents") or []
        if not pats:
            break
        for p in pats:
            orgs = [a.get("assignee_organization", "") for a in (p.get("assignees") or [])]
            uni = next((o for o in orgs if is_university(o)), "")
            if not uni:
                continue
            invs = [f"{i.get('inventor_name_first','')} {i.get('inventor_name_last','')}".strip()
                    for i in (p.get("inventors") or [])]
            out.append({
                "source": "PatentsView", "id": p.get("patent_id"),
                "title": p.get("patent_title", ""), "date": p.get("patent_date", ""),
                "university": uni, "inventors": invs,
                "abstract": (p.get("patent_abstract") or "")[:300],
                "url": f"https://patents.google.com/patent/US{p.get('patent_id')}",
            })
        after = pats[-1].get("patent_id")
        print(f"  ...{len(out)} university software patents so far", file=sys.stderr)
        if len(pats) < 100:
            break
    json.dump({"source": "PatentsView university software patents", "records": out},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "patents_university.json"), "w"), indent=1)
    print(f"wrote {len(out)} university software patents", file=sys.stderr)


if __name__ == "__main__":
    main()
