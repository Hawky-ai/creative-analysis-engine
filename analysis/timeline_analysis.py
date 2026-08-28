"""Beat timeline x retention analysis.

Joins per-video beat timelines against Meta's video watch quartiles to answer:
 - what beat is playing when the audience actually leaves
 - when does the CTA land, and what share of viewers survive to see it
 - which opening beat role holds attention / converts best

Usage: python3 scripts/timeline_analysis.py
"""
import json
from collections import defaultdict

P = '/private/tmp/claude-501/-Users-apple-work-meta/e76840e7-1662-4b18-a477-b25558c46351/scratchpad/phase0'
B = 'vidbrand'

tl = {r['hash']: r['timeline'] for r in json.load(open(f'{P}/dostt_tl100.json'))
      if not r['timeline'].get('error')}
ret = json.load(open(f'{B}/raw/retention100.json'))
ents = {r['hash']: r['obs'] for r in json.load(open(f'{B}/raw/dostt_obs100_v4.json'))
        if isinstance(r['obs'], list)}

print(f"timelines {len(tl)} | retention {len(ret)} | entity sets {len(ents)}\n")

def beat_at(beats, t):
    for b in beats:
        if b['t0'] <= t < b['t1']:
            return b
    return beats[-1] if beats else None

def facet(h, f):
    for o in ents.get(h, []):
        if o['facet'] == f:
            return str(o['value'])
    return None

# ── 1. what is playing at each quartile, weighted by the viewers still there
q_roles = {q: defaultdict(float) for q in ('p25', 'p50', 'p75')}
cta_rows, first_role = [], defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # sp, installs, plays, p25
for h, t in tl.items():
    r = ret.get(h, {})
    beats, dur = t['beats'], t.get('duration') or (beats[-1]['t1'] if t.get('beats') else 0)
    if not beats or not dur:
        continue
    plays = r.get('plays', 0)
    for q, frac in (('p25', .25), ('p50', .50), ('p75', .75)):
        b = beat_at(beats, dur * frac)
        if b:
            q_roles[q][b['role']] += r.get(q, 0)

    # when does the first CTA / invitation land?
    cta = next((b for b in beats if b['role'] in ('cta', 'invitation')), None)
    if cta and plays:
        pos = cta['t0'] / dur
        # linear-interpolate the retention curve to estimate reach at that point
        pts = [(0.0, plays), (.25, r.get('p25', 0)), (.50, r.get('p50', 0)),
               (.75, r.get('p75', 0)), (1.0, r.get('p100', 0))]
        reach = plays
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            if x0 <= pos <= x1:
                reach = y0 + (y1 - y0) * ((pos - x0) / (x1 - x0) if x1 > x0 else 0)
                break
        cta_rows.append({'hash': h, 'pos': pos, 't': cta['t0'], 'dur': dur,
                         'reach_pct': reach / plays * 100, 'sp': r.get('sp', 0),
                         'installs': r.get('installs', 0), 'lang': facet(h, 'language_spoken')})

    fr = first_role[beats[0]['role']]
    fr[0] += r.get('sp', 0); fr[1] += r.get('installs', 0)
    fr[2] += plays; fr[3] += r.get('p25', 0)

print("=== WHO IS STILL WATCHING, AND WHAT IS PLAYING ===")
for q, label in (('p25', '25% mark'), ('p50', '50% mark'), ('p75', '75% mark')):
    tot = sum(q_roles[q].values()) or 1
    top = sorted(q_roles[q].items(), key=lambda x: -x[1])[:5]
    print(f"\n{label} — beat role playing (share of surviving viewers):")
    for role, v in top:
        print(f"   {role:<20} {v/tot*100:5.1f}%   ({v:,.0f} viewers)")

print("\n\n=== OPENING BEAT ROLE: does the first beat hold the audience? ===")
print(f"{'first beat role':<22} {'videos':>6} {'spend':>10} {'hold@25%':>9} {'CPI':>8}")
for role, (sp, ins, pl, p25) in sorted(first_role.items(), key=lambda x: -x[1][0]):
    n = sum(1 for h, t in tl.items() if t['beats'] and t['beats'][0]['role'] == role)
    hold = p25 / pl * 100 if pl else 0
    cpi = sp / ins if ins else 0
    print(f"{role:<22} {n:>6} {sp:>10,.0f} {hold:>8.1f}% {cpi:>8.0f}")

print("\n\n=== WHEN THE ASK LANDS (first cta/invitation beat) ===")
cta_rows.sort(key=lambda x: x['pos'])
buckets = [('first quarter (0-25%)', 0, .25), ('second (25-50%)', .25, .5),
           ('third (50-75%)', .5, .75), ('final quarter (75-100%)', .75, 1.01)]
print(f"{'ask lands in':<26} {'videos':>6} {'spend':>10} {'CPI':>8} {'~viewers still there':>21}")
for label, lo, hi in buckets:
    grp = [c for c in cta_rows if lo <= c['pos'] < hi]
    if not grp:
        continue
    sp = sum(c['sp'] for c in grp); ins = sum(c['installs'] for c in grp)
    reach = sum(c['reach_pct'] for c in grp) / len(grp)
    print(f"{label:<26} {len(grp):>6} {sp:>10,.0f} {sp/ins if ins else 0:>8.0f} {reach:>20.1f}%")

no_cta = [h for h, t in tl.items() if t['beats'] and not any(
    b['role'] in ('cta', 'invitation') for b in t['beats'])]
if no_cta:
    sp = sum(ret.get(h, {}).get('sp', 0) for h in no_cta)
    ins = sum(ret.get(h, {}).get('installs', 0) for h in no_cta)
    print(f"{'NO ask at all':<26} {len(no_cta):>6} {sp:>10,.0f} {sp/ins if ins else 0:>8.0f}")

json.dump({'cta_rows': cta_rows}, open(f'{B}/results/timeline_analysis.json', 'w'), indent=1)
print("\nsaved vidbrand/results/timeline_analysis.json")
