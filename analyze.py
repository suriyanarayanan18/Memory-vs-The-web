# analysis script: turns the structured records into the numbers that tell the story
# no api calls here, just pandas, so it is free to run as many times as you want

import json
import pandas as pd
from collections import Counter

INPUT_FILE = "structured.jsonl"
TOTAL_QUERIES = 30

# fix inconsistent brand casing so Hoka and HOKA count as one brand
def canon_brand(name):
    key = name.strip().lower()
    mapping = {
        "asics": "ASICS", "hoka": "Hoka", "puma": "Puma", "nike": "Nike",
        "adidas": "Adidas", "brooks": "Brooks", "saucony": "Saucony",
        "new balance": "New Balance", "on": "On", "altra": "Altra",
        "salomon": "Salomon", "merrell": "Merrell", "la sportiva": "La Sportiva",
        "mizuno": "Mizuno", "topo": "Topo", "kiprun": "Kiprun",
        "reebok": "Reebok", "antepes": "Antepes"
    }
    return mapping.get(key, name.strip().title())

# load the records
rows = []
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

# explode into one row per brand mention, with casing fixed
long_rows = []
for r in rows:
    seen = set()
    for b in r["brands"]:
        cb = canon_brand(b)
        if cb in seen:
            continue
        seen.add(cb)
        long_rows.append({"query_id": r["query_id"], "intent_type": r["intent_type"], "mode": r["mode"], "brand": cb})

df = pd.DataFrame(long_rows)

# share of voice = percent of the 30 queries in that mode where the brand appears
def sov_table(frame):
    counts = frame.groupby(["mode", "brand"])["query_id"].nunique().reset_index(name="queries")
    counts["sov_pct"] = (counts["queries"] / TOTAL_QUERIES * 100).round(1)
    return counts

sov = sov_table(df)
memory_sov = sov[sov["mode"] == "memory"].set_index("brand")["sov_pct"]
retrieval_sov = sov[sov["mode"] == "retrieval"].set_index("brand")["sov_pct"]

# build the side by side comparison with the gap
all_brands = sorted(set(memory_sov.index) | set(retrieval_sov.index))
compare = pd.DataFrame(index=all_brands)
compare["memory_sov"] = memory_sov.reindex(all_brands).fillna(0)
compare["retrieval_sov"] = retrieval_sov.reindex(all_brands).fillna(0)
compare["gap"] = (compare["retrieval_sov"] - compare["memory_sov"]).round(1)
compare = compare.sort_values("retrieval_sov", ascending=False)

print("=" * 60)
print("SHARE OF VOICE: MEMORY vs RETRIEVAL (percent of 30 queries)")
print("=" * 60)
print(compare.to_string())

# brand universe differences
mem_brands = set(memory_sov.index)
ret_brands = set(retrieval_sov.index)
print("\nbrands ONLY in memory:", sorted(mem_brands - ret_brands))
print("brands ONLY in retrieval:", sorted(ret_brands - mem_brands))
print("brands in BOTH:", len(mem_brands & ret_brands))

# cited domain leaderboard, across retrieval queries
domain_counter = Counter()
for r in rows:
    if r["mode"] == "retrieval":
        for d in r["cited_domains"]:
            domain_counter[d] += 1

print("\n" + "=" * 60)
print("TOP CITED DOMAINS (number of queries that cited them, of 30)")
print("=" * 60)
for domain, count in domain_counter.most_common(12):
    print(f"{count:>3}  {domain}")

total_unique_domains = len(domain_counter)
print(f"\ntotal unique cited domains across all queries: {total_unique_domains}")

# save the comparison for the dashboard
compare.to_csv("sov_comparison.csv")
print("\nsaved sov_comparison.csv")