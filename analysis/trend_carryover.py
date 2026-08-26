"""For each cutoff: winning traits LEARNED in training, then checked against
creatives that launched AFTER the cutoff. Did the trend repeat, and in how many?"""
import json, sys
from collections import defaultdict

BRAND = sys.argv[1]
CONV = 'demo_sched' if BRAND == 'bhanzu' else 'leads'
inv = {json.loads(l)['hash']: json.loads(l) for l in open(f'{BRAND}/raw/inventory.jsonl')}
obs = json.load(open(f'{BRAND}/raw/canonical.json'))
traits_of = defaultdict(set)
for o in obs: traits_of[o['hash']].add((o['facet'], o['value']))

def cost(hs):
    hs = [h for h in hs if h in inv and inv[h].get(CONV)]
    sp = sum(inv[h]['spend'] for h in hs); cv = sum(inv[h][CONV] for h in hs)
    return (sp/cv, len(hs)) if cv else (None, len(hs))

out = {}
splits = ['2026-05-01','2026-06-01','2026-07-01'] if BRAND == 'guvi' else ['2026-04-01','2026-06-01','2026-07-01']
for split in splits:
    tr = [h for h in inv if inv[h]['d1'] < split and inv[h]['spend'] > 20000 and inv[h].get(CONV) and traits_of.get(h)]
    te = [h for h in inv if inv[h]['d0'] >= split and inv[h]['spend'] > 20000 and inv[h].get(CONV) and traits_of.get(h)]
    tr_base, _ = cost(tr); te_base, _ = cost(te)
    th = defaultdict(list)
    for h in tr:
        for t in traits_of[h]: th[t].append(h)
    winners = []
    for t, hs in th.items():
        sp = sum(inv[h]['spend'] for h in hs)
        if len(hs) < 8 or sp < 0.02*sum(inv[h]['spend'] for h in tr): continue
        c, n = cost(hs)
        if c and c < tr_base * 0.75:
            winners.append((t, c, n))
    winners.sort(key=lambda x: x[1])
    rows = []
    for t, c, n in winners[:12]:
        hold = [h for h in te if t in traits_of[h]]
        hc, hn = cost(hold)
        rows.append({'facet': t[0], 'trait': t[1], 'train_cost': round(c), 'train_n': n,
                     'hold_cost': round(hc) if hc else None, 'hold_n': hn,
                     'repeated': bool(hc and hc < te_base)})
    ok = sum(1 for r in rows if r['repeated']); testable = sum(1 for r in rows if r['hold_cost'])
    out[split] = {'train_base': round(tr_base), 'hold_base': round(te_base), 'train_n': len(tr),
                  'hold_n': len(te), 'rows': rows, 'repeated': ok, 'testable': testable}
    print(f"\n=== {BRAND} cutoff {split} | train {len(tr)} creatives (base {round(tr_base)}) -> holdout {len(te)} new creatives (base {round(te_base)}) ===")
    print(f"{'winning trend learned in training':<46} {'train':>12} {'holdout':>18}  repeated?")
    for r in rows:
        hc = f"{r['hold_cost']} ({r['hold_n']} ads)" if r['hold_cost'] else "not used again"
        print(f"  {r['facet']+':'+r['trait']:<44} {r['train_cost']:>5} ({r['train_n']:>3}) {hc:>18}  {'YES' if r['repeated'] else ('no' if r['hold_cost'] else '—')}")
    print(f"  -> {ok}/{testable} winning trends repeated in the new creatives")
json.dump(out, open(f'{BRAND}/results/trend_carryover.json','w'), indent=1)
