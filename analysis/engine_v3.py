"""V3: within-campaign weighted ridge. One model, effects net of campaign choice.
Rows = (creative-hash x campaign) cells. y = log cost-per-conversion.
Campaign + launch-month fixed effects absorbed by demeaning. Traits shrunk by ridge,
weighted by conversion count so thin cells can't shout."""
import json, sys, math
import numpy as np
from collections import defaultdict

BRAND = sys.argv[1]
CONV_D = 'ds' if BRAND == 'bhanzu' else 'ld'
MIN_TRAIT_N = 8

daily = [json.loads(l) for l in open(f'{BRAND}/raw/daily.jsonl')]
dim = [json.loads(l) for l in open(f'{BRAND}/raw/ctx_dim.jsonl')]
obs = json.load(open(f'{BRAND}/raw/canonical.json'))
inv = {json.loads(l)['hash']: json.loads(l) for l in open(f'{BRAND}/raw/inventory.jsonl')}

ad2camp = {r['ad_id']: (r.get('campaign_name') or 'unknown') for r in dim if r.get('ad_id')}
ad2hash = {r['ad_id']: r['hash'] for r in dim if r.get('ad_id') and r.get('hash')}
traits_of = defaultdict(set)
for o in obs: traits_of[o['hash']].add((o['facet'], o['value']))

# cells: (hash, campaign) -> spend, conv, first month
cell = defaultdict(lambda: [0.0, 0.0, '9999-99'])
for r in daily:
    h = r['hash'] or ad2hash.get(r['ad_id'])
    if not h or h not in traits_of or h not in inv: continue
    c = ad2camp.get(r['ad_id'], 'unknown')
    e = cell[(h, c)]
    e[0] += r['sp']; e[1] += (r.get(CONV_D) or 0); e[2] = min(e[2], r['daily_date'][:7])

rows = [(h, c, sp, cv, m) for (h, c), (sp, cv, m) in cell.items() if cv >= 3 and sp >= 10000]
print(f'{BRAND}: {len(rows)} (creative x campaign) cells from {len({r[0] for r in rows})} creatives, {len({r[1] for r in rows})} campaigns')

# trait columns (gated)
tcount = defaultdict(set)
for h, c, sp, cv, m in rows:
    for t in traits_of[h]: tcount[t].add(h)
traits = sorted([t for t, hs in tcount.items() if len(hs) >= MIN_TRAIT_N])
tidx = {t: i for i, t in enumerate(traits)}
print(f'traits in model: {len(traits)}')

y = np.array([math.log(sp / cv) for _, _, sp, cv, _ in rows])
w = np.array([cv for _, _, _, cv, _ in rows], dtype=float)
w = np.sqrt(w)                      # damp the mega-ads, keep signal ordering
X = np.zeros((len(rows), len(traits)))
for i, (h, c, sp, cv, m) in enumerate(rows):
    for t in traits_of[h]:
        j = tidx.get(t)
        if j is not None: X[i, j] = 1.0

# absorb campaign + month fixed effects: weighted demeaning within each group
def demean(M, yv, wv, keys):
    groups = defaultdict(list)
    for i, k in enumerate(keys): groups[k].append(i)
    M = M.copy(); yv = yv.copy()
    for idx in groups.values():
        idx = np.array(idx); ww = wv[idx]; sw = ww.sum()
        yv[idx] -= (yv[idx]*ww).sum()/sw
        M[idx] -= (M[idx]*ww[:, None]).sum(0)/sw
    return M, yv

camp_keys = [c for _, c, _, _, _ in rows]
mon_keys = [m for _, _, _, _, m in rows]
Xd, yd = demean(X, y, w, camp_keys)
Xd, yd = demean(Xd, yd, w, mon_keys)

# identifiability: a trait is WITHIN-estimable only if it varies inside campaigns.
# Traits that define campaigns (offer=free masterclass -> masterclass campaigns) have
# ~zero within-variance; their within-coefficient is noise from rare mixed campaigns.
Ws = w[:, None]
raw_var = ((X - (X*Ws).sum(0)/w.sum())**2 * Ws).sum(0)
within_var = (Xd**2 * Ws).sum(0)
with np.errstate(divide='ignore', invalid='ignore'):
    within_share = np.where(raw_var > 0, within_var/raw_var, 0.0)
IDENT = within_share >= 0.15
print(f'identifiable within campaigns: {IDENT.sum()}/{len(traits)} traits')

# weighted ridge, closed form
lam = 4.0
Ws = w[:, None]
A = (Xd*Ws).T @ Xd + lam*np.eye(len(traits))
b = (Xd*Ws).T @ yd
beta = np.linalg.solve(A, b)

# effect = multiplier on cost (exp(beta)); <1 cheaper, >1 costlier
eff = {t: float(np.exp(beta[tidx[t]])) for t in traits if IDENT[tidx[t]]}

# BETWEEN model for campaign-defining traits: campaign-level rows, trait = share of
# campaign spend carrying it. Estimates the creative+audience BUNDLE — labeled as such.
camp_agg = defaultdict(lambda: [0.0, 0.0, defaultdict(float), '9999-99'])
for i, (h, c, sp, cv, m) in enumerate(rows):
    e = camp_agg[c]; e[0] += sp; e[1] += cv; e[3] = min(e[3], m)
    for t in traits_of[h]:
        if t in tidx: e[2][t] += sp
crows = [(c, sp, cv, tw, m) for c, (sp, cv, tw, m) in camp_agg.items() if cv >= 5]
cy = np.array([math.log(sp/cv) for _, sp, cv, _, _ in crows])
cw = np.sqrt(np.array([cv for _, _, cv, _, _ in crows]))
bt_traits = [t for t in traits if not IDENT[tidx[t]]]
bidx = {t: i for i, t in enumerate(bt_traits)}
CX = np.zeros((len(crows), len(bt_traits)))
for i, (c, sp, cv, tw, m) in enumerate(crows):
    for t, s_ in tw.items():
        j = bidx.get(t)
        if j is not None: CX[i, j] = s_/sp
CXd, cyd = demean(CX, cy, cw, [m for *_, m in crows])
CA = (CXd*cw[:, None]).T @ CXd + 4.0*np.eye(len(bt_traits))
cb = (CXd*cw[:, None]).T @ cyd
cbeta = np.linalg.solve(CA, cb)
eff_between = {t: float(np.exp(cbeta[bidx[t]])) for t in bt_traits}
supp = {t: len(tcount[t]) for t in traits}
out = sorted(eff.items(), key=lambda x: x[1])
json.dump({'within_effects': {f'{t[0]}:{t[1]}': {'multiplier': round(v, 3), 'n_creatives': supp[t]} for t, v in eff.items()},
           'between_effects': {f'{t[0]}:{t[1]}': {'multiplier': round(v, 3), 'n_creatives': supp[t]} for t, v in eff_between.items()},
           'cells': len(rows), 'campaign_cells': len(crows), 'traits': len(traits)},
          open(f'{BRAND}/results/engine_v3.json', 'w'), indent=1)
print('\n[CREATIVE-LEVEL] within-campaign effects — change the ad, keep the campaign:')
for t, v in out[:10]: print(f'  x{v:.2f}  {t[0]}:{t[1]}  (n={supp[t]})')
print('  ...')
for t, v in out[-6:][::-1]: print(f'  x{v:.2f}  {t[0]}:{t[1]}  (n={supp[t]})')
outb = sorted(eff_between.items(), key=lambda x: x[1])
print('\n[STRATEGY-LEVEL] between-campaign effects — creative+audience bundle, labeled as such:')
for t, v in outb[:8]: print(f'  x{v:.2f}  {t[0]}:{t[1]}  (n={supp[t]})')
print('  ...')
for t, v in outb[-8:][::-1]: print(f'  x{v:.2f}  {t[0]}:{t[1]}  (n={supp[t]})')
