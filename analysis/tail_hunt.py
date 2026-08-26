import json, sys
from collections import defaultdict
B = sys.argv[1]
can = json.load(open(f'{B}/raw/canonical.json'))
cm = json.load(open(f'{B}/raw/concept_map.json'))
cmap = {}
for f, cons in cm.items():
    for c in cons:
        for v in c['values']: cmap[(f, v)] = c['concept']
inv = {json.loads(l)['hash']: json.loads(l) for l in open(f'{B}/raw/inventory.jsonl')}
ctx = json.load(open(f'{B}/raw/campaign_context.json'))
pool = {h: r for h, r in inv.items() if ctx.get(h, {}).get('primary_objective') == 'OUTCOME_LEADS' and r['leads'] > 0}
traits = defaultdict(set)
for o in can:
    if o['hash'] in pool:
        traits[(o['facet'], o['value'])].add(o['hash'])
        cc = cmap.get((o['facet'], o['value']))
        if cc: traits[(o['facet'], cc)].add(o['hash'])
tot_sp = sum(r['spend'] for r in pool.values())
base = tot_sp / sum(r['leads'] for r in pool.values())
big = {h for h, r in pool.items() if r.get('spend_life', r['spend']) >= 300000}
big_sp = sum(pool[h].get('spend_life', pool[h]['spend']) for h in big)
out = []
for (f, v), hs in traits.items():
    small = [h for h in hs if 10000 <= pool[h].get('spend_life', 0) <= 100000]
    if len(small) < 8: continue
    sp = sum(pool[h]['spend'] for h in small); ld = sum(pool[h]['leads'] for h in small)
    if ld < 50: continue
    cpl = sp / ld
    if cpl > 0.6 * base: continue
    big_share = sum(pool[h].get('spend_life', 0) for h in hs & big) / big_sp if big_sp else 0
    if big_share >= 0.03: continue
    out.append({'facet': f, 'trait': v, 'n_small_tests': len(small), 'small_cpl': round(cpl),
                'baseline': round(base), 'ratio': round(cpl/base, 2), 'leads': ld,
                'big_spend_share': round(big_share, 4)})
out.sort(key=lambda x: x['ratio'])
json.dump(out, open(f'{B}/results/unscaled_winners.json', 'w'), indent=1)
for r in out[:20]:
    print(f"₹{r['small_cpl']:<5} ({r['ratio']}x base) n={r['n_small_tests']:<3} leads={r['leads']:<6} big-share={r['big_spend_share']:.1%}  {r['facet']}:{r['trait']}")
print('total candidates:', len(out), '| baseline ₹%d' % base)
