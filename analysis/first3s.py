"""#4 First-3-seconds: which elements appear early, and does that move hook rate?"""
import json, re, sys
from collections import defaultdict
from statistics import median

BRAND = sys.argv[1]
obs = json.load(open(f'{BRAND}/raw/canonical.json'))
inv = {json.loads(l)['hash']: json.loads(l) for l in open(f'{BRAND}/raw/inventory.jsonl')}
TS = re.compile(r'\b(\d{1,2}):(\d{2})\b|\bfirst (\d) ?sec|\bopens? with|\bstarts? with|\bbeginning\b|\bintro\b', re.I)

def early(ev):
    ev = str(ev)
    if re.search(r'first \d ?sec|opens? with|starts? with|at the (very )?(start|beginning)|intro', ev, re.I): return True
    for m in re.finditer(r'\b(\d{1,2}):(\d{2})\b', ev):
        if int(m.group(1))*60 + int(m.group(2)) <= 3: return True
    return False

vids = {h for h, r in inv.items() if r['mt'] == 'video' and r['impressions'] > 20000 and (r.get('v3s') or 0) > 0}
hook = {h: inv[h]['v3s']/inv[h]['impressions'] for h in vids}
hold = {h: inv[h]['vp50']/inv[h]['vp25'] for h in vids if inv[h].get('vp25')}
med_hook = median(hook.values())

early_traits = defaultdict(set); any_traits = defaultdict(set)
for o in obs:
    if o['hash'] not in vids: continue
    k = (o['facet'], o['value'])
    any_traits[k].add(o['hash'])
    if early(o.get('evidence')): early_traits[k].add(o['hash'])

rows = []
for k, hs in early_traits.items():
    if len(hs) < 12: continue
    rest = vids - hs
    hm = median(hook[h] for h in hs); rm = median(hook[h] for h in rest)
    hh = [hold[h] for h in hs if h in hold]; rh = [hold[h] for h in rest if h in hold]
    rows.append({'facet': k[0], 'trait': k[1], 'n_early': len(hs),
                 'hook_rate': round(hm, 4), 'hook_vs_rest': round(hm/rm, 3),
                 'hold': round(median(hh), 3) if len(hh) > 5 else None,
                 'hold_vs_rest': round(median(hh)/median(rh), 3) if len(hh) > 5 and rh else None})
rows.sort(key=lambda r: -r['hook_vs_rest'])
json.dump({'median_hook_rate': med_hook, 'rows': rows}, open(f'{BRAND}/results/first3s.json','w'), indent=1)
print(f'=== {BRAND}: what appears in the first 3 seconds ({len(vids)} videos, median hook rate {med_hook:.1%}) ===')
print('\nBEST openers (hook rate vs all other videos):')
for r in rows[:8]:
    ho = f" | hold {r['hold_vs_rest']:.2f}x" if r['hold_vs_rest'] else ''
    print(f"  {r['facet']}:{r['trait']:<34} n={r['n_early']:<4} hook {r['hook_rate']:.1%} = {r['hook_vs_rest']:.2f}x{ho}")
print('\nWORST openers:')
for r in rows[-8:]:
    ho = f" | hold {r['hold_vs_rest']:.2f}x" if r['hold_vs_rest'] else ''
    print(f"  {r['facet']}:{r['trait']:<34} n={r['n_early']:<4} hook {r['hook_rate']:.1%} = {r['hook_vs_rest']:.2f}x{ho}")
