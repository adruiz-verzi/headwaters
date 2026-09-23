# Headwaters — spinout intelligence for Summit Venture Studio

A scouting feed for university software spinouts, ranked to SVS's thesis. Live demo:
`svs-pipeline.verzi.io` (Cloudflare Pages). Built by Verzi.

## What it does

Three views over four public data sources:

1. **Deals like theirs** — licensable software from university tech-transfer offices
   (University of Utah today), the channel SVS's portfolio actually comes through.
2. **University patents** — recent (2021+) US university software patents, nationwide,
   classified by CPC (AI/ML, computer vision, health informatics, ...). Filter by
   state, university, and software type. USPTO-disambiguated names, so identity is exact.
3. **Grant-backed software cos** — NIH + NSF + DoD grant-funded software companies
   (a separate, already-formed pool, labeled honestly).

## Pipeline (all free, no paid APIs)

| Script | Source | Output |
| --- | --- | --- |
| `svs_scan.py` | NIH RePORTER + NSF | `svs_data.json` (grant signals, scored) |
| `enrich_openalex.py` | OpenAlex | PI research profiles on `svs_data.json` |
| `merge_summaries.py` | (LLM one-liners) | plain-English summaries |
| `rescore.py` | — | wet-lab/therapeutic penalty |
| `fetch_usaspending.py` | USAspending.gov | `usaspending_sbir.json` (all-agency SBIR, incl. DoD) |
| `patents_filter.py` | USPTO PatentsView bulk | `patents_national.json` (US university software patents, CPC-classified) |
| `tto_enrich.py` | OpenAlex | inventor profiles on `tto_utah.json` |
| `build_site.py` | all of the above | `headwaters.html` |

TTO listings (`tto_utah.json`) are scraped from the U of Utah licensing portal.

## Data not in git

The USPTO bulk files live in `uspto/` (multi-GB, gitignored). Re-download from
data.uspto.gov (PatentsView Granted Patent Disambiguated Data): `g_assignee_disambiguated`,
`g_patent`, `g_inventor_disambiguated`, `g_location_disambiguated`, `g_cpc_current`.
`fetch_patents.py` / `fetch_sbir.py` run on a residential IP or the box (the sandbox proxy
blocks PatentsView and SBIR.gov).

## Deploy

```
python3 build_site.py
cp headwaters.html site-deploy/index.html
CLOUDFLARE_ACCOUNT_ID=<acct> npx wrangler pages deploy site-deploy --project-name svs-pipeline --branch main
```

## Context

`uni-research/SVS_SCOUTING_METHOD_2026-09-19.md` and `SVS_READ_2026-09-22.md` hold the
scouting method and the buyer-side (Spencer/SVS) feedback that shaped this.
