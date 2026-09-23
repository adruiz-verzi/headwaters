#!/usr/bin/env python3
"""Merge LLM one-liner summaries (llm/out/sum_*.json) into svs_data.json.

Each sum_N.json maps a record index (string) to a one-sentence summary. Missing
records simply keep no summary (the site falls back to the cleaned abstract).
"""
import glob, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "svs_data.json")))
recs = data["records"]

merged = {}
for f in sorted(glob.glob(os.path.join(HERE, "llm/out/sum_*.json"))):
    try:
        part = json.load(open(f))
    except Exception as e:
        print(f"  skip {os.path.basename(f)}: {e}")
        continue
    for k, v in part.items():
        if isinstance(v, str) and v.strip():
            merged[int(k)] = v.strip()

applied = 0
for i, r in enumerate(recs):
    if i in merged:
        r["summary"] = merged[i]
        applied += 1
    else:
        r.pop("summary", None)

json.dump(data, open(os.path.join(HERE, "svs_data.json"), "w"), indent=1)
print(f"applied {applied}/{len(recs)} summaries")
