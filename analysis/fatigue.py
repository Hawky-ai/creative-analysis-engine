"""#2 Creative fatigue: does a creative's cost per outcome rise as it ages?"""
import json, sys
from collections import defaultdict
from statistics import median

BRAND = sys.argv[1]
CONV_D = 'ds' if BRAND == 'bhanzu' else 'ld'
daily = [json.loads(l) for l in open(f'{BRAND}/raw/daily.jsonl')]
obs = json.load(open(f'{BRAND}/raw/canonical.json'))
traits_of = defaultdict(set)
for o in obs: traits_of[o['hash']].add((o['facet'], o['value']))

per = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
for r in daily:
    if not r['hash']: continue
    c = per[r['hash']][r['daily_date']]
    c[0] += r['sp']; c[1] += (r.get(CONV_D) or 0)

# week-since-launch curve, spend-weighted
weeks = defaultdict(lambda: [0.0, 0.0])
lifespans = []
decay = []
for h, days in per.items():
    ds = sorted(days)
    if len(ds) < 14: continue
    d0 = ds[0]
    from datetime import date
    def wk(s):
        y, m, dd = map(int, s.split('-')); y0, m0, d0d = map(int, d0.split('-'))
        return (date(y, m, dd) - date(y0, m0, d0d)).days // 7
    tot_sp = sum(v[0] for v in days.values()); tot_cv = sum(v[1] for v in days.values())
    if tot_cv < 10 or tot_sp < 50000: continue
    lifespans.append(len(ds))
    curve = defaultdict(lambda: [0.0, 0.0])
    for d, (sp, cv) in days.items():
        w = wk(d)
        if w > 7: continue
        weeks[w][0] += sp; weeks[w][1] += cv
        curve[w][0] += sp; curve[w][1] += cv
    if 0 in curve and curve[0][1] >= 3:
        base = curve[0][0]/curve[0][1]
        for w in sorted(curve):
            if w >= 1 and curve[w][1] >= 3:
                decay.append((w, (curve[w][0]/curve[w][1])/base))
print(f'=== {BRAND}: creative fatigue ===')
print(f'creatives with >=14 active days and enough conversions: {len(lifespans)} | median lifespan {median(lifespans):.0f} days')
print('\nweek since launch | cost per outcome (all creatives pooled)')
w0 = weeks[0][0]/weeks[0][1] if weeks[0][1] else None
for w in sorted(weeks):
    sp, cv = weeks[w]
    if cv < 5: continue
    c = sp/cv
    print(f'  week {w}: cost ₹{c:>8,.0f}   {"(baseline)" if w==0 else f"{c/w0:.2f}x week 0"}   spend ₹{sp/1e5:.0f}L')
byw = defaultdict(list)
for w, r in decay: byw[w].append(r)
print('\nper-creative decay (median of each creative vs its own week 0):')
for w in sorted(byw):
    if len(byw[w]) >= 5:
        print(f'  week {w}: {median(byw[w]):.2f}x   (n={len(byw[w])} creatives)')
json.dump({'pooled': {str(w): {'cost': (weeks[w][0]/weeks[w][1]) if weeks[w][1] else None, 'spend': weeks[w][0]} for w in sorted(weeks)},
           'per_creative_median': {str(w): median(v) for w, v in byw.items() if len(v) >= 5},
           'median_lifespan_days': median(lifespans)}, open(f'{BRAND}/results/fatigue.json','w'), indent=1)
