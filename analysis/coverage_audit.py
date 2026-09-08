"""Coverage audit — find creative devices living only in scene_description prose.

The gap this closes: open vocabulary applies to VALUES, not FACETS. A device no facet
asks about gets described in scene_description and becomes invisible to grouping (a
split-screen gameplay strip survived two extraction rounds this way). Run this after
EVERY extraction, before the human review round.

Usage: python3 analysis/coverage_audit.py <obs.json> [obs2.json ...]
Flags any device word that recurs in scene prose but appears in no facet value.
Exit 1 when something is flagged — wire it into the runbook as a gate.
"""
import json, sys, re
from collections import Counter

DEVICE_WORDS = [
    "game", "gameplay", "split screen", "split-screen", "picture-in-picture", "overlay",
    "reacts to", "reaction", "green screen", "greenscreen", "countdown", "poll",
    "sticker", "filter", "blur", "b-roll", "meme", "asmr", "slime", "duet",
    "voiceover", "animation", "cartoon", "screenshot", "collage", "grid",
]

# Some device words are ambiguous: "blur" means a deliberate censor/privacy blur (a real
# device) but also ordinary background bokeh (not a device at all). Flagging the latter makes
# the gate cry wolf, and a gate that cries wolf gets ignored. When an ambiguous word appears
# ONLY in an innocuous context, it is not counted.
AMBIGUOUS_CONTEXT = {
    "blur": ("blurred background", "blurry background", "softly blurred", "blurred outdoor",
             "blurred garden", "blurred residential", "blurred indoor", "background is blurred"),
}

def is_incidental(word, prose):
    ctx = AMBIGUOUS_CONTEXT.get(word)
    if not ctx:
        return False
    # every occurrence must sit inside one of the innocuous phrases
    idx, total, innocuous = 0, 0, 0
    while (i := prose.find(word, idx)) != -1:
        total += 1
        window = prose[max(0, i - 30):i + 30]
        if any(c in window for c in ctx):
            innocuous += 1
        idx = i + len(word)
    return total > 0 and innocuous == total

hits = Counter(); examples = {}
facet_values = set()
for path in sys.argv[1:]:
    for r in json.load(open(path)):
        obs = r.get("obs")
        if not isinstance(obs, list):
            continue
        prose = ""
        for o in obs:
            # a malformed observation must not crash the gate — skip it
            if not isinstance(o, dict) or "facet" not in o or "value" not in o:
                continue
            if o["facet"] == "scene_description":
                prose = str(o["value"]).lower()
            else:
                facet_values.add(str(o["value"]).lower())
        for w in DEVICE_WORDS:
            if w in prose and not is_incidental(w, prose):
                hits[w] += 1
                examples.setdefault(w, prose[max(0, prose.find(w) - 60):prose.find(w) + 80])

flagged = []
for w, n in hits.most_common():
    covered = any(w.rstrip("s") in v for v in facet_values)
    if n >= 3 and not covered:
        flagged.append((w, n))
        print(f"UNCOVERED  {w!r}  in {n} videos' prose, in NO facet value")
        print(f"   e.g. …{examples[w]}…")
    else:
        print(f"ok         {w!r}  prose={n}  covered={covered}")

if flagged:
    print(f"\n{len(flagged)} device(s) live only in prose — add a facet (or extend notable_device examples) and re-run.")
    sys.exit(1)
print("\ncoverage clean.")
