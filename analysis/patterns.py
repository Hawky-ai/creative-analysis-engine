"""Stage: cohort patterns. Per-trait cohorts vs segment baseline with bootstrap CIs.

Usage: python3 analysis/patterns.py <brand_dir> --kpi <conversions_field> [--spend-field spend]
Reads:  <brand_dir>/raw/canonical.json    [{hash, facet, value, evidence, source}, ...]
        <brand_dir>/raw/inventory.jsonl   one row per creative; must carry hash, spend field, kpi field
        <brand_dir>/raw/concept_map.json  optional; {facet: [{concept, values: [...]}]}
Writes: <brand_dir>/results/patterns.json
Verdict: CONFIRMED_WIN when the whole 90% CI beats baseline; CONFIRMED_LOSS when it's entirely worse.
"""
import json, random, sys, os, argparse
from collections import defaultdict, Counter

random.seed(7)
ap = argparse.ArgumentParser()
ap.add_argument("brand_dir")
ap.add_argument("--kpi", required=True, help="conversions field name in inventory.jsonl (e.g. leads, demo_sched, installs)")
ap.add_argument("--spend-field", default="spend")
ap.add_argument("--min-cohort", type=int, default=15)
ap.add_argument("--min-spend-share", type=float, default=0.02)
ap.add_argument("--bootstrap", type=int, default=1200)
a = ap.parse_args()
B, KPI, SP = a.brand_dir.rstrip("/"), a.kpi, a.spend_field

obs = json.load(open(f"{B}/raw/canonical.json"))
inv = {}
for line in open(f"{B}/raw/inventory.jsonl"):
    r = json.loads(line)
    if r.get("hash"): inv[r["hash"]] = r

cmap = {}
if os.path.exists(f"{B}/raw/concept_map.json"):
    for f, cons in json.load(open(f"{B}/raw/concept_map.json")).items():
        for c in cons:
            for v in c["values"]: cmap[(f, v)] = c["concept"]

pool = [h for h, r in inv.items() if r.get(KPI)]
tot_sp = sum(inv[h][SP] for h in pool)
tot_cv = sum(inv[h][KPI] for h in pool)
base = tot_sp / tot_cv
print(f"segment: {len(pool)} creatives, spend {tot_sp:,.0f}, {tot_cv:,.0f} {KPI}, base cost {base:,.1f}")

traits = defaultdict(set)
pset = set(pool)
for o in obs:
    if o["hash"] in pset:
        traits[("v", o["facet"], str(o["value"]))].add(o["hash"])
        cc = cmap.get((o["facet"], str(o["value"])))
        if cc: traits[("c", o["facet"], cc)].add(o["hash"])

def cost(hs):
    sp = sum(inv[h][SP] for h in hs); cv = sum(inv[h][KPI] for h in hs)
    return sp / cv if cv else None

def boot(hs):
    vals = []
    for _ in range(a.bootstrap):
        s = [random.choice(hs) for _ in hs]
        v = cost(s)
        if v: vals.append(v)
    vals.sort()
    return vals[int(.05 * len(vals))], vals[int(.95 * len(vals))]

pats = []
for (lvl, f, v), hs in traits.items():
    hs = list(hs)
    sp = sum(inv[h][SP] for h in hs)
    if len(hs) < a.min_cohort or sp < a.min_spend_share * tot_sp: continue
    val = cost(hs)
    if not val: continue
    lo, hi = boot(hs)
    verdict = "CONFIRMED_WIN" if hi < base else ("CONFIRMED_LOSS" if lo > base else "INCONCLUSIVE")
    pats.append({"level": lvl, "facet": f, "trait": v, "n": len(hs), "spend": round(sp),
                 "spend_share": round(sp / tot_sp, 3), "cpl": round(val, 1),
                 "ci90": [round(lo, 1), round(hi, 1)], "baseline": round(base, 1),
                 "verdict": verdict, "hashes": hs})

os.makedirs(f"{B}/results", exist_ok=True)
json.dump({"segment": {"n": len(pool), "spend": round(tot_sp), "conversions": tot_cv,
                        "kpi": KPI, "baseline_cpl": round(base, 1)}, "patterns": pats},
          open(f"{B}/results/patterns.json", "w"), indent=1)
print(Counter(p["verdict"] for p in pats))
for p in sorted([p for p in pats if p["verdict"] != "INCONCLUSIVE"], key=lambda x: x["cpl"])[:20]:
    print(f"{p['verdict'][10:]:<5} {p['facet']}:{p['trait'][:40]:<41} n={p['n']:<4} cost {p['cpl']} ci={p['ci90']}")
