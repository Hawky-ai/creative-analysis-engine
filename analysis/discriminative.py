import json, sys
from collections import defaultdict, Counter

BRAND = sys.argv[1]
inv = {json.loads(l)['hash']: json.loads(l) for l in open(f'{BRAND}/raw/inventory.jsonl')}
obs = json.load(open(f'{BRAND}/raw/canonical.json'))

# facet -> metric family it can causally move
FACET_METRIC = {
    'hook': 'ctr', 'format': 'ctr', 'background': 'ctr', 'people': 'ctr', 'tone': 'ctr',
    'founder_presence': 'ctr', 'occasion': 'ctr', 'language': 'ctr',
    'offer': 'cvr', 'outcome_promise': 'cvr', 'claim_usp': 'cvr', 'certification_body': 'cvr',
    'time_commitment': 'cvr', 'coupon_code': 'cvr', 'cta': 'cvr',
    'messaging_angle': 'both', 'tech_domain': 'both', 'learner_profile': 'both',
    'program_structure': 'cvr', 'audience_target': 'both', 'age_group': 'both', 'region_signal': 'both',
    'product_presentation': 'ctr',
}

CONV = 'demo_sched' if BRAND == 'bhanzu' else 'leads'
def metric(h, kind):
    r = inv[h]
    if kind == 'ctr':
        return r['clicks'] / r['impressions'] if r['impressions'] > 10000 else None
    if kind == 'cvr':
        return r.get(CONV, 0) / r['link_clicks'] if r.get('link_clicks', 0) > 100 else None
    if kind == 'cpl':
        return r['spend'] / r[CONV] if r.get(CONV) else None

traits_of = defaultdict(set)
for o in obs: traits_of[o['hash']].add((o['facet'], o['value']))

print(f'=== {BRAND} discriminative patterns (top-quartile vs bottom-quartile) ===')
results = {}
for kind, better_high in [('ctr', True), ('cvr', True), ('cpl', False)]:
    hs = [(h, metric(h, kind)) for h in traits_of if h in inv]
    hs = [(h, v) for h, v in hs if v is not None]
    hs.sort(key=lambda x: x[1], reverse=better_high)
    q = len(hs) // 4
    top, bottom = {h for h, _ in hs[:q]}, {h for h, _ in hs[-q:]}
    rows = []
    all_traits = Counter()
    for h, _ in hs:
        for t in traits_of[h]: all_traits[t] += 1
    for t, n in all_traits.items():
        f = t[0]
        allowed = FACET_METRIC.get(f, 'both')
        if kind != 'cpl' and allowed not in (kind, 'both'): continue
        pt = sum(1 for h in top if t in traits_of[h]) / len(top)
        pb = sum(1 for h in bottom if t in traits_of[h]) / len(bottom)
        if max(pt, pb) < 0.12 or n < 10: continue
        sep = pt - pb
        top_n = sum(1 for h in top if t in traits_of[h]); bot_n = sum(1 for h in bottom if t in traits_of[h])
        pp = sep * 100
        if min(top_n, bot_n) < 3 and max(top_n, bot_n) < 3: tier = 'EXPLORATORY'
        elif pp >= 30: tier = 'STRONG_WIN'
        elif pp >= 15: tier = 'INDICATIVE_WIN'
        elif pp <= -30: tier = 'STRONG_ANTI'
        elif pp <= -15: tier = 'ANTI_PATTERN'
        else: tier = 'NO_SIGNAL'
        rows.append({'facet': f, 'trait': t[1], 'metric': kind, 'in_top': round(pt, 2), 'in_bottom': round(pb, 2),
                     'separation': round(sep, 2), 'n': n, 'top_n': top_n, 'bottom_n': bot_n, 'tier': tier})
    rows.sort(key=lambda r: -abs(r['separation']))
    results[kind] = rows
    print(f'\n[{kind.upper()}] n={len(hs)}, quartile={q}')
    for r in rows[:8]:
        print(f"  {r['tier']:<15} {r['facet']}:{r['trait']:<38} top {r['in_top']:.0%} vs bottom {r['in_bottom']:.0%} ({r['separation']*100:+.0f}pp)")
json.dump(results, open(f'{BRAND}/results/discriminative.json', 'w'), indent=1)
