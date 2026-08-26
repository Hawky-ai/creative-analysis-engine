"""#1 Matched-pair analysis: compare creatives that ran in the SAME adset over
overlapping dates. Same audience, same budget logic, same period -> the only
difference left is the creative itself."""
import json, sys
from collections import defaultdict
from statistics import median

BRAND = sys.argv[1]
CONV = 'demo_sched' if BRAND == 'bhanzu' else 'leads'
CONV_DAILY = 'ds' if BRAND == 'bhanzu' else 'ld'

dim = [json.loads(l) for l in open(f'{BRAND}/raw/ctx_dim.jsonl')]
obs = json.load(open(f'{BRAND}/raw/canonical.json'))
daily = [json.loads(l) for l in open(f'{BRAND}/raw/daily.jsonl')]

ad2adset = {}
for r in dim:
    if r.get('ad_id'):
        key = r.get('adset_id') or (r.get('campaign_name','') + '|' + r.get('adset_name',''))
        ad2adset[r['ad_id']] = (key, r.get('adset_name',''), r.get('campaign_objective',''))

# per (adset, hash, date) performance
cell = defaultdict(lambda: [0.0, 0.0])   # spend, conv
dates_of = defaultdict(set)
for r in daily:
    a = ad2adset.get(r['ad_id'])
    if not a or not r['hash']: continue
    key = (a[0], r['hash'])
    c = cell[key]
    c[0] += r['sp']; c[1] += (r.get(CONV_DAILY) or 0)
    dates_of[key].add(r['daily_date'])

traits_of = defaultdict(set)
for o in obs: traits_of[o['hash']].add((o['facet'], o['value']))

# group by adset
by_adset = defaultdict(list)
for (adset, h), (sp, cv) in cell.items():
    if sp > 15000 and cv > 3 and traits_of.get(h):
        by_adset[adset].append((h, sp, cv, dates_of[(adset, h)]))

pairs = defaultdict(list)   # trait -> list of (with_cpl, without_cpl, weight)
n_adsets = 0
for adset, rows in by_adset.items():
    if len(rows) < 2: continue
    n_adsets += 1
    for i in range(len(rows)):
        for j in range(len(rows)):
            if i == j: continue
            hi, spi, cvi, di = rows[i]
            hj, spj, cvj, dj = rows[j]
            # require overlapping run dates (same market conditions)
            if len(di & dj) < 3: continue
            ti, tj = traits_of[hi], traits_of[hj]
            only_i = ti - tj
            if not only_i: continue
            cpl_i, cpl_j = spi/cvi, spj/cvj
            w = min(spi, spj)
            for t in only_i:
                pairs[t].append((cpl_i, cpl_j, w))

rows_out = []
for t, ps in pairs.items():
    if len(ps) < 12: continue
    wins = sum(1 for a, b, w in ps if a < b)
    tw = sum(w for _, _, w in ps)
    import math
    ratio = math.exp(sum(math.log(a/b)*w for a, b, w in ps) / tw)   # geometric mean: symmetric, unbiased
    rows_out.append({'facet': t[0], 'trait': t[1], 'comparisons': len(ps),
                     'win_rate': round(wins/len(ps), 3), 'cost_ratio': round(ratio, 3),
                     'verdict': 'CHEAPER' if ratio < 0.92 and wins/len(ps) > 0.56 else ('COSTLIER' if ratio > 1.08 and wins/len(ps) < 0.44 else 'NEUTRAL')})
rows_out.sort(key=lambda r: r['cost_ratio'])
json.dump({'adsets_used': n_adsets, 'results': rows_out}, open(f'{BRAND}/results/matched_pairs.json','w'), indent=1)
print(f'=== {BRAND}: {n_adsets} adsets with 2+ creatives running together ===')
print(f'{len(rows_out)} traits with >=12 head-to-head comparisons\n')
print('CHEAPER within the same adset (creative-only effect):')
for r in rows_out[:10]:
    if r['verdict'] == 'CHEAPER':
        print(f"  {r['facet']}:{r['trait']:<38} {r['comparisons']:>4} h2h | wins {r['win_rate']:.0%} | costs {r['cost_ratio']:.2f}x the rival")
print('\nCOSTLIER within the same adset:')
for r in reversed(rows_out[-10:]):
    if r['verdict'] == 'COSTLIER':
        print(f"  {r['facet']}:{r['trait']:<38} {r['comparisons']:>4} h2h | wins {r['win_rate']:.0%} | costs {r['cost_ratio']:.2f}x the rival")
