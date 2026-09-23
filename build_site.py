#!/usr/bin/env python3
"""Build the Headwaters demo site (single self-contained HTML) from scan data."""
import json, datetime, pathlib

HERE = pathlib.Path(__file__).parent
data = json.load(open(HERE / "svs_data.json"))
for r in data["records"]:
    r["abstract"] = (r.get("abstract", "") or "")[:240]

# "Deals you're missing": all-agency SBIR software companies from USAspending
# (mostly DoD, which SVS never sees through its Utah tech-transfer relationships).
# Normalize to the grants-view record shape and append.
_SW = ("software", "machine learning", "artificial intelligence", "ai-", "ai ",
       "algorithm", "platform", "analytics", "cyber", "autonom", "digital")
try:
    usa = json.load(open(HERE / "usaspending_sbir.json"))["records"]
except FileNotFoundError:
    usa = []
_agency_short = {"Department of Defense": "DoD",
                 "National Aeronautics and Space Administration": "NASA",
                 "Department of Energy": "DOE"}
import re as _re
_WET = _re.compile(r"therapeutic|vaccine|antibody|antigen receptor|car-?t|organoid|gene therapy|"
                   r"crispr|peptide|small molecule|monoclonal|\bdrug\b|cell therapy|nanoparticle|assay", _re.I)
for u in usa:
    title = (u.get("title") or "").strip()
    low = title.lower()
    blob = (title + " " + (u.get("abstract") or "")).lower()
    score = 0
    if any(t in low for t in _SW):
        score += 3
    if _WET.search(blob):
        score -= 6
    try:
        amt = int(float(u.get("amount") or 0))
    except (ValueError, TypeError):
        amt = 0
    if 0 < amt <= 2_000_000:
        score += 1
    data["records"].append({
        "source": _agency_short.get(u.get("agency", ""), "SBIR"),
        "code": "SBIR", "pi": "", "org": u.get("firm", ""),
        "state": u.get("state", ""), "city": "", "email": "",
        "amount": amt, "year": u.get("year", ""),
        "title": title[:110], "sector": "AI & software infrastructure",
        "university": "", "summary": "",
        "abstract": (u.get("abstract") or "")[:240],
        "why": "all-agency SBIR software (via USAspending); no university tie — a deal SVS would not see through its TTO relationships",
        "score": score, "id": u.get("id", ""),
        "url": "https://www.usaspending.gov/search",
    })
data["total"] = len(data["records"])
import collections
data["by_source"] = dict(collections.Counter(r["source"] for r in data["records"]))
DATA_JSON = json.dumps(data, separators=(",", ":"))

# "Deals like theirs": university-origin licensable software from the tech-transfer
# office (the source SVS's real portfolio actually comes from).
tto = json.load(open(HERE / "tto_utah.json"))
TTO_JSON = json.dumps(tto, separators=(",", ":"))

# National university software patents (USPTO PatentsView bulk), already filtered
# to country=US via the location join in patents_filter.py, with per-patent state.
try:
    pats = json.load(open(HERE / "patents_national.json"))
    pats["total_us_software_patents"] = len(pats["records"])
except FileNotFoundError:
    pats = {"records": [], "total_us_software_patents": 0,
            "distinct_universities": 0, "distinct_states": 0}
PATENTS_JSON = json.dumps(pats, separators=(",", ":"))

SCANNED = datetime.date(2026, 9, 22).strftime("%B %-d, %Y")

PAGE = r"""<title>Headwaters . Spinout Intelligence for Summit Venture Studio</title>
<style>
:root{
  --ground:#EEF1F0; --surface:#FFFFFF; --surface-2:#F5F7F6; --line:#DCE2E0;
  --ink:#14201E; --ink-dim:#5A6B69; --ink-faint:#8A9997;
  --accent:#BE5A20; --accent-soft:rgba(190,90,32,.10);
  --water:#2C7E72; --good:#3B8A56; --shadow:0 1px 2px rgba(20,32,30,.06),0 8px 24px rgba(20,32,30,.06);
}
@media (prefers-color-scheme:dark){
  :root{
    --ground:#0E1A1F; --surface:#15242B; --surface-2:#1B2E36; --line:#263C45;
    --ink:#E8EDEC; --ink-dim:#9EB1B2; --ink-faint:#6E8385;
    --accent:#E0864B; --accent-soft:rgba(224,134,75,.14);
    --water:#4FB0A5; --good:#5FB07A; --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
  }
}
:root[data-theme="light"]{
  --ground:#EEF1F0; --surface:#FFFFFF; --surface-2:#F5F7F6; --line:#DCE2E0;
  --ink:#14201E; --ink-dim:#5A6B69; --ink-faint:#8A9997;
  --accent:#BE5A20; --accent-soft:rgba(190,90,32,.10);
  --water:#2C7E72; --good:#3B8A56; --shadow:0 1px 2px rgba(20,32,30,.06),0 8px 24px rgba(20,32,30,.06);
}
:root[data-theme="dark"]{
  --ground:#0E1A1F; --surface:#15242B; --surface-2:#1B2E36; --line:#263C45;
  --ink:#E8EDEC; --ink-dim:#9EB1B2; --ink-faint:#6E8385;
  --accent:#E0864B; --accent-soft:rgba(224,134,75,.14);
  --water:#4FB0A5; --good:#5FB07A; --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  font-size:15px;line-height:1.5;letter-spacing:-.005em;}
:root{--serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
      --mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;}
.wrap{max-width:1300px;margin:0 auto;padding:0 24px}
.wrap .lede,.wrap .sub,.wrap .prov,.wrap .foot .grid{max-width:920px}
.wrap .lede{max-width:20ch}
a{color:var(--water);text-decoration:none}
a:hover{text-decoration:underline}

.mast{position:relative;overflow:hidden;border-bottom:1px solid var(--line);background:var(--surface)}
#contour{position:absolute;inset:0;width:100%;height:100%;opacity:.55;pointer-events:none}
.mast-in{position:relative;padding:38px 0 30px}
.brandrow{display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.mark{font-family:var(--serif);font-size:26px;font-weight:600;letter-spacing:-.01em}
.mark .drop{color:var(--accent)}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-faint)}
.theme-btn{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-dim);background:transparent;border:1px solid var(--line);border-radius:999px;padding:7px 14px;cursor:pointer}
.theme-btn:hover{color:var(--ink);border-color:var(--ink-faint)}
.lede{font-family:var(--serif);font-size:clamp(26px,4.2vw,40px);line-height:1.12;font-weight:600;
  text-wrap:balance;margin:22px 0 12px;max-width:20ch}
.lede em{font-style:italic;color:var(--accent)}
.sub{max-width:62ch;color:var(--ink-dim);font-size:16px}
.prov{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:20px;font-family:var(--mono);
  font-size:12px;color:var(--ink-faint);letter-spacing:.02em}
.prov b{color:var(--water);font-weight:500}
.live{display:inline-flex;align-items:center;gap:7px;color:var(--good)}
.dot{width:7px;height:7px;border-radius:50%;background:var(--good);animation:pulse 2.6s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(95,176,122,.5)}70%{box-shadow:0 0 0 7px rgba(95,176,122,0)}100%{box-shadow:0 0 0 0 rgba(95,176,122,0)}}
@media (prefers-reduced-motion:reduce){.dot{animation:none}}

.viewtabs{display:flex;gap:10px;margin:22px 0 6px;flex-wrap:wrap}
.vtab{display:flex;flex-direction:column;gap:2px;align-items:flex-start;font:inherit;cursor:pointer;
  background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 18px;color:var(--ink-dim);min-width:210px}
.vtab span{font-family:var(--mono);font-size:11px;letter-spacing:.04em;color:var(--ink-faint)}
.vtab[aria-pressed="true"]{border-color:var(--accent);color:var(--ink);
  background:color-mix(in srgb,var(--accent) 7%,var(--surface));font-weight:600}
.vtab[aria-pressed="true"] span{color:var(--accent)}
.tto-intro{max-width:78ch;color:var(--ink-dim);font-size:14.5px;margin:14px 0 18px}
.thead-tto,.trow{display:grid;grid-template-columns:minmax(0,150px) minmax(0,2fr) minmax(0,190px) minmax(0,150px) 90px;gap:18px;align-items:center}
.trow{padding:14px 22px;border-bottom:1px solid var(--line);cursor:pointer;transition:background .12s}
.trow:last-child{border-bottom:0}
.trow:hover{background:var(--surface-2)}
.trow>div{min-width:0}
.trow .ttitle{font-weight:600;font-size:14.5px;letter-spacing:-.01em}
.trow .tinv{font-family:var(--mono);font-size:12.5px;color:var(--ink-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block}
a.tinv{text-decoration:none}
a.tinv:hover{color:var(--water)}
.trow .tinv small{color:var(--ink-faint)}
.trow .tuni{font-family:var(--mono);font-size:12px;color:var(--water)}
.trow .tuni .no{color:var(--ink-faint)}
.trow .tcat{font-size:11.5px;padding:4px 10px;border-radius:999px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  display:inline-block;max-width:100%;color:var(--water);background:color-mix(in srgb,var(--water) 9%,transparent);border:1px solid color-mix(in srgb,var(--water) 22%,transparent)}
.trow .tid{font-family:var(--mono);font-size:12px;color:var(--accent);text-align:right}
@media (max-width:820px){.thead-tto{display:none}.trow{grid-template-columns:1fr auto;gap:10px}.trow .tcat,.trow .tuni{display:none}}
.thead-pat,.prow{display:grid;grid-template-columns:minmax(0,220px) minmax(0,2fr) minmax(0,180px) 100px 110px;gap:18px;align-items:center}
.prow{padding:14px 22px;border-bottom:1px solid var(--line);cursor:pointer;transition:background .12s}
.prow:last-child{border-bottom:0}
.prow:hover{background:var(--surface-2)}
.prow>div{min-width:0}
.prow .puni{font-family:var(--mono);font-size:12px;color:var(--water)}
.prow .pst{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);margin-left:6px}
.prow .ptitle{font-weight:600;font-size:14px;letter-spacing:-.01em}
.prow .pcat{display:inline-block;margin-top:4px;font-size:10.5px;padding:2px 8px;border-radius:999px;
  color:var(--water);background:color-mix(in srgb,var(--water) 9%,transparent);border:1px solid color-mix(in srgb,var(--water) 22%,transparent)}
.prow .pinv{font-family:var(--mono);font-size:12px;color:var(--ink-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.prow .pdate{font-family:var(--mono);font-size:12px;color:var(--ink-faint);text-align:right}
.prow .pnum{font-family:var(--mono);font-size:12px;color:var(--accent);text-align:right}
@media (max-width:820px){
  .thead-pat{display:none}
  .prow{grid-template-columns:1fr;gap:5px}
  .prow .pinv,.prow .pdate{display:none}
  .prow .puni{white-space:normal;color:var(--water)}
  .prow .pnum{text-align:left}
}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:14px;overflow:hidden;margin:26px 0}
.kpi{background:var(--surface);padding:18px 20px}
.kpi .n{font-family:var(--mono);font-size:25px;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.kpi .n.acc{color:var(--accent)} .kpi .n.wat{color:var(--water)}
.kpi .l{font-size:12px;color:var(--ink-dim);margin-top:4px;line-height:1.35}
@media (max-width:980px){.kpis{grid-template-columns:repeat(3,1fr)}}
@media (max-width:620px){.kpis{grid-template-columns:repeat(2,1fr)}}

.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:8px 0 18px}
.search{flex:1 1 260px;min-width:200px;position:relative}
.search input{width:100%;padding:10px 14px 10px 36px;border:1px solid var(--line);border-radius:10px;
  background:var(--surface);color:var(--ink);font-size:14px;font-family:inherit}
.search svg{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--ink-faint)}
.search input:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:transparent}
select{font-family:inherit;font-size:13px;color:var(--ink);background:var(--surface);
  border:1px solid var(--line);border-radius:10px;padding:9px 12px;cursor:pointer}
select:focus{outline:2px solid var(--accent);outline-offset:1px}
.seg{display:inline-flex;padding:3px;gap:2px;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
.seg button{font:inherit;font-size:13px;border:0;background:transparent;color:var(--ink-dim);padding:6px 12px;border-radius:7px;cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--accent-soft);color:var(--accent);font-weight:600}
.toggle{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--ink-dim);
  border:1px solid var(--line);border-radius:10px;padding:8px 12px;cursor:pointer;user-select:none}
.toggle input{accent-color:var(--water)}
.count{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--ink-faint);letter-spacing:.02em}

.feed{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--surface);box-shadow:var(--shadow)}
.thead,.row{display:grid;
  grid-template-columns:56px minmax(0,1.7fr) minmax(0,168px) minmax(0,150px) 116px 84px 40px;
  gap:18px;align-items:center}
.thead{padding:12px 22px;border-bottom:1px solid var(--line);background:var(--surface-2);
  font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint)}
.thead .r{text-align:right}
.row{padding:15px 22px;border-bottom:1px solid var(--line);cursor:pointer;transition:background .12s}
.row:last-child{border-bottom:0}
.row:hover{background:var(--surface-2)}
.row:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.row>div{min-width:0}
.fit{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;
  width:44px;height:44px;border-radius:11px;font-family:var(--mono);font-weight:600;font-variant-numeric:tabular-nums}
.fit b{font-size:17px;line-height:1}
.fit span{font-size:8px;letter-spacing:.08em;text-transform:uppercase;opacity:.85;margin-top:2px}
.org{font-weight:600;font-size:15px;letter-spacing:-.01em}
.hasmail{color:var(--accent);font-size:11px;margin-left:7px;vertical-align:1px}
.ttl{color:var(--ink-dim);font-size:13px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.univ{font-family:var(--mono);font-size:11.5px;color:var(--water);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vok{color:var(--good)}
.mailtag{display:inline-flex;align-items:center;gap:5px;margin-top:6px;font-family:var(--mono);font-size:11.5px;
  color:var(--accent);background:var(--accent-soft);border:1px solid color-mix(in srgb,var(--accent) 30%,transparent);
  border-radius:7px;padding:2px 9px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mailtag:hover{text-decoration:none;background:color-mix(in srgb,var(--accent) 16%,transparent)}
.pi{font-family:var(--mono);font-size:12.5px;color:var(--ink-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sector{display:inline-block;max-width:100%;font-size:11.5px;line-height:1.3;padding:4px 10px;border-radius:999px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border:1px solid transparent}
.sector.off{opacity:.62}
.prog{display:flex;flex-wrap:wrap;gap:5px}
.tag{font-family:var(--mono);font-size:10.5px;letter-spacing:.04em;padding:3px 7px;border-radius:6px;
  border:1px solid var(--line);color:var(--ink-dim);white-space:nowrap}
.tag.sttr{color:var(--water);border-color:var(--water);background:color-mix(in srgb,var(--water) 8%,transparent)}
.tag.src{color:var(--ink-faint)}
.amt{font-family:var(--mono);font-size:14px;font-variant-numeric:tabular-nums;text-align:right}
.st{font-family:var(--mono);font-size:12px;color:var(--ink-faint);text-align:center}
.st.ut{color:var(--accent);font-weight:600}
.detail{padding:18px 20px 18px 84px;border-bottom:1px solid var(--line);background:var(--surface-2)}
.detail p{margin:0 0 12px;color:var(--ink-dim);font-size:13.5px;max-width:80ch}
.detail p.summary{color:var(--ink);font-size:14.5px;font-weight:500;line-height:1.5}
.why{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.why .w{font-size:11.5px;padding:4px 9px;border-radius:999px;background:var(--accent-soft);color:var(--accent)}
.why .w.pen{background:color-mix(in srgb,var(--ink-faint) 14%,transparent);color:var(--ink-faint)}
.contact{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin:0 0 14px}
.contact .lab{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-faint)}
.contact .loc{font-family:var(--mono);font-size:12px;color:var(--ink-dim)}
.contact .note{font-size:11.5px;color:var(--ink-faint);font-style:italic}
.clink{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:12px;
  padding:5px 11px;border:1px solid var(--line);border-radius:8px;color:var(--water);white-space:nowrap}
.clink:hover{border-color:var(--water);text-decoration:none;background:color-mix(in srgb,var(--water) 7%,transparent)}
.clink.mail{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 40%,transparent)}
.clink.mail:hover{border-color:var(--accent);background:var(--accent-soft)}
.src-link{font-family:var(--mono);font-size:12px}
.empty{padding:60px 20px;text-align:center;color:var(--ink-faint)}
@media (max-width:900px){
  .thead{display:none}
  .row{grid-template-columns:44px 1fr auto;gap:12px}
  .row .pi,.row .prog,.row .st,.row .sectorcell{display:none}
  .row .amt{font-size:12px;color:var(--ink-faint)}
  .detail{padding-left:20px}
}
.foot{padding:34px 0 60px;color:var(--ink-faint);font-size:13px;line-height:1.6}
.foot h4{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-dim);margin:0 0 10px}
.foot .grid{display:grid;grid-template-columns:1fr 1fr;gap:28px;max-width:920px}
.foot b{color:var(--ink-dim)}
@media (max-width:700px){.foot .grid{grid-template-columns:1fr}}
</style>

<div class="mast">
  <canvas id="contour" aria-hidden="true"></canvas>
  <div class="wrap mast-in">
    <div class="brandrow">
      <div class="brand">
        <span class="mark">Head<span class="drop">waters</span></span>
        <span class="kicker">Spinout intelligence</span>
      </div>
      <button class="theme-btn" id="theme" type="button">Theme</button>
    </div>
    <h1 class="lede">The university software pipeline, <em>ranked before it has a name.</em></h1>
    <p class="sub">One feed over four sources: university tech-transfer listings, faculty research, federal
      grants, and patents. <b>Deals like theirs</b> is licensable university software from tech-transfer
      offices. <b>Grant-backed software cos</b> is federally funded software companies, a separate,
      already-formed pool. The two are labeled honestly because they are not the same motion.</p>
    <div class="prov">
      <span class="live"><span class="dot"></span> Confidential, prepared for Summit Venture Studio</span>
      <span>Sources <b>U of Utah tech transfer</b> · <b>NIH</b> · <b>NSF</b> · <b>DoD</b> · <b>OpenAlex</b></span>
      <span>Snapshot __SCANNED__ · refreshes on a scheduled run</span>
    </div>
  </div>
</div>

<div class="wrap">
  <div class="viewtabs" role="group" aria-label="View">
    <button id="tab-tto" class="vtab" aria-pressed="true">Deals like theirs<span>university IP, licensable now</span></button>
    <button id="tab-patents" class="vtab" aria-pressed="false">University patents<span>all US universities, national</span></button>
    <button id="tab-grants" class="vtab" aria-pressed="false">Grant-backed software cos<span>SBIR/STTR + DoD, not TTO deals</span></button>
  </div>

  <div id="view-tto">
    <p class="tto-intro">The <b>licensable-now</b> layer: software available to license today from a university
      tech-transfer office, with the faculty inventor attached and a one-click path to the listing. Shown here
      for the <b>University of Utah</b> (each school's licensing portal is different, so this layer is added school
      by school). For coverage of <b>every US university</b>, see the University patents tab. Already-licensed
      inventions drop off this list, so what you see is the pipeline ahead, not deals already done.</p>
    <div class="controls">
      <select id="tto-cat" aria-label="Category"><option value="">All categories</option></select>
      <span class="count" id="tto-count"></span>
    </div>
    <div class="feed">
      <div class="thead thead-tto">
        <div>Category</div><div>Technology</div><div>Faculty inventor</div><div>University</div><div class="r">Tech ID</div>
      </div>
      <div id="tto-rows"></div>
    </div>
  </div>

  <div id="view-patents" hidden>
    <p class="tto-intro">Recent (2021+) software patents assigned to <b>US universities</b>, nationwide, straight
      from USPTO's disambiguated bulk data. This is the "the tech-transfer office already protected it" signal
      at national scale: a professor's software the university thought worth patenting. Assignee names are
      USPTO-disambiguated, so the university is exact.</p>
    <div class="controls">
      <select id="pat-state" aria-label="State"><option value="">All states</option></select>
      <select id="pat-univ" aria-label="University"><option value="">All universities</option></select>
      <select id="pat-cat" aria-label="Software category"><option value="">All software types</option></select>
      <span class="count" id="pat-count"></span>
    </div>
    <div class="feed">
      <div class="thead thead-pat">
        <div>University</div><div>Technology</div><div>Inventors</div><div class="r">Granted</div><div class="r">Patent</div>
      </div>
      <div id="pat-rows"></div>
    </div>
  </div>

  <div id="view-grants" hidden>
  <div class="kpis" id="kpis"></div>
  <div class="controls">
    <div class="seg" role="group" aria-label="Source">
      <button data-src="all" aria-pressed="true">All</button>
      <button data-src="NIH" aria-pressed="false">NIH</button>
      <button data-src="NSF" aria-pressed="false">NSF</button>
      <button data-src="DoD" aria-pressed="false">DoD</button>
    </div>
    <select id="minscore" aria-label="Minimum fit score">
      <option value="-99">Any fit</option>
      <option value="6">High fit (6+)</option>
      <option value="8">Top fit (8+)</option>
    </select>
    <select id="sector" aria-label="Sector"><option value="">All sectors</option></select>
    <select id="phase" aria-label="Phase">
      <option value="">All phases</option>
      <option value="Phase I">Phase I</option>
      <option value="Phase II">Phase II</option>
    </select>
    <select id="state" aria-label="State"><option value="">All states</option></select>
    <label class="toggle"><input type="checkbox" id="sttr"> University-linked (STTR)</label>
    <label class="toggle"><input type="checkbox" id="hasemail"> Has PI email</label>
    <label class="toggle"><input type="checkbox" id="softonly"> Software-only</label>
    <span class="count" id="count"></span>
  </div>

  <div class="feed">
    <div class="thead">
      <div>Fit</div><div>Company / Technology</div><div>Sector</div><div>Principal investigator</div>
      <div>Program</div><div class="r">Award</div><div class="r">St</div>
    </div>
    <div id="rows"></div>
  </div>
  </div>

  <div class="foot">
    <div class="grid">
      <div>
        <h4>How the score works</h4>
        <p>Each signal is scored additively for fit with SVS: software in the title, STTR (which requires a
        university partner), a named university, Phase I stage, and a small early check. Wet-lab and therapeutic
        work is penalized, because SVS invests in software. The score is transparent: every row shows its reasons.</p>
      </div>
      <div>
        <h4>What this sample is, and is not</h4>
        <p>A snapshot of <b>__TOTAL__</b> SBIR/STTR software signals across <b>NIH, NSF, and DoD</b>
        (DoD via USAspending). This grant pool is competitive awareness, not SVS's sourcing motion;
        these are already-formed companies, not licensable university packages. A production feed adds
        PatentsView (university patents) and daily tech-transfer refresh. Public federal + tech-transfer
        data; every row links to its source. Built by Verzi.</p>
      </div>
    </div>
  </div>
</div>

<script id="data" type="application/json">__DATA__</script>
<script id="ttodata" type="application/json">__TTO__</script>
<script id="patdata" type="application/json">__PATENTS__</script>
<script>
(function(){
  "use strict";
  var DATA = JSON.parse(document.getElementById("data").textContent);
  var recs = DATA.records;
  var root = document.documentElement;
  var DASH = "—";

  function el(tag, attrs, kids){
    var n = document.createElement(tag);
    if(attrs) for(var k in attrs){
      if(k==="class") n.className = attrs[k];
      else if(k==="text") n.textContent = attrs[k];
      else if(k==="style") n.style.cssText = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    if(kids) kids.forEach(function(c){ if(c) n.appendChild(typeof c==="string"?document.createTextNode(c):c); });
    return n;
  }
  function clear(n){ while(n.firstChild) n.removeChild(n.firstChild); }
  function money(n){ if(!n) return DASH; if(n>=1e6) return "$"+(n/1e6).toFixed(1)+"m"; return "$"+Math.round(n/1e3)+"k"; }
  function isSttr(r){ return r.code==="R41"||r.code==="R42"||r.code==="STTR"; }
  function phase(r){ if(r.code==="R41"||r.code==="R43") return "Phase I";
    if(r.code==="R42"||r.code==="R44") return "Phase II"; return /phase ii/i.test(r.title)?"Phase II":"Phase I"; }
  function tier(s){ return s>=8?["var(--good)","best"] : s>=6?["var(--water)","strong"]
    : s>=3?["var(--accent)","fair"] : ["var(--ink-faint)","low"]; }
  function fitBg(c){ return "color-mix(in srgb,"+c+" 15%,transparent)"; }
  var OFF={"Therapeutics & biotech":1,"Medical device & hardware":1};
  function offThesis(r){ return !!OFF[r.sector]; }

  function curTheme(){ return root.getAttribute("data-theme") ||
    (matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light"); }
  var tbtn = document.getElementById("theme");
  tbtn.addEventListener("click", function(){
    var next = curTheme()==="dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    tbtn.textContent = next==="dark" ? "Light" : "Dark";
    drawContour();
  });

  /* KPI strip */
  (function(){
    var hi = recs.filter(function(r){return r.score>=6;}).length;
    var sttr = recs.filter(isSttr).length;
    var cap = recs.reduce(function(a,r){return a+(r.amount||0);},0);
    var states = new Set(recs.map(function(r){return r.state;}).filter(Boolean)).size;
    var contacts = recs.filter(function(r){return r.email;}).length;
    var k = [[String(recs.length),"Ranked spinout signals","acc"],
             [String(hi),"High-fit for SVS thesis (6+)","wat"],
             [String(sttr),"University-linked (STTR)","wat"],
             [String(contacts),"NSF PI emails on file (real)","acc"],
             ["$"+(cap/1e6).toFixed(0)+"m","Early federal capital tracked",""],
             [String(states),"States represented",""]];
    var box = document.getElementById("kpis");
    k.forEach(function(x){
      box.appendChild(el("div",{class:"kpi"},[
        el("div",{class:"n "+x[2],text:x[0]}), el("div",{class:"l",text:x[1]})]));
    });
  })();

  /* state dropdown, alphabetical */
  (function(){
    var counts={}; recs.forEach(function(r){ if(r.state) counts[r.state]=(counts[r.state]||0)+1; });
    var sel=document.getElementById("state");
    Object.keys(counts).sort().forEach(function(s){
      sel.appendChild(el("option",{value:s,text:s+" ("+counts[s]+")"}));
    });
  })();

  /* sector dropdown, alphabetical with counts */
  (function(){
    var counts={}; recs.forEach(function(r){ counts[r.sector]=(counts[r.sector]||0)+1; });
    var sel=document.getElementById("sector");
    Object.keys(counts).sort().forEach(function(s){
      sel.appendChild(el("option",{value:s,text:s+" ("+counts[s]+")"}));
    });
  })();

  var F={src:"all",min:-99,state:"",sector:"",phase:"",sttr:false,hasemail:false,softonly:false};
  var rowsEl=document.getElementById("rows");
  var current=[];

  function apply(){
    current=recs.filter(function(r){
      if(F.src!=="all" && r.source!==F.src) return false;
      if(r.score<F.min) return false;
      if(F.state && r.state!==F.state) return false;
      if(F.sector && r.sector!==F.sector) return false;
      if(F.phase && phase(r)!==F.phase) return false;
      if(F.sttr && !isSttr(r)) return false;
      if(F.hasemail && !r.email) return false;
      if(F.softonly && offThesis(r)) return false;
      return true;
    });
    render();
    document.getElementById("count").textContent=current.length+" of "+recs.length+" signals";
  }

  function tagEl(cls,txt){ return el("span",{class:"tag "+cls,text:txt}); }

  function render(){
    clear(rowsEl);
    if(!current.length){ rowsEl.appendChild(el("div",{class:"empty",text:"No signals match these filters."})); return; }
    current.forEach(function(r,i){
      var t=tier(r.score), c=t[0];
      var fit=el("div",{class:"fit",style:"color:"+c+";background:"+fitBg(c)},
        [el("b",{text:String(r.score)}), el("span",{text:t[1]})]);
      var orgline=el("div",{class:"org"},[r.org||DASH]);
      if(r.email) orgline.appendChild(el("span",{class:"hasmail",title:"Direct PI email on file",text:"✉"}));
      var mainKids=[orgline, el("div",{class:"ttl",text:r.title})];
      if(r.university){
        var u=el("div",{class:"univ"},["◈ "+r.university]);
        if(r.university_confirmed) u.appendChild(el("span",{class:"vok",title:"Confirmed by OpenAlex",text:" ✓"}));
        mainKids.push(u);
      }
      if(r.email){
        var mailTag=el("a",{class:"mailtag",href:"mailto:"+r.email,title:"Email "+r.pi},["✉ "+r.email]);
        mailTag.addEventListener("click",function(e){ e.stopPropagation(); });
        mainKids.push(mailTag);
      }
      var main=el("div",null,mainKids);
      var off=offThesis(r), on=!off && r.sector!=="Other";
      var pc=on?"var(--water)":"var(--ink-faint)";
      var pill=el("span",{class:"sector"+(off?" off":""),title:r.sector,
        style:"color:"+pc+";background:color-mix(in srgb,"+pc+" 9%,transparent);border-color:color-mix(in srgb,"+pc+" 22%,transparent)",
        text:r.sector});
      var prog=el("div",{class:"prog"},[
        tagEl(isSttr(r)?"sttr":"",r.code), tagEl("",phase(r)), tagEl("src",r.source)]);
      var row=el("div",{class:"row","data-i":String(i),role:"button",tabindex:"0","aria-expanded":"false"},[
        fit, main, el("div",{class:"sectorcell"},[pill]), el("div",{class:"pi",text:r.pi||DASH}), prog,
        el("div",{class:"amt",text:money(r.amount)}),
        el("div",{class:"st"+(r.state==="UT"?" ut":""),text:r.state||DASH})]);
      rowsEl.appendChild(row);
    });
  }

  function toggle(row){
    if(!row) return;
    var nx=row.nextElementSibling;
    if(nx && nx.classList.contains("detail")){ nx.remove(); row.setAttribute("aria-expanded","false"); return; }
    Array.prototype.forEach.call(document.querySelectorAll(".detail"),function(d){d.remove();});
    Array.prototype.forEach.call(document.querySelectorAll('.row[aria-expanded="true"]'),
      function(x){x.setAttribute("aria-expanded","false");});
    var r=current[+row.getAttribute("data-i")];
    var why=el("div",{class:"why"});
    r.why.split("; ").filter(Boolean).forEach(function(w){
      var pen=/PENALTY/i.test(w);
      why.appendChild(el("span",{class:"w"+(pen?" pen":""),text:w.replace("PENALTY: ","")}));
    });
    var d=el("div",{class:"detail"},[why]);
    if(r.summary) d.appendChild(el("p",{class:"summary",text:r.summary}));
    if(r.abstract) d.appendChild(el("p",{text:(r.summary?"From the grant abstract: ":"")
      +r.abstract+(r.abstract.length>=240?"…":"")}));

    // Contact enrichment. Email is a real, public value only for NSF awards.
    var contact=el("div",{class:"contact"},[el("span",{class:"lab",text:"Reach the PI"})]);
    if(r.city||r.state) contact.appendChild(el("span",{class:"loc",
      text:[r.city,r.state].filter(Boolean).join(", ")}));
    if(r.email) contact.appendChild(el("a",{class:"clink mail",href:"mailto:"+r.email,text:"✉ "+r.email}));
    contact.appendChild(el("a",{class:"clink",href:r.linkedin,target:"_blank",rel:"noopener",text:"LinkedIn ↗"}));
    contact.appendChild(el("a",{class:"clink",href:r.google,target:"_blank",rel:"noopener",text:"Web search ↗"}));
    if(!r.email) contact.appendChild(el("span",{class:"note",text:"NIH does not publish PI email"}));
    d.appendChild(contact);

    // PI research profile from OpenAlex. Labeled as the PI's profile, not asserted
    // as the grant's university (name-only resolution is only ~35% precise).
    if(r.oa_url || r.oa_affiliation){
      var prof=el("div",{class:"contact"},[el("span",{class:"lab",text:"PI research profile"})]);
      if(r.oa_affiliation) prof.appendChild(el("span",{class:"loc",
        text:r.oa_affiliation+(r.oa_works?" · "+r.oa_works+" works":"")}));
      if(r.oa_url) prof.appendChild(el("a",{class:"clink",href:r.oa_url,target:"_blank",rel:"noopener",text:"OpenAlex ↗"}));
      prof.appendChild(el("span",{class:"note",text:"scholarly affiliation, verify"}));
      d.appendChild(prof);
    }

    d.appendChild(el("a",{class:"src-link",href:r.url,target:"_blank",rel:"noopener",
      text:"View award on "+r.source+" ↗"}));
    row.after(d); row.setAttribute("aria-expanded","true");
  }
  rowsEl.addEventListener("click",function(e){ toggle(e.target.closest(".row")); });
  rowsEl.addEventListener("keydown",function(e){
    var row=e.target.closest && e.target.closest(".row");
    if(row && (e.key==="Enter"||e.key===" ")){ e.preventDefault(); toggle(row); }
  });

  Array.prototype.forEach.call(document.querySelectorAll(".seg button"),function(b){
    b.addEventListener("click",function(){
      Array.prototype.forEach.call(document.querySelectorAll(".seg button"),
        function(x){x.setAttribute("aria-pressed","false");});
      b.setAttribute("aria-pressed","true"); F.src=b.getAttribute("data-src"); apply();
    });
  });
  document.getElementById("minscore").addEventListener("change",function(e){ F.min=+e.target.value; apply(); });
  document.getElementById("state").addEventListener("change",function(e){ F.state=e.target.value; apply(); });
  document.getElementById("sector").addEventListener("change",function(e){ F.sector=e.target.value; apply(); });
  document.getElementById("phase").addEventListener("change",function(e){ F.phase=e.target.value; apply(); });
  document.getElementById("sttr").addEventListener("change",function(e){ F.sttr=e.target.checked; apply(); });
  document.getElementById("hasemail").addEventListener("change",function(e){ F.hasemail=e.target.checked; apply(); });
  document.getElementById("softonly").addEventListener("change",function(e){ F.softonly=e.target.checked; apply(); });
  apply();

  /* ---- Deals-like-theirs (TTO) view ---- */
  var TTO=JSON.parse(document.getElementById("ttodata").textContent).records||[];
  (function(){
    var box=document.getElementById("tto-rows");
    // sort: Utah-confirmed first, then by scholarly output (established lab)
    TTO.sort(function(a,b){ return (b.utah_confirmed?1:0)-(a.utah_confirmed?1:0) || (b.oa_works||0)-(a.oa_works||0); });
    var PORTAL="https://technologylicensing.utah.edu/available-technologies/";
    var ttoCat="";
    function renderTTO(){
      clear(box);
      var list=TTO.filter(function(r){ return !ttoCat || r.category===ttoCat; });
      list.forEach(function(r){
        var nm=r.lead_inventor||(r.inventors||"").split(",")[0]||DASH;
        var inv;
        // Only link/annotate OpenAlex when the match resolves to Utah; a namesake
        // guess (Florida, LSU) is worse than nothing. Otherwise show the name plain.
        if(r.utah_confirmed && r.oa_url){
          inv=el("a",{class:"tinv",href:r.oa_url,target:"_blank",rel:"noopener",title:"OpenAlex profile"},[nm]);
          inv.addEventListener("click",function(e){ e.stopPropagation(); });
          if(r.oa_works) inv.appendChild(el("small",{text:" · "+r.oa_works+"w"}));
        } else {
          inv=el("div",{class:"tinv"},[nm]);
        }
        var extra=(r.inventors||"").match(/\+\d+/);
        if(extra) inv.appendChild(el("small",{text:" "+extra[0]}));
        var uni=el("div",{class:"tuni"},["University of Utah"]);
        if(r.utah_confirmed) uni.appendChild(el("span",{class:"vok",title:"Inventor confirmed at Utah via OpenAlex",text:" ✓"}));
        var row=el("div",{class:"trow",role:"button",tabindex:"0",title:"Open this technology's listing at the U of Utah TTO"},[
          el("div",null,[el("span",{class:"tcat",text:r.category||"Software"})]),
          el("div",null,[el("div",{class:"ttitle",text:r.title})]),
          inv, uni, el("div",{class:"tid",text:r.id||""})]);
        row.addEventListener("click",function(){ window.open(PORTAL+encodeURIComponent(r.id),"_blank","noopener"); });
        box.appendChild(row);
      });
      var c=document.getElementById("tto-count");
      if(c) c.textContent=list.length+" of "+TTO.length+" licensable technologies";
    }
    var catSel=document.getElementById("tto-cat");
    if(catSel){
      var cats={}; TTO.forEach(function(r){ if(r.category) cats[r.category]=(cats[r.category]||0)+1; });
      Object.keys(cats).sort().forEach(function(k){ catSel.appendChild(el("option",{value:k,text:k+" ("+cats[k]+")"})); });
      catSel.addEventListener("change",function(e){ ttoCat=e.target.value; renderTTO(); });
    }
    renderTTO();
  })();

  /* ---- University patents (national) view ---- */
  var PAT=JSON.parse(document.getElementById("patdata").textContent);
  (function(){
    var box=document.getElementById("pat-rows"), recs=PAT.records||[];
    var uniSel=document.getElementById("pat-univ"), stSel=document.getElementById("pat-state"),
        catSel=document.getElementById("pat-cat");
    var pUni="", pState="", pCat="";
    var stc={}; recs.forEach(function(r){ if(r.state) stc[r.state]=(stc[r.state]||0)+1; });
    Object.keys(stc).sort().forEach(function(s){
      stSel.appendChild(el("option",{value:s,text:s+" ("+stc[s]+")"})); });
    var cc={}; recs.forEach(function(r){ if(r.category) cc[r.category]=(cc[r.category]||0)+1; });
    Object.keys(cc).sort().forEach(function(c){
      catSel.appendChild(el("option",{value:c,text:c+" ("+cc[c]+")"})); });
    function fillUniv(){
      clear(uniSel); uniSel.appendChild(el("option",{value:"",text:"All universities"}));
      var c={}; recs.forEach(function(r){ if(!pState||r.state===pState) c[r.university]=(c[r.university]||0)+1; });
      Object.keys(c).sort().forEach(function(u){ uniSel.appendChild(el("option",{value:u,text:u+" ("+c[u]+")"})); });
    }
    var CAP=1500;
    function draw(){
      clear(box);
      var list=recs.filter(function(r){
        return (!pUni||r.university===pUni)&&(!pState||r.state===pState)&&(!pCat||r.category===pCat); });
      list.slice(0,CAP).forEach(function(r){
        var uni=el("div",null,[el("span",{class:"puni",text:r.university})]);
        if(r.state) uni.appendChild(el("span",{class:"pst",text:" "+r.state}));
        var title=el("div",null,[el("div",{class:"ptitle",text:r.title})]);
        if(r.category) title.appendChild(el("span",{class:"pcat",text:r.category}));
        var row=el("div",{class:"prow",role:"button",tabindex:"0",title:"Open patent on Google Patents"},[
          uni, title,
          el("div",{class:"pinv",text:r.inventors||DASH}),
          el("div",{class:"pdate",text:(r.date||"").slice(0,7)}),
          el("div",{class:"pnum",text:"US"+r.id})]);
        row.addEventListener("click",function(){ window.open(r.url,"_blank","noopener"); });
        box.appendChild(row);
      });
      var us={}, ss={};
      list.forEach(function(r){ us[r.university]=1; if(r.state) ss[r.state]=1; });
      var un=Object.keys(us).length, sn=Object.keys(ss).length;
      var shown=Math.min(list.length,CAP);
      var head=(shown<list.length ? "showing "+shown.toLocaleString()+" of "+list.length.toLocaleString()
                                  : list.length.toLocaleString())
        +" US university software patents · "+un+(un===1?" university":" universities")
        +" · "+sn+(sn===1?" state":" states");
      if(shown<list.length) head+=" · narrow with the filters to see all";
      document.getElementById("pat-count").textContent=head;
    }
    fillUniv();
    stSel.addEventListener("change",function(e){ pState=e.target.value; pUni=""; fillUniv(); draw(); });
    uniSel.addEventListener("change",function(e){ pUni=e.target.value; draw(); });
    catSel.addEventListener("change",function(e){ pCat=e.target.value; draw(); });
    draw();
  })();

  /* ---- view toggle (3 views) ---- */
  var VIEWS={tto:["tab-tto","view-tto"],patents:["tab-patents","view-patents"],grants:["tab-grants","view-grants"]};
  function setView(which){
    for(var k in VIEWS){
      var on=k===which;
      document.getElementById(VIEWS[k][0]).setAttribute("aria-pressed",on?"true":"false");
      document.getElementById(VIEWS[k][1]).hidden=!on;
    }
  }
  Object.keys(VIEWS).forEach(function(k){
    document.getElementById(VIEWS[k][0]).addEventListener("click",function(){ setView(k); });
  });

  /* topographic contour motif */
  var cv=document.getElementById("contour"), ctx=cv.getContext("2d");
  function drawContour(){
    var m=cv.parentElement.getBoundingClientRect(), dpr=Math.min(devicePixelRatio||1,2);
    cv.width=m.width*dpr; cv.height=m.height*dpr; ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,m.width,m.height);
    var dark=curTheme()==="dark", W=m.width, H=m.height, N=13;
    for(var i=0;i<N;i++){
      var f=i/(N-1); ctx.beginPath();
      ctx.strokeStyle = i%4===0
        ? (dark?"rgba(224,134,75,":"rgba(190,90,32,")+(0.14-f*0.07)+")"
        : (dark?"rgba(79,176,165,":"rgba(44,126,114,")+(0.10-f*0.05)+")";
      ctx.lineWidth = i%4===0?1.4:0.8;
      var base=H*0.2 + f*H*0.74;
      for(var x=0;x<=W;x+=6){
        var y=base + Math.sin(x*0.006+i*0.9)*22*(1-f*0.4) + Math.sin(x*0.017+i*1.7)*9 + Math.sin(x*0.003-i*0.5)*30*f;
        x===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
      }
      ctx.stroke();
    }
  }
  drawContour();
  var rt; addEventListener("resize",function(){ clearTimeout(rt); rt=setTimeout(drawContour,150); });
})();
</script>
"""

out = (PAGE.replace("__DATA__", DATA_JSON)
           .replace("__TTO__", TTO_JSON)
           .replace("__PATENTS__", PATENTS_JSON)
           .replace("__SCANNED__", SCANNED)
           .replace("__TOTAL__", str(data["total"])))
(HERE / "headwaters.html").write_text(out)
print("wrote headwaters.html", round(len(out) / 1024), "KB")
