# SVS scouting — sources, score, and the four questions (from the Sept 19 chat)

Recovered 2026-09-22 from Adrian's paste of the day-one dry-run write-up. The findings it summarizes are compiled and
cited in `Uni Research Strategy/wiki/` (gaps, methods, topics, teams, companies); this file keeps the SVS-specific
method, which was not written down anywhere else. Companion: `SVS_READ_2026-09-22.md` (the leads).

## Why grants come first

Grant databases are the earliest public signal of a university technology, years before a paper or a company. In the
dry run NIH RePORTER answered immediately (19 active 2025–26 projects mentioning prior authorization, each with PI,
institution, dollars, dates, and full abstract; e.g. Schwartz's Penn R01 on prior-auth exposure in cardiovascular
care, Landon's Harvard P01 on Medicare Advantage). NSF's award API answered too, and its first hit was a live SBIR
Phase I, "Reducing Medical Insurance Claim Denials," Actualization AI LLC, $275K — precisely what SVS exists to find.
Filtering NIH by SBIR/STTR activity codes (R41–R44) yields every small business commercializing NIH-funded health-tech
work: the university-to-startup pipeline itself.

So the pipeline is inverted: run the grant tier before the paper tier, and start the paper tier from the grant PIs'
publications rather than from keyword search. "Find the funded teams, then read what they published" is both more
precise and exactly the SVS scouting shape. (Now the rule in the `uni-research` skill.)

## Sources beyond grants and papers (SVS-specific; deferred in the dry run)

| Source | What it tells you | Status |
| --- | --- | --- |
| PatentsView | Patents with a university assignee and the researcher as inventor — the TTO already decided it's worth protecting | not yet wired |
| Lens.org | Links papers to patents | not yet wired |
| University tech-transfer portals ("available technologies") | Licensable inventions listed directly; whether a technology is already licensed is often public here — the source that turns "interesting team" into "actionable deal" | not yet wired |
| NSF I-Corps rosters | A team already trying to commercialize | not yet wired |
| STTR / PFI-TT participation (NIH R41/R42, NSF) | Same signal, with money attached | wired (grants tier) |
| SBIR.gov API | Company-side awards and outcomes | refused requests from the cloud sandbox; run from the Hetzner box or Claude Code |

## The scouting score

Each research group in the index gets features: has a live grant; has an SBIR/STTR; has a patent; has public code;
publishes on a rising topic; is at an institution SVS can work with; is not already spun out (check the SBIR firm
against the paper's authors). Sort by that and you get a ranked list of teams worth a conversation, with the paper,
the code, the grant abstract, and the PI's institution attached. First cut of this is `../svs_scan.py` → `../svs_ranked.csv`
(810 rows, grants only). For Verzi the same data reads the other way: teams whose grant abstracts describe a data or
engineering problem Verzi solves for a living are prospective partners or clients, and the gap map says which of those
problems nobody has productized.

## The four SVS questions

1. **Where is the technology on the university-to-company path?** Signals in order: paper → grant → patent or
   disclosure → I-Corps → STTR/PFI-TT → SBIR Phase I → Phase II → spinout. Bukhari at St. John's (I-Corps → $550K
   PFI-TT for trustworthy medical-code recommendations, running through 2027) is at the sweet spot: proven interest
   in commercializing, no company yet. The dive: take every academic author in the dataset and check them against
   I-Corps rosters, PatentsView, and NIH/NSF STTR participation.
2. **Who owns it?** Federally funded university technology is licensed through the tech-transfer office; whether it
   has been licensed is often public in the TTO portal. Deferred source; the one that makes a deal actionable.
3. **Is the team fundable?** Citation velocity of recent work; industry co-authors; early-career PI (K awards, first
   R01) versus established chair. SVS presumably wants founders, not tenured chairs.
4. **What has already been tried and died?** BrilliantMD took $1M of NSF money for blockchain-plus-ML denials
   reduction and the award ended December 2024; Albeado did fraud-detection SBIRs 2016–2021. Why those didn't become
   companies is due diligence you can do from public records, and a venture studio should know it before backing the
   next one.

## What the dry run produced (for scale)

129 relevant works with reconstructed abstracts, institutions, corresponding authors, funders and award IDs, OA
links, and a license flag (52 open for reuse, 24 restricted NC/ND, 53 unknown/closed — the "don't touch" bucket is
real and sizable). 176 grant records (NIH RePORTER + NSF). Limits: only 39 of 100 OA PDFs could be fetched (publishers
block automated fetches; needs Unpaywall mirrors / IA), and code links are near-absent because health-policy and
economics papers run on proprietary claims data and rarely release code — a fact about the field, so "find the code"
is a code-tier (GitHub) job, not a paper-tier one.

## Early companies surfaced (competitors or partners for Verzi; candidates or cautionary tales for SVS)

Actualization AI (FL, NSF Phase I through Oct 2025, "code-augmented policy" for reducing denials — an
LLM-follows-rules framework); Hidalga Technologies (AR, NSF Phase I from Oct 2025, oncology PA automation);
BrilliantMD (CA, $1M NSF Phase II ended Dec 2024, denials + PA); Handl Health (CA, $2.1M NIH Phase I/II, upfront
pricing + automated billing, ends Mar 2026); Syed Bukhari, St. John's University (I-Corps → $550K PFI-TT, trustworthy
medical-code recommendations, through 2027 — the purest university-to-startup candidate in the set).
Pages: `Uni Research Strategy/wiki/companies/`.

## Next

Wire PatentsView, Lens.org, I-Corps rosters, and TTO portals into the engine as a fourth tier; run SBIR.gov from the
box; then re-score. The team-reads pass across the ~10 key institutions is still the open item that turns the catalog
into a call list.
