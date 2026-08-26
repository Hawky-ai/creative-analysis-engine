"""Creative recipes: 2-3 trait combinations that (a) forecast well (V2 bundle),
(b) are not contradicted by the causal layer (V3 within), (c) have enough evidence."""
import json, sys
from itertools import combinations
from collections import defaultdict

BRAND = sys.argv[1]
CONV = 'demo_sched' if BRAND == 'bhanzu' else 'leads'
inv = {json.loads(l)['hash']: json.loads(l) for l in open(f'{BRAND}/raw/inventory.jsonl')}
obs = json.load(open(f'{BRAND}/raw/canonical.json'))
v3 = json.load(open(f'{BRAND}/results/engine_v3.json'))
win_eff = {k: v['multiplier'] for k, v in v3['within_effects'].items()}
traits_of = defaultdict(set)
for o in obs: traits_of[o['hash']].add((o['facet'], o['value']))

hs_all = [h for h in inv if inv[h].get(CONV) and inv[h]['spend'] > 20000 and traits_of.get(h)]
tot_sp = sum(inv[h]['spend'] for h in hs_all); tot_cv = sum(inv[h][CONV] for h in hs_all)
base = tot_sp/tot_cv
def cost(hs):
    sp = sum(inv[h]['spend'] for h in hs); cv = sum(inv[h][CONV] for h in hs)
    return (sp/cv, sp) if cv else (None, sp)

th = defaultdict(set)
for h in hs_all:
    for t in traits_of[h]: th[t].add(h)
singles = {t: cost(list(hs))[0] for t, hs in th.items() if len(hs) >= 12}
good = [t for t, c in singles.items() if c and c < base*0.9]

def causal_ok(ts):
    # no member actively harmful at creative level
    return all(win_eff.get(f'{t[0]}:{t[1]}', 1.0) <= 1.10 for t in ts)

rows = []
for r in (2, 3):
    for combo in combinations(sorted(good), r):
        if len({t[0] for t in combo}) < r: continue     # distinct facets
        hs = set.intersection(*[th[t] for t in combo])
        if len(hs) < 10: continue
        c, sp = cost(list(hs))
        if not c or sp < 0.015*tot_sp: continue
        best_single = min(singles[t] for t in combo)
        rows.append({'recipe': [f'{t[0]}:{t[1]}' for t in combo], 'n': len(hs),
                     'spend': round(sp), 'cost': round(c), 'vs_base': round(c/base, 2),
                     'vs_best_single': round(c/best_single, 2), 'causal_ok': causal_ok(combo)})
rows.sort(key=lambda r: r['cost'])
# keep recipes that add value over their best ingredient AND pass the causal gate
keep = [r for r in rows if r['vs_best_single'] <= 1.0 and r['causal_ok']][:15]
json.dump({'baseline': round(base), 'recipes': keep, 'all_tested': len(rows)},
          open(f'{BRAND}/results/recipes.json', 'w'), indent=1)
print(f'=== {BRAND} recipes (base ₹{base:,.0f}) — combos beating their own best ingredient, causal-gated ===')
for r in keep:
    print(f"  ₹{r['cost']:<6,} (n={r['n']:<3} {r['vs_base']:.2f}x base, {r['vs_best_single']:.2f}x best half)  " + '  +  '.join(r['recipe']))
