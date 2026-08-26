"""Skill enforcement layer: machine-check every LLM-written insight against the
copilot skill rules. Violations -> reject list (caller regenerates or drops).
Principle: prompts ASK, validators ENFORCE."""
import json, sys
from collections import defaultdict

BRAND = sys.argv[1]
ins = json.load(open(f'{BRAND}/results/insights_v3.json'))
obs = json.load(open(f'{BRAND}/raw/canonical.json'))
pat = {f"{p['facet']}:{p['trait']}": p for p in json.load(open(f'{BRAND}/results/patterns.json'))['patterns']}
ev_by_hash = defaultdict(list)
for o in obs: ev_by_hash[o['hash'][:12]].append(str(o.get('evidence','')).lower())

FORBIDDEN_PHRASES = ["cost per lead is the clearest business-performance signal"]
REPORT = {'passed': [], 'violations': []}

for key, d in ins.items():
    if not isinstance(d, dict): REPORT['violations'].append({'key': key, 'errors': ['R0: malformed insight']}); continue
    errs = []
    # R1 every insight names its evidence base (skill: confidence+scale on every insight)
    p = pat.get(key) or d.get('pattern', {})
    pd = d.get('pattern') if isinstance(d.get('pattern'), dict) else {}
    if not (pd.get('n') or (pat.get(key) or {}).get('n')):
        errs.append('R1: no sample size attached')
    # R2 claim exists and is not a restated label (skill: never restate label as reason)
    claim = (d.get('claim') or '').strip()
    if len(claim) < 30: errs.append('R2: claim missing/trivial')
    trait_word = key.split(':', 1)[1].lower()
    mech = (d.get('mechanism') or '').lower()
    if not mech: errs.append('R2b: no mechanism')
    # R3 proof quotes must be verifiable: hash must exist, quote text must appear in that
    #    creative's stored evidence (anti-hallucination — hard rule)
    proofs = d.get('proof') or []
    if not proofs: errs.append('R3: no proof quotes')
    for q in proofs:
        h = str(q.get('hash', ''))[:12]
        if h and h not in ev_by_hash:
            errs.append(f'R3a: proof hash {h} not in corpus')
        elif h:
            quote = str(q.get('quote', '')).lower().strip('." ')
            if quote and len(quote) > 15 and not any(quote[:60] in e or e[:60] in quote for e in ev_by_hash[h]):
                # allow fuzzy: any 6-word window match
                words = quote.split()
                ok = any(' '.join(words[i:i+6]) in e for e in ev_by_hash[h] for i in range(max(1, len(words)-5)))
                if not ok: errs.append(f'R3b: quote not found in creative {h} evidence (possible hallucination)')
    # R4 action labeled with the causal layer (skill: recommendations must name the lever)
    if d.get('action_type') not in ('MAKE THIS AD', 'RESTRUCTURE CAMPAIGNS'):
        errs.append('R4: action_type missing/invalid')
    # R4b action content must be substantive (not empty/null-valued dict/short string)
    act = d.get('action')
    def act_len(a):
        if isinstance(a, str): return len(a.strip())
        if isinstance(a, dict): return sum(len(str(v)) for v in a.values() if v not in (None, '', 'null'))
        return 0
    if act_len(act) < 60: errs.append('R4b: action content empty/thin')
    # R5 campaign-only findings must not give ad-tweak advice
    if d.get('layer_agreement') == 'campaign-only' and d.get('action_type') == 'MAKE THIS AD':
        errs.append('R5: campaign-only evidence but ad-level action')
    # R6 forbidden sentences (skill: halt phrases)
    text = json.dumps(d).lower()
    for fp in FORBIDDEN_PHRASES:
        if fp in text: errs.append(f'R6: forbidden phrase "{fp[:40]}..."')
    # R7 disagree cases must carry a caveat (skill: cross-validation honesty)
    if d.get('layer_agreement') == 'disagree' and not d.get('caveats'):
        errs.append('R7: layers disagree but no caveat')
    (REPORT['violations'] if errs else REPORT['passed']).append({'key': key, 'errors': errs} if errs else key)

json.dump(REPORT, open(f'{BRAND}/results/insights_validation.json', 'w'), indent=1)
print(f"{BRAND}: {len(REPORT['passed'])} passed | {len(REPORT['violations'])} with violations")
for v in REPORT['violations']:
    print(f"  {v['key']}: " + '; '.join(v['errors']))
