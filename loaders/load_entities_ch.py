"""Load extracted observations into ClickHouse `default.extracted_entities_v2`
(the per-creative entity table Copilot's creative_group_by / view / include_entities read).

Per hash, one JSON object:
  facet -> "value"              scalar facet
  facet -> ["v1", "v2"]         multi-value facet (any facet that carries >1 value on ANY
                                creative is emitted as an array on EVERY creative, so the
                                column type is stable; Copilot's group-by explodes arrays)
  _observations -> [{facet, value, evidence, source}]   verbatim evidence, for `view`
  _timeline     -> {duration, beats:[...]}              optional, from --timeline

Keys starting with '_' are payloads, not attributes; Copilot's all-keys ranking skips them.

Usage:
  python3 loaders/load_entities_ch.py <obs.json> <brand_id> [--aliases aliases.json]
                                      [--timeline tl.json] [--dry-run]
  CH endpoint: env CLICKHOUSE_URL (default http://127.0.0.1:8123), auth CLICKHOUSE_USER/PASSWORD.

extracted_entities_v2 is a ReplacingMergeTree on (hash) versioned by insert time:
loading is non-destructive — old rows survive on disk until merge; a re-load of older
data 'reverts' what FINAL reads. Never DELETE to undo a load; load the previous state back.
"""
import json, os, sys, argparse, urllib.request, urllib.parse, base64, hashlib
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("obs_json")
ap.add_argument("brand_id")
ap.add_argument("--aliases", help="JSON {facet: [alias, ...]} — publish facet under extra names")
ap.add_argument("--timeline", help="beat timeline JSON from extract_timeline_vid.mjs")
ap.add_argument("--hash-from-url", action="store_true",
                help="key rows by md5(url)[:16] — matches accounts whose ad_metadata_v3.hash was synthesised from url")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

def key(r):
    return hashlib.md5(r["url"].encode()).hexdigest()[:16] if a.hash_from_url else r["hash"]

aliases = json.load(open(a.aliases)) if a.aliases else {}
timelines = {}
if a.timeline:
    for r in json.load(open(a.timeline)):
        if isinstance(r.get("timeline"), dict) and not r["timeline"].get("error"):
            timelines[key(r)] = r["timeline"]

records = [r for r in json.load(open(a.obs_json)) if isinstance(r.get("obs"), list)]

grouped_by_hash = {}
multi = set()
for r in records:
    grouped = defaultdict(list)
    for o in r["obs"]:
        v = str(o["value"]).strip().lower()
        if v and v not in grouped[o["facet"]]:
            grouped[o["facet"]].append(v)
    grouped_by_hash[key(r)] = grouped
    multi.update(f for f, vals in grouped.items() if len(vals) > 1)

rows_out = []
for r in records:
    grouped = grouped_by_hash[key(r)]
    ent = {}
    for f, vals in grouped.items():
        val = vals if f in multi else vals[0][:500]
        ent[f] = val
        for al in aliases.get(f, []):
            ent[al] = val
    ent["_observations"] = [
        {"facet": o["facet"], "value": str(o["value"]), "evidence": str(o.get("evidence", ""))[:600],
         "source": o.get("source", "")}
        for o in r["obs"] if o.get("evidence")
    ]
    if key(r) in timelines:
        ent["_timeline"] = timelines[key(r)]
    rows_out.append({"hash": key(r), "brand_id": a.brand_id, "extracted_entities": ent})

print(f"{len(rows_out)} entity rows for brand {a.brand_id}; "
      f"multi-value facets: {sorted(multi)}; timelines attached: {sum('_timeline' in r['extracted_entities'] for r in rows_out)}")
if a.dry_run:
    print(json.dumps(rows_out[0], indent=1, ensure_ascii=False)[:1500]); sys.exit(0)

url = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8123")
auth = base64.b64encode(f"{os.environ['CLICKHOUSE_USER']}:{os.environ['CLICKHOUSE_PASSWORD']}".encode()).decode()
q = urllib.parse.quote("INSERT INTO default.extracted_entities_v2 (hash, brand_id, extracted_entities) FORMAT JSONEachRow")
body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows_out).encode()
req = urllib.request.Request(f"{url}/?query={q}", data=body, headers={"Authorization": "Basic " + auth})
urllib.request.urlopen(req, timeout=300)
print("loaded.")
